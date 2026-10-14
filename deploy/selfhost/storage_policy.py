"""Pinned SDK full-document durability and private atomic JSON persistence."""

import hashlib
import importlib
import json
import os
import secrets
import stat
import tempfile
from importlib import metadata
from pathlib import Path
from typing import Any


def _identity(
    path: Path, directory: int | None = None
) -> tuple[int, int, int, int] | None:
    try:
        value = (
            path.lstat()
            if directory is None
            else os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        )
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(value.st_mode):
        raise ValueError("Regular JSON storage file required")
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def atomic_json(value: Any, filename: str | os.PathLike[str]) -> None:
    """Replace complete JSON privately; POSIX also syncs the parent directory."""
    target = Path(filename)
    if any(parent.is_symlink() for parent in [target.parent, *target.parent.parents]):
        raise ValueError("JSON storage parent must not be a symlink")
    directory = None
    temporary = None
    descriptor = None
    created_identity = None
    try:
        if os.name == "posix":
            directory = os.open(
                target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
        before = _identity(target, directory)
        if directory is not None:
            temporary = Path("." + target.name + ".pending-" + secrets.token_hex(16))
            descriptor = os.open(
                temporary.name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            os.fchmod(descriptor, 0o600)
        else:
            descriptor, name = tempfile.mkstemp(
                prefix="." + target.name + ".pending-", dir=target.parent
            )
            temporary = Path(name)
            os.chmod(temporary, 0o600)
        opened = os.fstat(descriptor)
        created_identity = opened.st_dev, opened.st_ino
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = None
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        if _identity(target, directory) != before:
            raise ValueError("JSON storage changed during persistence")
        current_temporary = _identity(temporary, directory)
        if current_temporary is None or current_temporary[:2] != created_identity:
            raise ValueError("Temporary JSON storage identity changed")
        if directory is None:
            os.replace(temporary, target)
        else:
            parent = target.parent.lstat()
            anchored_parent = os.fstat(directory)
            if not stat.S_ISDIR(parent.st_mode) or (parent.st_dev, parent.st_ino) != (
                anchored_parent.st_dev,
                anchored_parent.st_ino,
            ):
                raise ValueError("JSON storage parent changed during persistence")
            os.replace(
                temporary.name, target.name, src_dir_fd=directory, dst_dir_fd=directory
            )
            os.fsync(directory)
    finally:
        try:
            if descriptor is not None:
                os.close(descriptor)
            if temporary is not None and created_identity is not None:
                try:
                    remaining = _identity(temporary, directory)
                except ValueError:
                    remaining = None
                if remaining is not None and remaining[:2] == created_identity:
                    if directory is None:
                        temporary.unlink(missing_ok=True)
                    else:
                        try:
                            os.unlink(temporary.name, dir_fd=directory)
                        except FileNotFoundError:
                            pass
        finally:
            if directory is not None:
                os.close(directory)


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate storage protocol contract key")
        result[key] = value
    return result


def install_durable_storage() -> None:
    """Fail closed for unreviewed SDK bytes before installing the scoped policy."""
    contract = json.loads(
        Path(__file__).with_name("storage_contract.json").read_text(encoding="utf-8"),
        object_pairs_hook=_unique,
    )
    modules = (
        "lightrag.kg.json_kv_impl",
        "lightrag.kg.json_doc_status_impl",
        "lightrag.lightrag",
        "lightrag.namespace",
    )
    if set(contract) != {"distribution", "version", "module_sha256"} or set(
        contract["module_sha256"]
    ) != set(modules):
        raise ValueError("Exact pinned storage protocol contract required")
    distribution = metadata.distribution(contract["distribution"])
    if distribution.version != contract["version"]:
        raise ValueError("Unreviewed LightRAG storage version")
    for name in modules:
        source = Path(str(distribution.locate_file(name.replace(".", "/") + ".py")))
        if (
            hashlib.sha256(source.read_bytes()).hexdigest()
            != contract["module_sha256"][name]
        ):
            raise ValueError("Unreviewed LightRAG storage distribution source")
    loaded: dict[str, Any] = {}
    for name in modules:
        module = importlib.import_module(name)
        if not isinstance(module.__file__, str):
            raise TypeError("File-backed LightRAG storage module required")
        digest = hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        if digest != contract["module_sha256"][name]:
            raise ValueError("Unreviewed LightRAG storage source")
        loaded[name] = module
    kv = loaded[modules[0]]
    status = loaded[modules[1]]
    namespace = loaded[modules[3]].NameSpace
    original = kv.JsonKVStorage.upsert
    if getattr(original, "_mediconnect_durable", False):
        return

    async def durable_upsert(storage: Any, data: dict[str, dict[str, Any]]) -> None:
        await original(storage, data)
        if storage.namespace == namespace.KV_STORE_FULL_DOCS:
            # Original upsert releases the SDK lock; callback reacquires it.
            await storage.index_done_callback()

    durable_upsert.__dict__["_mediconnect_durable"] = True
    kv.write_json = atomic_json
    status.write_json = atomic_json
    kv.JsonKVStorage.upsert = durable_upsert

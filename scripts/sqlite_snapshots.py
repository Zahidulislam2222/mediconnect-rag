"""Prepare and validate consistent per-database snapshots without stopping services."""
import argparse
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import shutil
import tempfile
import time

from backup_settings import load_settings


MANIFEST = "manifest.json"
FORMAT_VERSION = 1


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def readonly(path, timeout):
    # mode=ro refuses nonexistent input and includes committed WAL transactions.
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=timeout)


def check_database(path, timeout):
    with closing(readonly(path, timeout)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity check failed")


def save(directory, data):
    temporary = directory / (MANIFEST + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(directory / MANIFEST)


@contextmanager
def snapshot_lock(policy):
    directory = policy.directory
    directory.parent.mkdir(parents=True, exist_ok=True)
    lock = directory.parent / (directory.name + ".lock")
    lock.mkdir()  # A crash leaves a visible lock; never silently discard it.
    try:
        yield
    finally:
        lock.rmdir()


def prepare_locked(policy):
    directory = policy.directory
    directory.mkdir(exist_ok=True)
    state = {"version": FORMAT_VERSION, "status": "PREPARING", "databases": []}
    save(directory, state)
    started = time.monotonic()

    def progress(_status, _remaining, _total):
        if time.monotonic() - started > policy.deadline_seconds:
            raise TimeoutError("SQLite snapshot deadline exceeded")

    for database in policy.databases:
        if not database.path.is_file():
            raise ValueError("Required SQLite source is unavailable")
        # Retain partial failures outside the group that Restic publishes.
        with tempfile.NamedTemporaryFile(prefix=database.name + "-", suffix=".partial", dir=directory.parent, delete=False) as temporary:
            destination = Path(temporary.name)
        with closing(readonly(database.path, policy.timeout_seconds)) as source, closing(sqlite3.connect(destination)) as target:
            source.backup(target, pages=policy.pages_per_step, progress=progress,
                          sleep=policy.retry_sleep_seconds)
        check_database(destination, policy.timeout_seconds)
        name = database.name + ".sqlite3"
        destination.replace(directory / name)
        state["databases"].append({"name": database.name, "file": name,
                                   "sha256": sha256(directory / name)})
        save(directory, state)
    state["status"] = "COMPLETE"
    state["completed_utc"] = datetime.now(timezone.utc).isoformat()
    save(directory, state)


def prepare(settings):
    if settings.sqlite:
        with snapshot_lock(settings.sqlite):
            prepare_locked(settings.sqlite)


def validate(directory, policy):
    state = json.loads((directory / MANIFEST).read_text(encoding="utf-8"))
    if state.get("version") != FORMAT_VERSION or state.get("status") != "COMPLETE":
        raise ValueError("SQLite snapshot set is incomplete")
    completed = datetime.fromisoformat(state.get("completed_utc", ""))
    if completed.tzinfo is None:
        raise ValueError("SQLite completion timestamp is invalid")
    rows = state.get("databases")
    expected = {db.name for db in policy.databases}
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows) or len(rows) != len(expected) or {row.get("name") for row in rows} != expected:
        raise ValueError("SQLite snapshot coverage differs from policy")
    for row in rows:
        if row.get("file") != row["name"] + ".sqlite3":
            raise ValueError("Unexpected SQLite snapshot filename")
        path = directory / row["file"]
        if path.is_symlink() or not path.is_file() or sha256(path) != row.get("sha256"):
            raise ValueError("SQLite snapshot hash mismatch")
        check_database(path, policy.timeout_seconds)
    return state


def backup(settings):
    """Keep the staging lock through the last Restic read, including pruning."""
    if not settings.sqlite or not settings.password_file.is_file():
        raise ValueError("Backup requires SQLite policy and an existing password file")
    executable = shutil.which("restic")
    if not executable:
        raise ValueError("Restic executable is unavailable")
    settings.backup_log_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", prefix="backup-", suffix=".log",
                                     dir=settings.backup_log_directory, delete=False) as log:
        def run(*arguments):
            result = subprocess.run([executable, "-r", str(settings.repository), "--password-file",
                                     str(settings.password_file), *arguments],
                                    stdout=log, stderr=log, check=False)
            if result.returncode:
                raise RuntimeError("Restic backup command failed; see retained log")

        with snapshot_lock(settings.sqlite):
            prepare_locked(settings.sqlite)
            validate(settings.sqlite.directory, settings.sqlite)
            # Access/password errors must never be mistaken for an empty repo.
            if not settings.repository.exists():
                run("init")
            run("snapshots")
            for group in settings.groups:
                args = ["backup", str(group.path), "--tag", group.tag]
                if group.exclude:
                    args.append("--exclude=" + group.exclude)
                run(*args)
            daily, weekly, monthly = settings.retention
            run("forget", "--keep-daily", str(daily), "--keep-weekly", str(weekly),
                "--keep-monthly", str(monthly), "--prune")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--backup", action="store_true", help="Create local Restic snapshots and apply configured retention")
    args = parser.parse_args()
    try:
        settings = load_settings(args.project_root)
        if args.backup:
            backup(settings)
        else:
            prepare(settings)
        if settings.sqlite:
            validate(settings.sqlite.directory, settings.sqlite)
        print("Backup PASS" if args.backup else "SQLite snapshot preparation PASS")
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, sqlite3.Error):
        print("SQLite snapshot preparation FAIL; retained evidence requires investigation")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

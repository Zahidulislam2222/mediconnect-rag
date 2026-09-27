"""Validated shared configuration for the backup and verification commands."""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re


@dataclass(frozen=True)
class Group:
    tag: str
    path: Path
    exclude: str | None


@dataclass(frozen=True)
class Database:
    name: str
    path: Path


@dataclass(frozen=True)
class SQLiteSettings:
    directory: Path
    group_tag: str
    timeout_seconds: float
    deadline_seconds: float
    pages_per_step: int
    retry_sleep_seconds: float
    databases: tuple[Database, ...]


@dataclass(frozen=True)
class Settings:
    repository: Path
    password_file: Path
    backup_log_directory: Path
    verification_directory: Path
    retention: tuple[int, int, int]
    groups: tuple[Group, ...]
    sqlite: SQLiteSettings | None = None


def clean_text(value):
    if not isinstance(value, str) or not value or any(c in value for c in "\r\n\t|\0"):
        raise ValueError("Invalid backup configuration text")
    return value


def local_path(root, value):
    relative = Path(clean_text(value))
    if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
        raise ValueError("Backup paths must be relative and contained in the project")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Backup path escapes the project")
    clean_text(str(resolved))
    return resolved


def load_settings(root, policy=None):
    root = root.resolve()
    policy = policy or Path(__file__).resolve().parents[1] / "config/backup-policy.json"
    data = json.loads(policy.read_text(encoding="utf-8"))
    paths = [local_path(root, data[key]) for key in (
        "repository", "password_file", "backup_log_directory", "verification_directory")]
    retention = tuple(data["retention"][key] for key in ("daily", "weekly", "monthly"))
    if any(type(value) is not int or value < 1 for value in retention):
        raise ValueError("Retention values must be positive integers")
    if not isinstance(data["groups"], list) or not data["groups"]:
        raise ValueError("At least one backup group is required")
    groups = []
    for item in data["groups"]:
        tag = clean_text(item["tag"])
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", tag):
            raise ValueError("Invalid backup group tag")
        exclude = item["exclude"]
        if exclude is not None:
            clean_text(exclude)
        groups.append(Group(tag, local_path(root, item["path"]), exclude))
    if len({g.tag for g in groups}) != len(groups) or len({g.path for g in groups}) != len(groups):
        raise ValueError("Backup groups must have unique tags and paths")
    sqlite = None
    if "sqlite" in data:
        item = data["sqlite"]
        directory = local_path(root, item["directory"])
        tag = clean_text(item["group_tag"])
        if not any(g.tag == tag and g.path == directory and g.exclude is None for g in groups):
            raise ValueError("SQLite staging must have its own complete backup group")
        protected = [paths[0], paths[1], *(g.path for g in groups if g.tag != tag)]
        if any(directory.is_relative_to(p) or p.is_relative_to(directory) for p in protected):
            raise ValueError("SQLite staging overlaps a protected path")
        numbers = [item[key] for key in ("timeout_seconds", "deadline_seconds", "retry_sleep_seconds")]
        if any(type(n) not in (int, float) or not 0 < n < float("inf") for n in numbers):
            raise ValueError("SQLite timing values must be finite and positive")
        if type(item["pages_per_step"]) is not int or item["pages_per_step"] < 1:
            raise ValueError("SQLite page batch must be positive")
        databases = []
        for db in item["databases"]:
            name = clean_text(db["name"])
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
                raise ValueError("Invalid SQLite database name")
            source = local_path(root, db["path"])
            if source.is_relative_to(directory) or source.is_relative_to(paths[0]):
                raise ValueError("SQLite source must be outside staging and repository")
            databases.append(Database(name, source))
        if not databases or len({db.name for db in databases}) != len(databases) or len({db.path for db in databases}) != len(databases):
            raise ValueError("SQLite databases must have unique names and paths")
        sqlite = SQLiteSettings(directory, tag, numbers[0], numbers[1], item["pages_per_step"], numbers[2], tuple(databases))
    return Settings(*paths, retention, tuple(groups), sqlite)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("section", choices=("paths", "groups"))
    args = parser.parse_args()
    settings = load_settings(args.root)
    if args.section == "paths":
        for value in (settings.repository, settings.password_file,
                      settings.backup_log_directory, *settings.retention):
            print(value)
    else:
        for group in settings.groups:
            print("|".join((group.tag, str(group.path), group.exclude or "")))


if __name__ == "__main__":
    main()

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
class Settings:
    repository: Path
    password_file: Path
    backup_log_directory: Path
    verification_directory: Path
    retention: tuple[int, int, int]
    groups: tuple[Group, ...]


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
    return Settings(*paths, retention, tuple(groups))


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

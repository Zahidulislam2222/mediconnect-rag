"""Verify every configured backup group and preserve isolated restore evidence."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import tempfile

from backup_settings import load_settings


def select_snapshots(snapshots, groups):
    if not isinstance(snapshots, list):
        raise ValueError("Snapshot inventory must be a list")
    candidates = []
    for snapshot in snapshots:
        if not isinstance(snapshot, dict) or not re.fullmatch(r"[0-9a-f]{64}", snapshot.get("id", "")):
            raise ValueError("Invalid snapshot identity")
        tags, paths = snapshot.get("tags", []), snapshot.get("paths")
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError("Invalid snapshot tags")
        if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
            raise ValueError("Invalid snapshot source paths")
        timestamp = snapshot.get("time")
        if not isinstance(timestamp, str):
            raise ValueError("Invalid snapshot timestamp")
        time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if time.tzinfo is None:
            raise ValueError("Snapshot timestamp must contain a timezone")
        candidates.append((time, snapshot))
    selected = []
    for group in groups:
        matching = [(time, snapshot) for time, snapshot in candidates
                    if group.tag in snapshot.get("tags", [])
                    and snapshot["paths"] == [str(group.path)]]
        if not matching:
            raise ValueError("Missing exact-source snapshot for a required group")
        selected.append((group, max(matching, key=lambda item: (item[0], item[1]["id"]))[1]))
    return selected


def verify(settings, output_root):
    if not settings.password_file.is_file():
        raise ValueError("Backup password file is unavailable")
    output_root = output_root.resolve()
    protected = [settings.repository, *(group.path for group in settings.groups)]
    if any(output_root.is_relative_to(path) for path in protected):
        raise ValueError("Restore evidence cannot be placed in a backup source or repository")
    output_root.mkdir(parents=True, exist_ok=True)
    evidence = Path(tempfile.mkdtemp(prefix="verify-", dir=output_root))
    state = {"status": "RUNNING", "groups": [], "scope": "Configured local file groups only"}
    report = evidence / "verification.json"

    def save():
        temporary = report.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        temporary.replace(report)

    def run(arguments, label):
        with (evidence / (label + ".stdout.log")).open("w", encoding="utf-8") as out, (
            evidence / (label + ".stderr.log")
        ).open("w", encoding="utf-8") as err:
            result = subprocess.run(["restic", "-r", str(settings.repository), "--password-file",
                                     str(settings.password_file), "--no-cache", *arguments],
                                    stdout=out, stderr=err, check=False)
        return result.returncode

    save()
    try:
        code = run(["snapshots", "--json"], "snapshots")
        if code:
            raise RuntimeError("Snapshot inventory failed")
        snapshots = json.loads((evidence / "snapshots.stdout.log").read_text(encoding="utf-8"))
        selected = select_snapshots(snapshots, settings.groups)
        state["integrity_exit"] = run(["check", "--read-data"], "integrity")
        save()
        if state["integrity_exit"]:
            raise RuntimeError("Full-data integrity check failed")
        for group, snapshot in selected:
            target = evidence / group.tag
            target.mkdir()
            entry = {"tag": group.tag, "snapshot_id": snapshot["id"], "status": "RESTORING"}
            state["groups"].append(entry)
            save()
            entry["restore_exit"] = run(["restore", snapshot["id"], "--target", str(target),
                                         "--verify"], "restore-" + group.tag)
            entry["status"] = "PASS" if entry["restore_exit"] == 0 else "FAIL"
            save()
        state["status"] = "PASS" if all(g["status"] == "PASS" for g in state["groups"]) else "FAIL"
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        state["status"] = "FAIL"
        state["error"] = str(exc)
    finally:
        save()
    print("Backup verification " + state["status"] + "; evidence and restore files retained.")
    return 0 if state["status"] == "PASS" else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    try:
        settings = load_settings(args.project_root)
        return verify(settings, args.output_root or settings.verification_directory)
    except (OSError, ValueError, KeyError, TypeError):
        print("Backup verification FAIL: configuration or local prerequisites are invalid.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

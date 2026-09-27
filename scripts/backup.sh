#!/bin/bash
# Prepare consistent SQLite copies, then create/prune local Restic snapshots.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/sqlite_snapshots.py" --project-root "$SCRIPT_DIR/.." --backup "$@"

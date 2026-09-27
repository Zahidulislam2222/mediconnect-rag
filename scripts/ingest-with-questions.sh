#!/bin/bash
# --plan reads local files; --execute may incur provider charges.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/ingest_documents.py" --profile hyde "$@"

#!/bin/bash
# RAGSetup Backup Verification Script
# Verifies repository integrity and tests restore capability

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REPO="$PROJECT_ROOT/backups"
PASSWORD_FILE="$PROJECT_ROOT/configs/.restic-password"
RESTORE_DIR="/tmp/ragsetup-restore-test"

echo "=== RAGSetup Backup Verification: $(date) ==="

# Check prerequisites
if [ ! -f "$PASSWORD_FILE" ]; then
    echo "ERROR: Password file not found at $PASSWORD_FILE"
    exit 1
fi

# Step 1: Check repository integrity
echo ""
echo "--- Step 1: Repository Integrity Check ---"
restic -r "$REPO" --password-file "$PASSWORD_FILE" check
echo "Repository integrity: OK"

# Step 2: List snapshots
echo ""
echo "--- Step 2: Available Snapshots ---"
restic -r "$REPO" --password-file "$PASSWORD_FILE" snapshots

# Step 3: Test restore (latest snapshot to temp dir)
echo ""
echo "--- Step 3: Test Restore (dry run) ---"
LATEST_ID=$(restic -r "$REPO" --password-file "$PASSWORD_FILE" snapshots --json | python3 -c "import sys,json; snaps=json.load(sys.stdin); print(snaps[-1]['short_id'] if snaps else 'NONE')" 2>/dev/null || echo "NONE")

if [ "$LATEST_ID" = "NONE" ]; then
    echo "WARNING: No snapshots found. Run backup.sh first."
    exit 1
fi

echo "Restoring snapshot $LATEST_ID to $RESTORE_DIR..."
mkdir -p "$RESTORE_DIR"
restic -r "$REPO" --password-file "$PASSWORD_FILE" restore "$LATEST_ID" --target "$RESTORE_DIR" --verify
echo "Restore verification: OK"

# Cleanup test restore
rm -rf "$RESTORE_DIR"
echo "Cleaned up test restore directory."

echo ""
echo "=== Backup Verification Complete: $(date) ==="
echo "Status: ALL CHECKS PASSED"

#!/bin/bash
# RAGSetup Backup Script — uses restic for encrypted, deduplicated backups
# Run manually or via Windows Task Scheduler

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REPO="$PROJECT_ROOT/backups"
PASSWORD_FILE="$PROJECT_ROOT/configs/.restic-password"
LOG_FILE="$PROJECT_ROOT/reports/backup-$(date +%Y%m%d-%H%M%S).log"

echo "=== RAGSetup Backup Started: $(date) ===" | tee "$LOG_FILE"

# Check prerequisites
if [ ! -f "$PASSWORD_FILE" ]; then
    echo "ERROR: Password file not found at $PASSWORD_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

# Initialize repo if not already initialized
if ! restic -r "$REPO" --password-file "$PASSWORD_FILE" snapshots > /dev/null 2>&1; then
    echo "Initializing restic repository..." | tee -a "$LOG_FILE"
    restic -r "$REPO" --password-file "$PASSWORD_FILE" init
fi

# Backup configs
echo "Backing up configs..." | tee -a "$LOG_FILE"
restic -r "$REPO" --password-file "$PASSWORD_FILE" backup \
    "$PROJECT_ROOT/configs/" \
    --exclude="*.sqlite3" \
    --tag "configs" \
    2>&1 | tee -a "$LOG_FILE"

# Backup LightRAG data
echo "Backing up LightRAG data..." | tee -a "$LOG_FILE"
restic -r "$REPO" --password-file "$PASSWORD_FILE" backup \
    "$PROJECT_ROOT/lightrag/data/" \
    --tag "lightrag-data" \
    2>&1 | tee -a "$LOG_FILE"

# Backup Grafana dashboards and provisioning
echo "Backing up Grafana..." | tee -a "$LOG_FILE"
restic -r "$REPO" --password-file "$PASSWORD_FILE" backup \
    "$PROJECT_ROOT/monitoring/grafana/" \
    --exclude="*.db" \
    --tag "grafana" \
    2>&1 | tee -a "$LOG_FILE"

# Prune old backups — keep last 7 daily, 4 weekly, 6 monthly
echo "Pruning old backups..." | tee -a "$LOG_FILE"
restic -r "$REPO" --password-file "$PASSWORD_FILE" forget \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 6 \
    --prune \
    2>&1 | tee -a "$LOG_FILE"

echo "=== RAGSetup Backup Completed: $(date) ===" | tee -a "$LOG_FILE"

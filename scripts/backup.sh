#!/bin/bash
# RAGSetup Backup Script — uses restic for encrypted, deduplicated backups
# Run manually or via Windows Task Scheduler

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Both commands consume the same validated policy. Capture failures before parsing.
CONFIG_VALUES=$(python3 "$SCRIPT_DIR/backup_settings.py" "$PROJECT_ROOT" paths)
GROUP_VALUES=$(python3 "$SCRIPT_DIR/backup_settings.py" "$PROJECT_ROOT" groups)
mapfile -t SETTINGS <<< "$CONFIG_VALUES"
REPO="${SETTINGS[0]}"
PASSWORD_FILE="${SETTINGS[1]}"
LOG_DIR="${SETTINGS[2]}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/backup-$(date +%Y%m%d-%H%M%S).log"

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

# Backup each configured group with its existing exclusions.
while IFS='|' read -r group source exclude; do
    echo "Backing up $group..." | tee -a "$LOG_FILE"
    arguments=(backup "$source" --tag "$group")
    if [ -n "$exclude" ]; then arguments+=("--exclude=$exclude"); fi
    restic -r "$REPO" --password-file "$PASSWORD_FILE" "${arguments[@]}" \
        2>&1 | tee -a "$LOG_FILE"
done <<< "$GROUP_VALUES"

# Prune according to the existing retention policy.
echo "Pruning old backups..." | tee -a "$LOG_FILE"
restic -r "$REPO" --password-file "$PASSWORD_FILE" forget \
    --keep-daily "${SETTINGS[3]}" \
    --keep-weekly "${SETTINGS[4]}" \
    --keep-monthly "${SETTINGS[5]}" \
    --prune \
    2>&1 | tee -a "$LOG_FILE"

echo "=== RAGSetup Backup Completed: $(date) ===" | tee -a "$LOG_FILE"

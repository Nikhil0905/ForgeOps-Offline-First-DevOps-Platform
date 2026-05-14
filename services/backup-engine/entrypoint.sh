#!/usr/bin/env bash
# Backup engine entrypoint — runs backup on start then on schedule
set -euo pipefail

INTERVAL="${BACKUP_SCHEDULE:-86400}"  # Default: every 24h in seconds

echo "[BACKUP] ForgeOps Backup Engine starting..."
echo "[BACKUP] Schedule interval: ${INTERVAL}s"

while true; do
    /usr/local/bin/backup.sh
    echo "[BACKUP] Next backup in ${INTERVAL}s..."
    sleep "${INTERVAL}"
done

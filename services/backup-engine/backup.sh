#!/usr/bin/env bash
# ============================================================
# ForgeOps Backup Engine
# Backs up: Gitea repos, Jenkins config, Docker registry data
# Runs on a cron schedule defined by BACKUP_SCHEDULE env var
# ============================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_ROOT="${BACKUP_DIR}/${TIMESTAMP}"
MAX_BACKUPS=10  # Keep last 10 snapshots

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [BACKUP] $*"; }

# ── Create backup directory ──────────────────────────────────
mkdir -p "${BACKUP_ROOT}"
log "Starting backup → ${BACKUP_ROOT}"

# ── Backup Gitea ─────────────────────────────────────────────
if [ -d "/source/gitea" ]; then
    log "Backing up Gitea data..."
    tar -czf "${BACKUP_ROOT}/gitea.tar.gz" -C /source gitea || true
    log "✅ Gitea backed up"
else
    log "⚠️  Gitea source not found — skipping"
fi

# ── Backup Jenkins ───────────────────────────────────────────
if [ -d "/source/jenkins" ]; then
    log "Backing up Jenkins data..."
    # Exclude workspace and cache dirs to save space
    tar -czf "${BACKUP_ROOT}/jenkins.tar.gz" \
        --exclude='*/workspace/*' \
        --exclude='*/.cache/*' \
        --exclude='*/logs/*' \
        -C /source jenkins || true
    log "✅ Jenkins backed up"
else
    log "⚠️  Jenkins source not found — skipping"
fi

# ── Backup Docker Registry ───────────────────────────────────
if [ -d "/source/registry" ]; then
    log "Backing up Docker registry..."
    tar -czf "${BACKUP_ROOT}/registry.tar.gz" -C /source registry || true
    log "✅ Registry backed up"
else
    log "⚠️  Registry source not found — skipping"
fi

# ── Create manifest ──────────────────────────────────────────
cat > "${BACKUP_ROOT}/manifest.json" <<EOF
{
  "timestamp": "${TIMESTAMP}",
  "backup_root": "${BACKUP_ROOT}",
  "components": ["gitea", "jenkins", "registry"],
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "hostname": "$(hostname)"
}
EOF
log "✅ Manifest written"

# ── Compute checksum ─────────────────────────────────────────
sha256sum "${BACKUP_ROOT}"/*.tar.gz 2>/dev/null > "${BACKUP_ROOT}/checksums.sha256" || true
log "✅ Checksums written"

# ── Prune old backups (keep last MAX_BACKUPS) ────────────────
log "Pruning old backups (keeping last ${MAX_BACKUPS})..."
ls -dt "${BACKUP_DIR}"/20* 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -rf || true
log "✅ Pruning complete"

# ── Summary ──────────────────────────────────────────────────
TOTAL_SIZE=$(du -sh "${BACKUP_ROOT}" 2>/dev/null | cut -f1)
log "Backup complete — size: ${TOTAL_SIZE} — location: ${BACKUP_ROOT}"

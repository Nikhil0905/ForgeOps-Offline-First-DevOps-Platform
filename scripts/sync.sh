#!/usr/bin/env bash
# ============================================================
# ForgeOps Manual Sync Trigger
# Forces an immediate sync of queued commits/images
# Usage: bash scripts/sync.sh
# ============================================================
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()  { echo -e "${CYAN}[SYNC]${NC} $*"; }
ok()   { echo -e "${GREEN}[SYNC ✅]${NC} $*"; }
warn() { echo -e "${YELLOW}[SYNC ⚠️]${NC} $*"; }

# Check internet
log "Checking internet connectivity..."
if curl -sf --connect-timeout 3 https://8.8.8.8 > /dev/null 2>&1 || \
   nc -zw3 8.8.8.8 53 > /dev/null 2>&1; then
    ok "Internet is available"
else
    warn "No internet connectivity — sync will be queued"
fi

# Restart sync engine to force immediate cycle
log "Triggering sync engine..."
if docker ps --filter "name=forgeops-sync-engine" --format "{{.Names}}" | grep -q sync; then
    docker restart forgeops-sync-engine
    ok "Sync engine restarted — sync cycle will begin shortly"
    log "Tailing sync logs (Ctrl+C to stop)..."
    docker logs -f --tail=30 forgeops-sync-engine
else
    warn "Sync engine container not running — starting it..."
    FORGEOPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    docker compose -f "${FORGEOPS_DIR}/docker-compose.yml" up -d sync-engine
fi

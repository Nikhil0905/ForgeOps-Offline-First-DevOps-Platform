#!/usr/bin/env bash
# ============================================================
# ForgeOps Manual Sync Trigger
# Forces an immediate sync of all local Gitea repos to GitHub.
#
# Strategy: Each local repo is pushed as a separate branch
#           (projects/<repo-name>) in the configured remote repo.
#
# Usage: bash scripts/sync.sh
# ============================================================
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

log()  { echo -e "${CYAN}[SYNC]${NC} $*"; }
ok()   { echo -e "${GREEN}[SYNC OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[SYNC WARN]${NC} $*"; }
err()  { echo -e "${RED}[SYNC ERR]${NC} $*"; }

FORGEOPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Check internet ──────────────────────────────────────────
log "Checking internet connectivity..."
if ping -c 1 -W 3 8.8.8.8 > /dev/null 2>&1 || \
   nc -zw3 8.8.8.8 53 > /dev/null 2>&1; then
    ok "Internet is available"
else
    warn "No internet connectivity — sync will be queued"
fi

# ── Show current sync status ────────────────────────────────
QUEUE_FILE="${FORGEOPS_DIR}/services/sync-engine/queue.json"
if [ -f "${QUEUE_FILE}" ]; then
    PENDING_COMMITS=$(python3 -c "import json; q=json.load(open('${QUEUE_FILE}')); print(len(q.get('pending_commits',[])))" 2>/dev/null || echo "?")
    PENDING_IMAGES=$(python3 -c "import json; q=json.load(open('${QUEUE_FILE}')); print(len(q.get('pending_images',[])))" 2>/dev/null || echo "?")
    LAST_SYNC=$(python3 -c "import json; q=json.load(open('${QUEUE_FILE}')); print(q.get('last_sync','never'))" 2>/dev/null || echo "unknown")
    ONLINE=$(python3 -c "import json; q=json.load(open('${QUEUE_FILE}')); print('yes' if q.get('online') else 'no')" 2>/dev/null || echo "unknown")

    log "Queue status:"
    log "  Pending commits : ${PENDING_COMMITS}"
    log "  Pending images  : ${PENDING_IMAGES}"
    log "  Last sync       : ${LAST_SYNC}"
    log "  Online          : ${ONLINE}"
    echo ""
fi

# ── List local Gitea repos ──────────────────────────────────
log "Fetching local Gitea repos..."
REPOS=$(curl -s -u "forgeops:ForgeOps@2025" "http://localhost/gitea/api/v1/repos/search?limit=50" 2>/dev/null \
    | python3 -c "import sys,json; [print(f'  - {r[\"name\"]}') for r in json.load(sys.stdin).get('data',[])]" 2>/dev/null || true)

if [ -n "${REPOS}" ]; then
    log "Repos to sync:"
    echo "${REPOS}"
    echo ""
else
    warn "Could not fetch repos from Gitea (is it running?)"
fi

# ── Restart sync engine to force immediate cycle ────────────
log "Triggering sync engine..."
if docker ps --filter "name=forgeops-sync-engine" --format "{{.Names}}" | grep -q sync; then
    docker restart forgeops-sync-engine > /dev/null 2>&1
    ok "Sync engine restarted — sync cycle will begin shortly"
    log "Each repo will be pushed as branch 'projects/<repo-name>' in the remote repo"
    echo ""
    log "Tailing sync logs (Ctrl+C to stop)..."
    echo "────────────────────────────────────────────────────"
    docker logs -f --tail=30 forgeops-sync-engine
else
    warn "Sync engine container not running — starting it..."
    docker compose -f "${FORGEOPS_DIR}/docker-compose.yml" up -d sync-engine
    ok "Sync engine started"
    log "Tailing sync logs (Ctrl+C to stop)..."
    echo "────────────────────────────────────────────────────"
    docker logs -f --tail=30 forgeops-sync-engine
fi

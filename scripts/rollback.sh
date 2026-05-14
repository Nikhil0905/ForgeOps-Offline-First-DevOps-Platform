#!/usr/bin/env bash
# ============================================================
# ForgeOps Emergency Rollback Script
# Rolls back a deployed container to its previous image
# Usage: bash scripts/rollback.sh <service-name> [image:tag]
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

SERVICE="${1:-}"
TARGET_IMAGE="${2:-}"
REGISTRY="${REGISTRY_HOST:-registry:5000}"

log()     { echo -e "${CYAN}[ROLLBACK]${NC} $*"; }
success() { echo -e "${GREEN}[ROLLBACK ✅]${NC} $*"; }
warn()    { echo -e "${YELLOW}[ROLLBACK ⚠️]${NC} $*"; }
error()   { echo -e "${RED}[ROLLBACK ❌]${NC} $*"; exit 1; }

[ -z "${SERVICE}" ] && error "Usage: rollback.sh <service-name> [image:tag]"

log "Rolling back service: ${SERVICE}"

# ── Find previous image if not specified ──────────────────────
if [ -z "${TARGET_IMAGE}" ]; then
    log "No target image specified — looking up previous image..."

    # Get current image
    CURRENT=$(docker inspect --format='{{.Config.Image}}' "${SERVICE}" 2>/dev/null || echo "")
    [ -z "${CURRENT}" ] && error "Container '${SERVICE}' not found"
    log "Current image: ${CURRENT}"

    # Extract image name and current tag (assumes numeric build tags)
    IMAGE_NAME=$(echo "${CURRENT}" | sed 's/:[^:]*$//')
    CURRENT_TAG=$(echo "${CURRENT}" | grep -oP ':\K[^:]+$' || echo "latest")

    # List all tags in local registry for this image
    IMAGE_REPO=$(echo "${IMAGE_NAME}" | sed "s|${REGISTRY}/||")
    log "Fetching tags from registry for: ${IMAGE_REPO}"

    TAGS_JSON=$(curl -sf "http://${REGISTRY}/v2/${IMAGE_REPO}/tags/list" 2>/dev/null || echo '{"tags":[]}')
    TAGS=$(echo "${TAGS_JSON}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tags = [t for t in (data.get('tags') or []) if t != 'latest']
try:
    tags_sorted = sorted(tags, key=lambda x: int(x) if x.isdigit() else 0, reverse=True)
except:
    tags_sorted = sorted(tags, reverse=True)
print('\n'.join(tags_sorted))" 2>/dev/null || echo "")

    if [ -z "${TAGS}" ]; then
        error "No previous tags found in registry for ${IMAGE_REPO}"
    fi

    # Pick the second-most-recent tag (skip current)
    PREV_TAG=$(echo "${TAGS}" | grep -v "^${CURRENT_TAG}$" | head -1)
    [ -z "${PREV_TAG}" ] && error "No previous tag available to rollback to"

    TARGET_IMAGE="${IMAGE_NAME}:${PREV_TAG}"
    warn "Auto-selected previous image: ${TARGET_IMAGE}"
fi

# ── Confirm ───────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}  Service       : ${SERVICE}${NC}"
echo -e "${YELLOW}  Target image  : ${TARGET_IMAGE}${NC}"
echo ""
read -rp "  Proceed with rollback? [y/N] " CONFIRM
[[ "${CONFIRM}" =~ ^[Yy]$ ]] || { warn "Rollback cancelled."; exit 0; }

# ── Stop current container ────────────────────────────────────
log "Stopping current container..."
docker stop "${SERVICE}" 2>/dev/null || warn "Container was not running"
docker rm   "${SERVICE}" 2>/dev/null || true

# ── Pull target image from registry ──────────────────────────
log "Pulling target image: ${TARGET_IMAGE}..."
docker pull "${TARGET_IMAGE}" || error "Failed to pull ${TARGET_IMAGE}"

# ── Start with previous image ─────────────────────────────────
log "Starting container with rolled-back image..."
docker run -d \
    --name "${SERVICE}" \
    --restart unless-stopped \
    "${TARGET_IMAGE}"

# ── Verify ───────────────────────────────────────────────────
sleep 5
STATUS=$(docker inspect --format='{{.State.Status}}' "${SERVICE}" 2>/dev/null || echo "missing")
if [ "${STATUS}" = "running" ]; then
    success "Rollback successful — ${SERVICE} is running with ${TARGET_IMAGE}"
else
    error "Rollback failed — container status: ${STATUS}"
fi

# ── Report to dashboard ───────────────────────────────────────
curl -sf -X POST "http://localhost:5050/api/deployments" \
    -H "Content-Type: application/json" \
    -d "{
        \"service\": \"${SERVICE}\",
        \"image\": \"${TARGET_IMAGE}\",
        \"status\": \"ROLLBACK_SUCCESS\",
        \"started_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    }" > /dev/null 2>&1 || true

success "Done. Dashboard updated."

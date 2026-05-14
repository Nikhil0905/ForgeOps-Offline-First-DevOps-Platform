#!/usr/bin/env bash
# ============================================================
# ForgeOps Install Script
# Bootstraps the entire platform from scratch
# Usage: bash scripts/install.sh
# ============================================================
set -euo pipefail

FORGEOPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${FORGEOPS_DIR}/docker-compose.yml"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()     { echo -e "${CYAN}[$(date '+%H:%M:%S')] [FORGEOPS]${NC} $*"; }
success() { echo -e "${GREEN}[$(date '+%H:%M:%S')] [✅ OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[$(date '+%H:%M:%S')] [⚠️  WARN]${NC} $*"; }
error()   { echo -e "${RED}[$(date '+%H:%M:%S')] [❌ ERROR]${NC} $*"; exit 1; }

# ── Banner ────────────────────────────────────────────────────
echo -e "${CYAN}"
cat << 'EOF'
  ___  ___  ____   __  ____     ___  ____  ____
 | __|| _ \| () ) / _||  __|   / _ \|  _ \/ ___|
 | _| | () )| () \| (_ | _|   | (_) | (_) \__ \
 |_|  |___/ |____/ \__||___|   \___/ |____/____/

  Offline-First DevOps Platform — Installer v1.0
EOF
echo -e "${NC}"

log "Starting ForgeOps installation in: ${FORGEOPS_DIR}"

# ── Pre-flight checks ─────────────────────────────────────────
log "Running pre-flight checks..."

command -v docker >/dev/null 2>&1 || error "Docker is not installed. Install Docker first: https://docs.docker.com/get-docker/"
command -v docker compose >/dev/null 2>&1 || \
    command -v docker-compose >/dev/null 2>&1 || \
    error "Docker Compose not found. Install it first."

DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+' | head -1)
log "Docker version: ${DOCKER_VERSION}"
success "Pre-flight checks passed"

# ── Detect compose command ────────────────────────────────────
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi
log "Using compose command: ${COMPOSE_CMD}"

# ── Setup data directories ────────────────────────────────────
log "Creating data directories..."
mkdir -p "${FORGEOPS_DIR}/data/gitea"
mkdir -p "${FORGEOPS_DIR}/data/jenkins"
mkdir -p "${FORGEOPS_DIR}/data/registry"
mkdir -p "${FORGEOPS_DIR}/data/nexus"
mkdir -p "${FORGEOPS_DIR}/data/dashboard"
mkdir -p "${FORGEOPS_DIR}/data/backups"
mkdir -p "${FORGEOPS_DIR}/infrastructure/nginx/certs"
chmod -R 755 "${FORGEOPS_DIR}/data"
success "Data directories created"

# ── Fix file permissions ──────────────────────────────────────
log "Setting script permissions..."
chmod +x "${FORGEOPS_DIR}/scripts/"*.sh
chmod +x "${FORGEOPS_DIR}/services/backup-engine/backup.sh"
chmod +x "${FORGEOPS_DIR}/services/backup-engine/entrypoint.sh"
chmod +x "${FORGEOPS_DIR}/services/dependency-mirror/setup-nexus.sh"
success "Permissions set"

# ── Configure Docker to allow local registry (insecure) ───────
DAEMON_FILE="/etc/docker/daemon.json"
if [ -f "${DAEMON_FILE}" ]; then
    if ! grep -q "registry:5000" "${DAEMON_FILE}" 2>/dev/null; then
        warn "You may need to add registry:5000 to insecure-registries in ${DAEMON_FILE}"
        warn "  { \"insecure-registries\": [\"localhost:5000\", \"registry:5000\"] }"
    fi
else
    warn "Consider creating ${DAEMON_FILE} with insecure-registries for localhost:5000"
fi

# ── Pull base images first (if online) ───────────────────────
log "Pulling base Docker images (if internet available)..."
IMAGES=(
    "nginx:1.25-alpine"
    "gitea/gitea:1.21"
    "registry:2"
    "prom/prometheus:latest"
    "grafana/grafana:latest"
    "python:3.11-slim"
    "alpine:3.19"
)

ONLINE=false
if curl -sf --connect-timeout 3 https://hub.docker.com > /dev/null 2>&1; then
    ONLINE=true
    log "Internet available — pulling images..."
    for img in "${IMAGES[@]}"; do
        log "  Pulling ${img}..."
        docker pull "${img}" || warn "Failed to pull ${img} — will use cached if available"
    done
    success "Base images pulled"
else
    warn "Offline mode — using cached images only"
fi

# ── Build custom images ────────────────────────────────────────
log "Building custom ForgeOps images..."
${COMPOSE_CMD} -f "${COMPOSE_FILE}" build --parallel || error "Image build failed"
success "Custom images built"

# ── Start core services ────────────────────────────────────────
log "Starting core services (Gitea, Registry, Prometheus)..."
${COMPOSE_CMD} -f "${COMPOSE_FILE}" up -d \
    gitea registry prometheus grafana
sleep 10

# ── Start Jenkins ──────────────────────────────────────────────
log "Starting Jenkins (this takes ~2 minutes on first run)..."
${COMPOSE_CMD} -f "${COMPOSE_FILE}" up -d jenkins
log "Waiting for Jenkins to initialise..."
for i in $(seq 1 24); do
    if curl -sf http://localhost:8080/login > /dev/null 2>&1; then
        success "Jenkins is ready!"
        break
    fi
    echo -n "."
    sleep 5
done
echo ""

# ── Start remaining services ───────────────────────────────────
log "Starting all remaining services..."
${COMPOSE_CMD} -f "${COMPOSE_FILE}" up -d
success "All services started"

# ── Setup Nexus Maven mirror (if online) ──────────────────────
if [ "${ONLINE}" = "true" ]; then
    log "Configuring Nexus Maven mirror..."
    sleep 30
    bash "${FORGEOPS_DIR}/services/dependency-mirror/setup-nexus.sh" || \
        warn "Nexus setup had issues — you can re-run setup-nexus.sh manually"
fi

# ── Health check ───────────────────────────────────────────────
log "Running health checks..."
bash "${FORGEOPS_DIR}/scripts/healthcheck.sh"

# ── Done ──────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  🎉 ForgeOps installation complete!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Dashboard  :${NC}  http://localhost/"
echo -e "  ${CYAN}Gitea      :${NC}  http://localhost/gitea/"
echo -e "  ${CYAN}Jenkins    :${NC}  http://localhost/jenkins/"
echo -e "  ${CYAN}Registry   :${NC}  http://localhost:5000"
echo -e "  ${CYAN}Nexus      :${NC}  http://localhost:8081"
echo -e "  ${CYAN}Prometheus :${NC}  http://localhost:9090"
echo -e "  ${CYAN}Grafana    :${NC}  http://localhost/grafana/"
echo ""
echo -e "  ${YELLOW}Admin credentials are in .env${NC}"
echo ""

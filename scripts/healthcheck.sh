#!/usr/bin/env bash
# ============================================================
# ForgeOps Health Check Script
# Verifies all services are running and responsive
# Usage: bash scripts/healthcheck.sh
# ============================================================

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

PASS=0; FAIL=0; WARN=0

ok()   { echo -e "  ${GREEN}✅ PASS${NC}  $*"; ((PASS++)); }
fail() { echo -e "  ${RED}❌ FAIL${NC}  $*"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}⚠️  WARN${NC}  $*"; ((WARN++)); }

check_http() {
    local name="$1" url="$2"
    if curl -sf --connect-timeout 5 --max-time 10 "${url}" > /dev/null 2>&1 || false; then
        ok "${name} (${url})"
    else
        fail "${name} — not responding at ${url}"
    fi
}

check_container() {
    local name="$1"
    if docker inspect --format='{{.State.Status}}' "${name}" 2>/dev/null | grep -q "running" || false; then
        ok "Container: ${name}"
    else
        fail "Container: ${name} — not running"
    fi
}

echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${CYAN}   ForgeOps Health Check${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}── Container Status ───────────────────────${NC}"
check_container "forgeops-gitea"
check_container "forgeops-jenkins"
check_container "forgeops-registry"
check_container "forgeops-nexus"
check_container "forgeops-prometheus"
check_container "forgeops-grafana"
check_container "forgeops-dashboard-api"
check_container "forgeops-dashboard-ui"
check_container "forgeops-nginx"
check_container "forgeops-sync-engine"
check_container "forgeops-backup-engine"

echo ""
echo -e "${CYAN}── HTTP Endpoints ─────────────────────────${NC}"
check_http "Gitea"          "http://localhost/gitea/"
check_http "Jenkins"        "http://localhost/jenkins/"
check_http "Registry"       "http://localhost:5000/v2/"
check_http "Nexus"          "http://localhost:8081/service/rest/v1/status"
check_http "Prometheus"     "http://localhost:9090/-/ready"
check_http "Grafana"        "http://localhost/grafana/api/health"
check_http "Dashboard API"  "http://localhost:5050/api/system-health"
check_http "Dashboard UI"   "http://localhost"
check_http "Nginx"          "http://localhost/health"

echo ""
echo -e "${CYAN}── Disk Usage ─────────────────────────────${NC}"
DISK_FREE=$(df -h / | awk 'NR==2{print $4}')
DISK_USED=$(df -h / | awk 'NR==2{print $5}' | tr -d '%')
echo "  Free disk: ${DISK_FREE}"
if [ "${DISK_USED}" -gt 90 ]; then
    warn "Disk usage is ${DISK_USED}% — consider cleanup"
else
    ok "Disk usage: ${DISK_USED}%"
fi

echo ""
echo -e "${CYAN}── Docker Resources ───────────────────────${NC}"
RUNNING=$(docker ps --filter "name=forgeops" --format "{{.Names}}" | wc -l)
echo "  ForgeOps containers running: ${RUNNING}"

echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "  Results: ${GREEN}${PASS} passed${NC}  ${RED}${FAIL} failed${NC}  ${YELLOW}${WARN} warnings${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo ""

if [ "${FAIL}" -gt 0 ]; then
    echo -e "${RED}Some checks failed. Run: docker compose logs <service>${NC}"
    exit 1
fi

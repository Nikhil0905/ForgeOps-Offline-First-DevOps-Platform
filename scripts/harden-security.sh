#!/usr/bin/env bash
# ============================================================
# ForgeOps Platform Security Hardening Script
# Generates TLS certificates and configures Nginx basic auth
# ============================================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

FORGEOPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERTS_DIR="${FORGEOPS_DIR}/infrastructure/nginx/certs"
NGINX_DIR="${FORGEOPS_DIR}/infrastructure/nginx"

echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${CYAN}   ForgeOps Security Hardening Tool${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo ""

# 1. Create directory structures
mkdir -p "${CERTS_DIR}"

# 2. Generate Self-Signed SSL/TLS Certificates
if [ ! -f "${CERTS_DIR}/forgeops.crt" ] || [ ! -f "${CERTS_DIR}/forgeops.key" ]; then
    echo -e "${YELLOW}[TLS] Generating self-signed TLS certificates...${NC}"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${CERTS_DIR}/forgeops.key" \
        -out "${CERTS_DIR}/forgeops.crt" \
        -subj "/C=US/ST=DevOps/L=Offline/O=ForgeOps/CN=forgeops.local" 2>/dev/null
    echo -e "${GREEN}[✅ OK] Certificates generated at:${NC}"
    echo "  - Key: ${CERTS_DIR}/forgeops.key"
    echo "  - Cert: ${CERTS_DIR}/forgeops.crt"
else
    echo -e "${GREEN}[✅ OK] TLS certificates already exist. Skipping.${NC}"
fi

# 3. Generate Nginx .htpasswd for Dashboard Basic Auth
if [ ! -f "${NGINX_DIR}/.htpasswd" ]; then
    echo -e "${YELLOW}[AUTH] Creating Nginx basic authentication credentials...${NC}"
    # Default: admin / ForgeOps@2025
    HASHED_PASSWORD=$(openssl passwd -apr1 "ForgeOps@2025")
    echo "admin:${HASHED_PASSWORD}" > "${NGINX_DIR}/.htpasswd"
    echo -e "${GREEN}[✅ OK] .htpasswd created with user 'admin'${NC}"
    echo "  - Default Password: ForgeOps@2025"
else
    echo -e "${GREEN}[✅ OK] .htpasswd already exists. Skipping.${NC}"
fi

echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}   Security Assets Successfully Prepared!${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "Next steps:"
echo -e " 1. Update Nginx configuration to enable SSL and basic auth."
echo -e " 2. Restart Nginx container using: ${CYAN}docker compose up -d nginx${NC}"
echo ""

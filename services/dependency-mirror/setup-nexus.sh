#!/usr/bin/env bash
# ============================================================
# ForgeOps Nexus Maven Mirror Bootstrap Script
# Run once to configure Nexus as a Maven proxy
# ============================================================
set -euo pipefail

NEXUS_URL="${NEXUS_URL:-http://nexus:8081}"
NEXUS_ADMIN_PASSWORD="${NEXUS_ADMIN_PASSWORD:-ForgeOps@Nexus2025}"
DEFAULT_PASSWORD_FILE="/nexus-data/admin.password"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [NEXUS] $*"; }

wait_for_nexus() {
    log "Waiting for Nexus to be ready..."
    for i in $(seq 1 60); do
        if curl -sf "${NEXUS_URL}/service/rest/v1/status" > /dev/null 2>&1; then
            log "Nexus is ready after ${i}s"
            return 0
        fi
        sleep 5
    done
    log "ERROR: Nexus did not start in time"
    return 1
}

get_initial_password() {
    if [ -f "${DEFAULT_PASSWORD_FILE}" ]; then
        cat "${DEFAULT_PASSWORD_FILE}"
    else
        echo "admin123"  # default
    fi
}

nexus_api() {
    local method="$1"
    local path="$2"
    local data="${3:-}"
    local password
    password=$(get_initial_password)

    curl -sf -X "${method}" \
        -u "admin:${password}" \
        -H "Content-Type: application/json" \
        "${NEXUS_URL}${path}" \
        ${data:+-d "${data}"}
}

set_admin_password() {
    local old_pass
    old_pass=$(get_initial_password)
    log "Setting admin password..."
    curl -sf -X PUT \
        -u "admin:${old_pass}" \
        -H "Content-Type: text/plain" \
        -d "${NEXUS_ADMIN_PASSWORD}" \
        "${NEXUS_URL}/service/rest/v1/security/users/admin/change-password" || true
}

create_maven_proxy() {
    log "Creating Maven Central proxy repository..."
    nexus_api POST "/service/rest/v1/repositories/maven/proxy" '{
        "name": "maven-central-proxy",
        "online": true,
        "storage": {
            "blobStoreName": "default",
            "strictContentTypeValidation": true
        },
        "proxy": {
            "remoteUrl": "https://repo1.maven.org/maven2/",
            "contentMaxAge": 1440,
            "metadataMaxAge": 1440
        },
        "negativeCache": {
            "enabled": true,
            "timeToLive": 1440
        },
        "httpClient": {
            "blocked": false,
            "autoBlock": true
        },
        "maven": {
            "versionPolicy": "RELEASE",
            "layoutPolicy": "STRICT"
        }
    }' || log "maven-central-proxy may already exist"
}

create_maven_snapshots_proxy() {
    log "Creating Maven Snapshots proxy repository..."
    nexus_api POST "/service/rest/v1/repositories/maven/proxy" '{
        "name": "maven-snapshots-proxy",
        "online": true,
        "storage": {
            "blobStoreName": "default",
            "strictContentTypeValidation": true
        },
        "proxy": {
            "remoteUrl": "https://oss.sonatype.org/content/repositories/snapshots/",
            "contentMaxAge": 1440,
            "metadataMaxAge": 1440
        },
        "negativeCache": {
            "enabled": true,
            "timeToLive": 1440
        },
        "maven": {
            "versionPolicy": "SNAPSHOT",
            "layoutPolicy": "STRICT"
        }
    }' || log "maven-snapshots-proxy may already exist"
}

create_maven_group() {
    log "Creating Maven group repository (offline mirror)..."
    nexus_api POST "/service/rest/v1/repositories/maven/group" '{
        "name": "forgeops-maven-mirror",
        "online": true,
        "storage": {
            "blobStoreName": "default",
            "strictContentTypeValidation": true
        },
        "group": {
            "memberNames": [
                "maven-releases",
                "maven-snapshots",
                "maven-central-proxy",
                "maven-snapshots-proxy"
            ]
        },
        "maven": {
            "versionPolicy": "MIXED",
            "layoutPolicy": "STRICT"
        }
    }' || log "forgeops-maven-mirror may already exist"
}

disable_anonymous_access() {
    log "Configuring anonymous access..."
    nexus_api PUT "/service/rest/v1/security/anonymous" '{
        "enabled": false,
        "userId": "anonymous",
        "realmName": "NexusAuthorizingRealm"
    }' || true
}

# ── Main ──────────────────────────────────────────────────────────────────────
wait_for_nexus
set_admin_password
create_maven_proxy
create_maven_snapshots_proxy
create_maven_group
disable_anonymous_access

log "✅ Nexus Maven mirror configured!"
log "Mirror URL: ${NEXUS_URL}/repository/forgeops-maven-mirror/"
log "Add to your pom.xml:"
log "  <repository><id>forgeops</id>"
log "    <url>${NEXUS_URL}/repository/forgeops-maven-mirror/</url></repository>"

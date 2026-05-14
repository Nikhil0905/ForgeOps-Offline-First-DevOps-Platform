# ForgeOps — Living Project Context
> **Auto-update this file** whenever the project changes. It is the single source of truth for AI assistants, new contributors, and future you.

---

## 📌 Project Identity

| Field          | Value                                                   |
|----------------|---------------------------------------------------------|
| **Name**       | ForgeOps                                                |
| **Full Name**  | Fully Offline Resilient GitOps & CI/CD Platform         |
| **Location**   | `/home/0xlunatic/Downloads/Docker-Project/forgeops/`    |
| **Created**    | 2026-05-07                                              |
| **Status**     | 🟢 Active Development                                   |
| **Purpose**    | Self-hosted offline-first DevOps for air-gapped/low-connectivity environments |

---

## 🏗️ Architecture Summary

```
[Developer] → git push → [Gitea :3000] → webhook → [Jenkins :8080]
                                                         │
                         ┌───────────────────────────────┤
                         ▼               ▼               ▼
                  [Nexus :8081]   [Docker Build]  [Security Scanner]
                  Maven Mirror                           │
                         │               │               │
                         └───────────────▼───────────────┘
                                [Local Registry :5000]
                                         │
                                [Deployment Engine]
                                 ┌───────┴──────┐
                              healthy?        failed?
                                 │               │
                              [Keep]         [Rollback]
                                         │
                              [Dashboard :8888]
                              [Prometheus :9090]
                              [Grafana :3001]
```

---

## 📦 Services & Ports

| Container                    | Image                    | Port(s)       | Role                        |
|------------------------------|--------------------------|---------------|-----------------------------|
| `forgeops-nginx`             | nginx:1.25-alpine        | 80, 443       | Reverse proxy / router      |
| `forgeops-gitea`             | gitea/gitea:1.21         | 3000, 2222    | Local Git server            |
| `forgeops-jenkins`           | custom (jenkins/lts)     | 8080, 50000   | CI/CD engine                |
| `forgeops-registry`          | registry:2               | 5000          | Docker image store          |
| `forgeops-nexus`             | sonatype/nexus3          | 8081          | Maven dependency mirror     |
| `forgeops-prometheus`        | prom/prometheus          | 9090          | Metrics collection          |
| `forgeops-grafana`           | grafana/grafana          | 3001          | Metrics visualisation       |
| `forgeops-dashboard-api`     | custom (python:3.11)     | 5050          | Flask REST API              |
| `forgeops-dashboard-ui`      | custom (nginx)           | 8888          | SPA monitoring dashboard    |
| `forgeops-sync-engine`       | custom (python:3.11)     | —             | Internet-aware sync         |
| `forgeops-backup-engine`     | custom (alpine)          | —             | Scheduled backups           |
| `forgeops-deployment-engine` | custom (python:3.11)     | —             | Health-check deployer       |
| `forgeops-security-scanner`  | custom (python:3.11)     | —             | Secrets + image scanner     |

---

## 📁 File Map

```
forgeops/
├── context.md                          ← YOU ARE HERE
├── docker-compose.yml                  ← Full orchestration (all services)
├── .env                                ← All credentials & config vars
│
├── infrastructure/
│   ├── nginx/nginx.conf                ← Reverse proxy routing rules
│   ├── registry/config.yml             ← Docker registry v2 config
│   ├── jenkins/
│   │   ├── Dockerfile                  ← Jenkins + Docker CLI + Maven
│   │   ├── jenkins.yaml                ← JCasC auto-configuration
│   │   └── plugins.txt                 ← Jenkins plugins to install
│   ├── gitea/app.ini                   ← Gitea offline config (SQLite)
│   └── monitoring/
│       ├── prometheus.yml              ← Scrape targets config
│       └── grafana/datasources.yml     ← Auto-provision Prometheus DS
│
├── services/
│   ├── sync-engine/
│   │   ├── sync.py                     ← Internet detection + sync loop
│   │   ├── queue.json                  ← Persistent offline queue state
│   │   └── Dockerfile
│   ├── backup-engine/
│   │   ├── backup.sh                   ← Tar-based backup with rotation
│   │   ├── entrypoint.sh               ← Loop runner for scheduled backups
│   │   └── Dockerfile
│   ├── deployment-engine/
│   │   ├── deploy.py                   ← Pull → run → healthcheck → rollback
│   │   └── Dockerfile
│   ├── security-scanner/
│   │   ├── scanner.py                  ← Regex secret scan + image check
│   │   └── Dockerfile
│   └── dependency-mirror/
│       └── setup-nexus.sh              ← Nexus REST API bootstrap
│
├── dashboard/
│   ├── backend/
│   │   ├── app.py                      ← Flask API (8 endpoints + /metrics)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/
│       ├── index.html                  ← SPA shell (7 pages)
│       ├── style.css                   ← Premium dark theme
│       ├── app.js                      ← Fetch + render logic
│       └── Dockerfile
│
├── templates/
│   ├── java-maven/
│   │   ├── Jenkinsfile                 ← Maven CI pipeline
│   │   └── pom.xml                     ← Pre-configured Nexus mirror
│   ├── nodejs/Jenkinsfile              ← Node.js CI pipeline
│   └── python/Jenkinsfile              ← Python CI pipeline
│
├── scripts/
│   ├── install.sh                      ← Full bootstrap (run once)
│   ├── healthcheck.sh                  ← Verify all services
│   ├── sync.sh                         ← Manual sync trigger
│   └── rollback.sh                     ← Emergency rollback
│
└── docs/README.md                      ← User-facing documentation
```

---

## 🔐 Default Credentials

| Service   | Username  | Password                 |
|-----------|-----------|--------------------------|
| Gitea     | forgeops  | ForgeOps@2025            |
| Jenkins   | admin     | ForgeOps@Jenkins2025     |
| Nexus     | admin     | ForgeOps@Nexus2025       |
| Grafana   | admin     | ForgeOps@Grafana2025     |

> ⚠️ Change all passwords in `.env` before production use.

---

## 🔌 Dashboard API Endpoints

| Method | Path                       | Description                        |
|--------|----------------------------|------------------------------------|
| GET    | `/api/system-health`       | Aggregate health of all services   |
| GET    | `/api/stats`               | Summary stats for overview cards   |
| GET    | `/api/builds`              | Jenkins build history              |
| POST   | `/api/builds/webhook`      | Receive Jenkins build events       |
| GET    | `/api/deployments`         | Deployment history                 |
| POST   | `/api/deployments`         | Record a deployment event          |
| GET    | `/api/repositories`        | List Gitea repositories            |
| GET    | `/api/registry/images`     | List local Docker images           |
| GET    | `/api/security-findings`   | Security scan results              |
| POST   | `/api/security-findings`   | Record scanner findings            |
| GET    | `/api/logs`                | Combined event log stream          |
| GET    | `/api/sync-status`         | Sync engine queue state            |
| GET    | `/metrics`                 | Prometheus metrics                 |

---

## 🛠️ Common Commands

```bash
# Start everything
docker compose up -d

# Stop everything
docker compose down

# View logs for a service
docker compose logs -f jenkins

# Run health check
bash scripts/healthcheck.sh

# Manual sync
bash scripts/sync.sh

# Emergency rollback
bash scripts/rollback.sh <service-name>

# Manual backup
docker exec forgeops-backup-engine /usr/local/bin/backup.sh

# Nexus Maven mirror setup (run after Nexus starts)
bash services/dependency-mirror/setup-nexus.sh

# Rebuild a single service
docker compose build dashboard-backend
docker compose up -d --no-deps dashboard-backend
```

---

## 📈 Implementation Phases

| Phase | Goal                        | Status      |
|-------|-----------------------------|-------------|
| 1     | Infrastructure setup        | ✅ Complete |
| 2     | CI/CD automation            | ✅ Complete |
| 3     | Offline dependency system   | ✅ Complete |
| 4     | Sync engine                 | ✅ Complete |
| 5     | Monitoring dashboard        | ✅ Complete |
| 6     | Security & recovery         | ✅ Complete |

---

## 🔮 Future Enhancements

- [ ] AI log analysis (Jenkins failure pattern detection)
- [ ] K3s offline Kubernetes cluster support
- [ ] Multi-node edge deployment
- [ ] USB/portable SSD mode
- [ ] LDAP authentication integration
- [ ] Webhook signature verification (Gitea → Jenkins HMAC)
- [ ] Grafana dashboard JSON provisioning
- [ ] Trivy offline DB bundling

---

## 📝 Change Log

| Date       | Change                                              | By         |
|------------|-----------------------------------------------------|------------|
| 2026-05-07 | Initial full platform scaffold created              | ForgeOps   |

> **How to update this file**: After making changes to any component, add a row to the Change Log and update the relevant section above. This keeps AI assistants and collaborators in sync without reading all the code.

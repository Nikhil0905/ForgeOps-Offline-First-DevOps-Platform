# ForgeOps — Living Project Context
> **Auto-update this file** whenever the project changes. It is the single source of truth for AI assistants, new contributors, and future you.

---

## 📌 Project Identity

| Field          | Value                                                   |
|----------------|---------------------------------------------------------|
| **Name**       | ForgeOps                                                |
| **Full Name**  | Fully Offline Resilient GitOps & CI/CD Platform         |
| **Repo**       | `github.com/Nikhil0905/ForgeOps-Offline-First-DevOps-Platform` |
| **Org Repo**   | `github.com/Nikhil0905/ForgeOps-Org-repo`               |
| **Created**    | 2026-05-07                                              |
| **Status**     | ✅ Complete                                              |
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
                                         │
                              [Sync Engine → GitHub]
                              (projects/* branches)
```

---

## 📦 Services & Ports

| Container                    | Image                    | Port(s)       | Role                        |
|------------------------------|--------------------------|---------------|-----------------------------
| `forgeops-nginx`             | nginx:1.25-alpine        | 80, 443       | Reverse proxy / router      |
| `forgeops-gitea`             | gitea/gitea:1.21         | 3000, 2222    | Local Git server            |
| `forgeops-jenkins`           | custom (jenkins/lts)     | 8080, 50000   | CI/CD engine                |
| `forgeops-registry`          | registry:2               | 5000          | Docker image store          |
| `forgeops-nexus`             | sonatype/nexus3          | 8081          | Maven dependency mirror     |
| `forgeops-prometheus`        | prom/prometheus          | 9090          | Metrics collection          |
| `forgeops-grafana`           | grafana/grafana          | 3001          | Metrics visualisation       |
| `forgeops-dashboard-api`     | custom (python:3.11)     | 5050          | Flask REST API              |
| `forgeops-dashboard-ui`      | custom (nginx)           | 8888          | SPA monitoring dashboard    |
| `forgeops-sync-engine`       | custom (python:3.11)     | —             | Internet-aware GitHub sync  |
| `forgeops-backup-engine`     | custom (alpine)          | —             | Scheduled backups           |
| `forgeops-deployment-engine` | custom (python:3.11)     | —             | Health-check deployer       |
| `forgeops-security-scanner`  | custom (python:3.11)     | —             | Secrets + image scanner     |

---

## 📁 File Map

```
forgeops/
├── context.md                          ← YOU ARE HERE
├── README.md                           ← User-facing documentation (with screenshots)
├── docker-compose.yml                  ← Full orchestration (13 services)
├── .env                                ← All credentials & config vars
├── .env.example                        ← Template for new deployments
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
│       └── prometheus.yml              ← Scrape targets config
│
├── services/
│   ├── sync-engine/
│   │   ├── sync.py                     ← Branch-based GitHub sync engine
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
│   │   ├── app.py                      ← Flask API (12 endpoints + /metrics)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/
│       ├── index.html                  ← SPA shell (7 pages)
│       ├── style.css                   ← Jenkins Classic theme
│       ├── app.js                      ← Fetch + render logic (SVG icons)
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
│   ├── sync.sh                         ← Manual sync trigger (shows status)
│   └── rollback.sh                     ← Emergency rollback
│
└── Screenshot_Visuals/                 ← Platform screenshots for README
    ├── ForgeOps-Dashboard.png
    ├── Celebration-app_Jenkins.png
    ├── grafana_dashboard.png
    ├── Gitea_Repos.png
    ├── jenkins_dashboard.png
    ├── nexus.png
    └── webpage_Test_success.png
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

## 🔄 Sync Strategy

The sync engine pushes each local Gitea repo as a **separate branch** in the single configured GitHub org repo:

```
Local Gitea repo                    GitHub (ForgeOps-Org-repo)
─────────────────                   ────────────────────────────
celebration-app         →           branch: projects/celebration-app
sample-python-app       →           branch: projects/sample-python-app
<any-new-project>       →           branch: projects/<new-project>
```

- **Single-repo PAT** — scoped to `ForgeOps-Org-repo` only, no broad permissions
- **Offline queue** — changes are queued in `queue.json` and replayed on reconnect
- **Auto-sync** — runs every 60 seconds (configurable via `SYNC_INTERVAL_SECONDS`)
- **Code review** — projects must go through PR review before merging to `main`

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
| 7     | UI modernization (SVG icons, branding) | ✅ Complete |
| 8     | GitHub sync (branch-based)  | ✅ Complete |

---

## 🎨 Dashboard UI

- **Theme**: Jenkins Classic (slate-based, monochrome palette)
- **Font**: Roboto (Google Fonts)
- **Icons**: Inline SVGs from `devicons` and `simple-icons` CDNs (no emojis)
- **Branding**: "ForgeOps — Offline First DevOps Platform" in top navbar
- **Layout**: Sidebar navigation (7 pages) + 3-column topbar (Brand | Context | Controls)

---

## 📝 Change Log

| Date       | Change                                              | By         |
|------------|-----------------------------------------------------|------------|
| 2026-05-07 | Initial full platform scaffold created              | ForgeOps   |
| 2026-05-14 | Dashboard UI modernized — SVG logos, branding       | ForgeOps   |
| 2026-05-14 | Sync engine fixed — branch-based per-repo sync      | ForgeOps   |
| 2026-05-14 | README moved to root with screenshot visuals        | ForgeOps   |
| 2026-05-14 | .env.example synced, data/ removed, docs/ cleaned   | ForgeOps   |

> **How to update this file**: After making changes to any component, add a row to the Change Log and update the relevant section above. This keeps AI assistants and collaborators in sync without reading all the code.

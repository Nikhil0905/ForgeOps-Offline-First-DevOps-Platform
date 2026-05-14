<div align="center">

# ⚙️ ForgeOps

### Offline-First DevOps Platform

**Build. Deploy. Monitor. — Even Without Internet.**

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Jenkins](https://img.shields.io/badge/Jenkins-CI%2FCD-D24939?style=for-the-badge&logo=jenkins&logoColor=white)](https://www.jenkins.io/)
[![Gitea](https://img.shields.io/badge/Gitea-Git%20Server-609926?style=for-the-badge&logo=gitea&logoColor=white)](https://gitea.io/)
[![Prometheus](https://img.shields.io/badge/Prometheus-Monitoring-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?style=for-the-badge&logo=grafana&logoColor=white)](https://grafana.com/)

---

*A fully self-hosted, containerized DevOps environment that operates completely offline — with automatic synchronization to GitHub when connectivity is restored.*

</div>

---

## 📸 Platform in Action

### Command Center Dashboard
> Real-time overview of service health, builds, deployments, and activity — all from a single pane of glass.

![ForgeOps Dashboard](Screenshot_Visuals/ForgeOps-Dashboard.png)

### Jenkins CI/CD Pipeline — Stage View
> Full multi-stage pipeline with Checkout → Build & Test → Publish to Nexus → Docker Build → Push to Registry → Deploy — all running locally.

![Jenkins CI/CD Pipeline](Screenshot_Visuals/Celebration-app_Jenkins.png)

### Grafana Monitoring — System Overview
> Real-time CI/CD pipeline analytics, build success rate, and infrastructure component health grid.

![Grafana Monitoring](Screenshot_Visuals/grafana_dashboard.png)

### Gitea — Local Git Repository
> Self-hosted Git server with full commit history, branch management, and webhook integration to Jenkins.

![Gitea Repository](Screenshot_Visuals/Gitea_Repos.png)

### Jenkins Dashboard — Build Overview
> All projects with build history, success/failure status, and executor monitoring.

![Jenkins Dashboard](Screenshot_Visuals/jenkins_dashboard.png)

### Deployed Application — End-to-End Success
> A fully built, tested, and deployed application running live — the complete CI/CD cycle working autonomously.

![Deployed Application](Screenshot_Visuals/webpage_Test_success.png)

---

## 🎯 What is ForgeOps?

ForgeOps is a **fully self-contained DevOps platform** that runs entirely offline. It provides Git hosting, CI/CD automation, Docker image management, Maven dependency mirroring, deployment automation, security scanning, and a monitoring dashboard — **all without any cloud dependency**.

When internet connectivity is detected, the **Sync Engine** automatically pushes all local repositories to GitHub as dedicated project branches — enabling code review, collaboration, and backup without manual intervention.

---

## 💡 Use Cases

| Scenario | Description |
|----------|-------------|
| **Air-Gapped Environments** | Develop, test, and deploy in networks completely isolated from the internet (defense, classified, edge) |
| **Local Development Labs** | Full-featured DevOps pipeline on a single machine — zero cloud costs |
| **Disaster-Resilient Infra** | Continue deploying autonomously during cloud outages or network partitions |
| **Enterprise Self-Hosting** | Complete data sovereignty — no third-party SaaS dependency |
| **Edge Computing** | Run CI/CD at the edge with intermittent connectivity and auto-sync |

---

## 🏗️ Architecture

```
┌──────────────┐     git push      ┌──────────────┐    webhook     ┌──────────────────┐
│  Developer   │ ──────────────▶   │  Gitea :3000  │ ────────────▶ │  Jenkins :8080   │
│              │                   │  (Git Server)  │               │  (CI/CD Engine)  │
└──────────────┘                   └──────────────┘               └────────┬─────────┘
                                                                           │
                     ┌─────────────────────────────────────────────────────┤
                     │                    │                    │           │
                     ▼                    ▼                    ▼           ▼
              ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ ┌─────────────┐
              │ Nexus :8081  │   │ Docker Build  │   │  Security    │ │ Deployment  │
              │ Maven Mirror │   │               │   │  Scanner     │ │ Engine      │
              └──────────────┘   └──────┬───────┘   └──────────────┘ └──────┬──────┘
                                        │                                    │
                                        ▼                                    ▼
                                ┌──────────────┐                    ┌──────────────┐
                                │ Registry     │                    │ Live App     │
                                │ :5000        │                    │ Container    │
                                └──────────────┘                    └──────────────┘
                                        │
              ┌─────────────────────────┤─────────────────────────────┐
              ▼                         ▼                             ▼
      ┌──────────────┐         ┌──────────────┐              ┌──────────────┐
      │ Dashboard    │         │ Prometheus   │              │ Sync Engine  │
      │ :8888        │         │ :9090        │              │ → GitHub     │
      └──────────────┘         └──────┬───────┘              └──────────────┘
                                      ▼
                               ┌──────────────┐
                               │ Grafana      │
                               │ :3001        │
                               └──────────────┘
```

---

## 📦 Services & Ports

| Container | Image | Port(s) | Role |
|-----------|-------|---------|------|
| `forgeops-nginx` | nginx:1.25-alpine | 80, 443 | Reverse proxy & router |
| `forgeops-gitea` | gitea/gitea:1.21 | 3000 | Local Git server |
| `forgeops-jenkins` | custom (jenkins/lts) | 8080, 50000 | CI/CD engine |
| `forgeops-registry` | registry:2 | 5000 | Docker image store |
| `forgeops-nexus` | sonatype/nexus3 | 8081 | Maven dependency mirror |
| `forgeops-prometheus` | prom/prometheus | 9090 | Metrics collection |
| `forgeops-grafana` | grafana/grafana | 3001 | Metrics visualisation |
| `forgeops-dashboard-api` | custom (python:3.11) | 5050 | Flask REST API |
| `forgeops-dashboard-ui` | custom (nginx) | 8888 | SPA monitoring dashboard |
| `forgeops-sync-engine` | custom (python:3.11) | — | Internet-aware GitHub sync |
| `forgeops-backup-engine` | custom (alpine) | — | Scheduled backups |
| `forgeops-deployment-engine` | custom (python:3.11) | — | Health-check deployer |
| `forgeops-security-scanner` | custom (python:3.11) | — | Secrets & image scanner |

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Nikhil0905/ForgeOps-Offline-First-DevOps-Platform.git
cd ForgeOps-Offline-First-DevOps-Platform

# 2. Configure environment
cp .env.example .env
nano .env    # Update credentials and GitHub PAT

# 3. Run the installer
bash scripts/install.sh

# 4. Open the dashboard
# http://localhost
```

---

## 🌐 Service URLs

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| **Dashboard** | http://localhost | — |
| **Gitea** | http://localhost/gitea/ | `forgeops` / `ForgeOps@2025` |
| **Jenkins** | http://localhost/jenkins/ | `admin` / `ForgeOps@Jenkins2025` |
| **Registry** | http://localhost:5000 | — |
| **Nexus** | http://localhost:8081 | `admin` / `ForgeOps@Nexus2025` |
| **Prometheus** | http://localhost:9090 | — |
| **Grafana** | http://localhost/grafana/ | `admin` / `ForgeOps@Grafana2025` |

> ⚠️ Change all default passwords in `.env` before production use.

---

## 🔄 GitHub Sync Strategy

ForgeOps includes an intelligent **Sync Engine** that bridges offline development with GitHub collaboration:

```
Local Gitea                              GitHub (ForgeOps-Org-repo)
┌──────────────────┐                     ┌──────────────────────────┐
│ celebration-app  │ ──── sync ────────▶ │ branch: projects/        │
│ sample-python-app│ ──── every 60s ───▶ │         celebration-app  │
│ <new-project>    │ ──── auto-create ─▶ │         sample-python-app│
└──────────────────┘                     │         <new-project>    │
                                         └──────────────────────────┘
```

- **Each project** syncs as a dedicated `projects/<name>` branch — never directly to `main`
- **Offline changes** are queued and replayed automatically when connectivity is restored
- **Single PAT** — only needs access to one repository, no broad permissions required
- **Code review enforced** — projects must go through PR review before merging to `main`

---

## 📁 Project Structure

```
forgeops/
├── docker-compose.yml              # Full orchestration (13 services)
├── .env                            # Credentials & configuration
├── .env.example                    # Template for new deployments
│
├── infrastructure/
│   ├── nginx/nginx.conf            # Reverse proxy routing
│   ├── registry/config.yml         # Docker registry v2 config
│   ├── jenkins/
│   │   ├── Dockerfile              # Jenkins + Docker CLI + Maven
│   │   ├── jenkins.yaml            # JCasC auto-configuration
│   │   └── plugins.txt             # Jenkins plugins
│   ├── gitea/app.ini               # Gitea offline config (SQLite)
│   └── monitoring/
│       └── prometheus.yml          # Scrape targets
│
├── services/
│   ├── sync-engine/                # Internet detection + GitHub sync
│   ├── backup-engine/              # Tar-based backup with rotation
│   ├── deployment-engine/          # Pull → run → healthcheck → rollback
│   ├── security-scanner/           # Regex secret scan + image checks
│   └── dependency-mirror/          # Nexus Maven bootstrap
│
├── dashboard/
│   ├── backend/app.py              # Flask REST API (12 endpoints)
│   └── frontend/                   # SPA dashboard (HTML/CSS/JS)
│
├── templates/                      # CI pipeline templates
│   ├── java-maven/Jenkinsfile
│   ├── nodejs/Jenkinsfile
│   └── python/Jenkinsfile
│
├── scripts/
│   ├── install.sh                  # Full bootstrap (run once)
│   ├── healthcheck.sh              # Verify all services
│   ├── sync.sh                     # Manual sync trigger
│   └── rollback.sh                 # Emergency rollback
│
└── Screenshot_Visuals/             # Platform screenshots
```

---

## 🛠️ Common Commands

```bash
# Start the platform
docker compose up -d

# Stop the platform
docker compose down

# View logs for a service
docker compose logs -f jenkins

# Run health check
bash scripts/healthcheck.sh

# Manual GitHub sync
bash scripts/sync.sh

# Emergency rollback
bash scripts/rollback.sh <service-name>

# Manual backup
docker exec forgeops-backup-engine /usr/local/bin/backup.sh

# Rebuild a single service
docker compose build dashboard-backend
docker compose up -d --no-deps dashboard-backend
```

---

## 📊 Dashboard API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/system-health` | Aggregate health of all services |
| GET | `/api/stats` | Summary stats for overview cards |
| GET | `/api/builds` | Jenkins build history |
| POST | `/api/builds/webhook` | Receive Jenkins build events |
| GET | `/api/deployments` | Deployment history |
| POST | `/api/deployments` | Record a deployment event |
| GET | `/api/repositories` | List Gitea repositories |
| GET | `/api/registry/images` | List local Docker images |
| GET | `/api/security-findings` | Security scan results |
| POST | `/api/security-findings` | Record scanner findings |
| GET | `/api/logs` | Combined event log stream |
| GET | `/api/sync-status` | Sync engine queue state |
| GET | `/metrics` | Prometheus metrics endpoint |

---

## 🔮 Future Enhancements

- [ ] AI-powered Jenkins log analysis (failure pattern detection)
- [ ] K3s offline Kubernetes cluster support
- [ ] Multi-node edge deployment
- [ ] USB/portable SSD mode for air-gapped transfers
- [ ] LDAP/SSO authentication integration
- [ ] Trivy offline vulnerability DB bundling
- [ ] Grafana dashboard JSON auto-provisioning

---

<div align="center">

**Built with ❤️ for environments where the internet is a luxury, not a given.**

*ForgeOps — Because your CI/CD pipeline shouldn't depend on someone else's cloud.*

</div>

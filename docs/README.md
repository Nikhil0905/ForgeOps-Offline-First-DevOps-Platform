# ForgeOps — Offline-First DevOps Platform

> **Self-hosted CI/CD for air-gapped, low-connectivity, and edge environments.**

---

## 🎯 What is ForgeOps?

ForgeOps is a fully self-contained DevOps platform that runs entirely offline. It provides Git hosting, CI/CD automation, Docker image management, Maven dependency mirroring, deployment automation, and a monitoring dashboard — all without any cloud dependency.

---

## 💡 Use Cases

ForgeOps is designed for scenarios where traditional cloud-based CI/CD platforms fall short:

- **Air-Gapped Environments:** Securely develop, test, and deploy applications in environments completely isolated from the public internet (e.g., defense, classified networks, or extreme edge computing).
- **Local Development Labs:** Spin up a full-featured, lightweight DevOps pipeline on a single machine to test integrations without incurring cloud provider costs.
- **Disaster-Resilient Infrastructure:** Continue deploying and monitoring critical applications autonomously, even during widespread cloud outages or network partitions.
- **Enterprise Self-Hosting:** Maintain absolute data sovereignty and control over your source code, deployment artifacts, and CI/CD pipelines without relying on third-party SaaS vendors.

---

## 🏗️ Architecture

```
Developer PC → Gitea (Git) → Jenkins (CI/CD) → Docker Registry → Deployed Container
                                    ↓
                           Nexus (Maven mirror)
                           Security Scanner
                           Dashboard (Flask + SPA)
                           Sync Engine (queued sync)
                           Backup Engine
```

---

## 🚀 Quick Start

```bash
# 1. Clone or copy ForgeOps to your machine
cd forgeops/

# 2. Review and adjust .env (credentials, ports)
nano .env

# 3. Run the installer
bash scripts/install.sh

# 4. Open the dashboard
http://localhost
```

---

## 🌐 Service URLs

| Service       | URL                          | Default Credentials         |
|---------------|------------------------------|-----------------------------|
| Dashboard     | http://localhost             | —                           |
| Gitea         | http://localhost/gitea/      | forgeops / ForgeOps@2025    |
| Jenkins       | http://localhost/jenkins/    | admin / ForgeOps@Jenkins2025|
| Registry      | http://localhost:5000        | —                           |
| Nexus         | http://localhost:8081        | admin / ForgeOps@Nexus2025  |
| Prometheus    | http://localhost:9090        | —                           |
| Grafana       | http://localhost/grafana/    | admin / ForgeOps@Grafana2025|

---

## 📁 Project Structure

```
forgeops/
├── docker-compose.yml          # Core orchestration
├── .env                        # Shared config & credentials
├── infrastructure/
│   ├── nginx/nginx.conf        # Reverse proxy
│   ├── registry/config.yml     # Docker registry
│   ├── jenkins/                # Jenkins image + JCasC
│   ├── gitea/app.ini           # Gitea config
│   └── monitoring/             # Prometheus + Grafana
├── services/
│   ├── sync-engine/            # Offline/online sync
│   ├── backup-engine/          # Scheduled backups
│   ├── deployment-engine/      # Health-check deployer
│   ├── security-scanner/       # Secrets + image scanner
│   └── dependency-mirror/      # Nexus Maven bootstrap
├── dashboard/
│   ├── backend/app.py          # Flask REST API
│   └── frontend/               # SPA dashboard UI
├── templates/
│   ├── java-maven/Jenkinsfile  # Maven CI pipeline
│   ├── nodejs/Jenkinsfile      # Node.js CI pipeline
│   └── python/Jenkinsfile      # Python CI pipeline
├── scripts/
│   ├── install.sh              # Full bootstrap
│   ├── healthcheck.sh          # Service verification
│   ├── sync.sh                 # Manual sync trigger
│   └── rollback.sh             # Emergency rollback
└── docs/README.md
```

---

## 🛠️ Basic Commands

To manage the platform, simply use standard Docker Compose commands from the project root:

```bash
# Start the platform in the background
docker compose up -d

# Stop and remove containers
docker compose down

# View logs for all services (press Ctrl+C to exit)
docker compose logs -f

# Run a full system health check
bash scripts/healthcheck.sh
```

---

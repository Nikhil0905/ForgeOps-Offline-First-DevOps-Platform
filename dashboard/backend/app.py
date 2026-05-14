#!/usr/bin/env python3
"""
ForgeOps Dashboard Backend API
================================
Flask REST API providing metrics and status aggregated from:
  - Jenkins (build history, pipeline status)
  - Gitea (repos, commits)
  - Docker Registry (images, tags)
  - Prometheus (system metrics)
  - Local SQLite (deployments, security findings)
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path

import requests
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# ── Config ────────────────────────────────────────────────────────────────────
FLASK_SECRET_KEY    = os.getenv("FLASK_SECRET_KEY", "forgeops-secret")
DB_PATH             = os.getenv("DB_PATH", "/data/forgeops.db")
JENKINS_URL         = os.getenv("JENKINS_URL", "http://jenkins:8080")
JENKINS_USER        = os.getenv("JENKINS_ADMIN_USER", "admin")
JENKINS_PASS        = os.getenv("JENKINS_ADMIN_PASSWORD", "ForgeOps@Jenkins2025")
GITEA_URL           = os.getenv("GITEA_URL", "http://gitea:3000")
REGISTRY_URL        = os.getenv("REGISTRY_URL", "http://registry:5000")
PROMETHEUS_URL      = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
PORT                = int(os.getenv("DASHBOARD_PORT", "5050"))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [API] %(levelname)s — %(message)s")
log = logging.getLogger("forgeops.api")

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
CORS(app)

# ── Prometheus metrics ────────────────────────────────────────────────────────
deployments_total = Counter("forgeops_deployments_total",
                            "Total deployments", ["service", "status"])
builds_total      = Counter("forgeops_builds_total",
                            "Total Jenkins builds", ["job", "result"])
active_containers = Gauge("forgeops_active_containers",
                          "Number of running containers")

# ── DB helpers ────────────────────────────────────────────────────────────────

def get_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS deployments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                service      TEXT NOT NULL,
                image        TEXT,
                status       TEXT NOT NULL,
                reason       TEXT,
                previous_image TEXT,
                started_at   TEXT,
                finished_at  TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS security_findings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                type         TEXT,
                label        TEXT,
                file         TEXT,
                line         INTEGER,
                snippet      TEXT,
                severity     TEXT,
                image        TEXT,
                reason       TEXT,
                scanned_at   TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS build_events (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                job          TEXT,
                build_number INTEGER,
                result       TEXT,
                duration_ms  INTEGER,
                triggered_at TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
    log.info("Database initialised at %s", DB_PATH)
    
    # Pre-populate metrics from DB
    try:
        with get_db() as db:
            # Builds
            rows = db.execute("SELECT job, result, COUNT(*) as count FROM build_events GROUP BY job, result").fetchall()
            for r in rows:
                builds_total.labels(job=r['job'], result=r['result']).inc(r['count'])
            
            # Deployments
            rows = db.execute("SELECT service, status, COUNT(*) as count FROM deployments GROUP BY service, status").fetchall()
            for r in rows:
                deployments_total.labels(service=r['service'], status=r['status']).inc(r['count'])
        log.info("Prometheus metrics initialised from database")
    except Exception as e:
        log.warning("Failed to pre-populate metrics: %s", e)



# ── External API helpers ──────────────────────────────────────────────────────

def jenkins_get(path: str) -> dict | None:
    try:
        r = requests.get(f"{JENKINS_URL}{path}",
                         auth=(JENKINS_USER, JENKINS_PASS), timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("Jenkins request failed: %s", e)
        return None


def gitea_get(path: str) -> dict | list | None:
    try:
        r = requests.get(f"{GITEA_URL}/api/v1{path}", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("Gitea request failed: %s", e)
        return None


def registry_get(path: str) -> dict | None:
    try:
        r = requests.get(f"{REGISTRY_URL}{path}", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("Registry request failed: %s", e)
        return None


def prometheus_query(query: str) -> dict | None:
    try:
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                         params={"query": query}, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("Prometheus query failed: %s", e)
        return None


# ── API Routes ────────────────────────────────────────────────────────────────

@app.route("/api/system-health")
def system_health():
    """Aggregate health of all ForgeOps services."""
    services = {}

    # Jenkins
    j = jenkins_get("/api/json?tree=mode,nodeDescription")
    services["jenkins"] = {"status": "up", "details": j} if j else {"status": "down"}

    # Gitea
    g = gitea_get("/repos/search?limit=1")
    services["gitea"] = {"status": "up", "repo_count": len(g.get("data", [])) if g else 0} \
        if g else {"status": "down"}

    # Registry
    reg = registry_get("/v2/_catalog")
    services["registry"] = {
        "status": "up",
        "image_count": len(reg.get("repositories", [])) if reg else 0
    } if reg else {"status": "down"}

    # Prometheus
    prom = prometheus_query("up")
    services["prometheus"] = {"status": "up"} if prom else {"status": "down"}

    overall = "healthy" if all(
        s["status"] == "up" for s in services.values()) else "degraded"

    return jsonify({
        "overall":    overall,
        "services":   services,
        "checked_at": datetime.utcnow().isoformat(),
    })


@app.route("/api/builds")
def get_builds():
    """Recent Jenkins build history across all jobs."""
    data = jenkins_get("/api/json?tree=jobs[name,lastBuild[number,result,duration,timestamp],lastFailedBuild[number]]")
    if not data:
        # Fallback: return from local DB
        with get_db() as db:
            rows = db.execute(
                "SELECT * FROM build_events ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
            return jsonify([dict(r) for r in rows])

    jobs = []
    for job in data.get("jobs", []):
        lb = job.get("lastBuild") or {}
        jobs.append({
            "job":          job.get("name"),
            "build_number": lb.get("number"),
            "result":       lb.get("result", "UNKNOWN"),
            "duration_ms":  lb.get("duration"),
            "timestamp":    lb.get("timestamp"),
        })
    return jsonify(jobs)


@app.route("/api/builds/webhook", methods=["POST"])
def build_webhook():
    """Receive build completion events from Jenkins."""
    body = request.get_json(silent=True) or {}
    with get_db() as db:
        db.execute(
            "INSERT INTO build_events (job, build_number, result, duration_ms, triggered_at) VALUES (?,?,?,?,?)",
            (body.get("job"), body.get("build_number"), body.get("result"),
             body.get("duration_ms"), body.get("triggered_at"))
        )
    result = body.get("result", "")
    builds_total.labels(job=body.get("job", "unknown"), result=result).inc()
    return jsonify({"status": "recorded"})


@app.route("/api/deployments", methods=["GET", "POST"])
def deployments():
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        with get_db() as db:
            db.execute(
                """INSERT INTO deployments
                   (service, image, status, reason, previous_image, started_at, finished_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (body.get("service"), body.get("image"), body.get("status"),
                 body.get("reason"), body.get("previous_image"),
                 body.get("started_at"), body.get("finished_at"))
            )
        status = body.get("status", "")
        deployments_total.labels(
            service=body.get("service", "unknown"), status=status).inc()
        return jsonify({"status": "recorded"})

    # GET
    limit = request.args.get("limit", 50, type=int)
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM deployments ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/security-findings", methods=["GET", "POST"])
def security_findings():
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        scanned_at = body.get("scanned_at", datetime.utcnow().isoformat())
        findings   = body.get("findings", [])
        with get_db() as db:
            db.execute("DELETE FROM security_findings")
            for f in findings:
                db.execute(
                    """INSERT INTO security_findings
                       (type,label,file,line,snippet,severity,image,reason,scanned_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (f.get("type"), f.get("label"), f.get("file"), f.get("line"),
                     f.get("snippet"), f.get("severity"), f.get("image"),
                     f.get("reason"), scanned_at)
                )
        return jsonify({"status": "recorded", "count": len(findings)})

    # GET
    limit = request.args.get("limit", 100, type=int)
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM security_findings ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/repositories")
def repositories():
    """List all Gitea repositories."""
    data = gitea_get("/repos/search?limit=50") # Use default sorting to avoid 422 errors
    if not data:
        return jsonify([])
    repos = []
    for r in data.get("data", []):
        repos.append({
            "name":         r.get("name"),
            "full_name":    r.get("full_name"),
            "clone_url":    r.get("clone_url"),
            "description":  r.get("description"),
            "stars":        r.get("stars_count"),
            "language":     r.get("language"),
            "updated_at":   r.get("updated"),
            "default_branch": r.get("default_branch"),
        })
    return jsonify(repos)


@app.route("/api/registry/images")
def registry_images():
    """List all images in the local Docker registry with tags."""
    catalog = registry_get("/v2/_catalog")
    if not catalog:
        return jsonify([])
    images = []
    for repo in catalog.get("repositories", []):
        tags_resp = registry_get(f"/v2/{repo}/tags/list")
        tags = tags_resp.get("tags") or [] if tags_resp else []
        images.append({"repository": repo, "tags": tags, "tag_count": len(tags)})
    return jsonify(images)


@app.route("/api/logs")
def logs():
    """Return recent deployment and build events as a combined log stream."""
    limit = request.args.get("limit", 100, type=int)
    with get_db() as db:
        builds = db.execute(
            "SELECT 'build' as event_type, job as name, result as status, created_at FROM build_events ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        deps = db.execute(
            "SELECT 'deployment' as event_type, service as name, status, created_at FROM deployments ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    combined = sorted(
        [dict(r) for r in list(builds) + list(deps)],
        key=lambda x: x["created_at"], reverse=True
    )[:limit]
    return jsonify(combined)


@app.route("/api/stats")
def stats():
    """Summary statistics for the dashboard overview cards."""
    with get_db() as db:
        total_builds = db.execute("SELECT COUNT(*) FROM build_events").fetchone()[0]
        success_builds = db.execute(
            "SELECT COUNT(*) FROM build_events WHERE result='SUCCESS'").fetchone()[0]
        total_deploys = db.execute("SELECT COUNT(*) FROM deployments").fetchone()[0]
        failed_deploys = db.execute(
            "SELECT COUNT(*) FROM deployments WHERE status NOT LIKE '%SUCCESS%'").fetchone()[0]
        security_issues = db.execute(
            "SELECT COUNT(*) FROM security_findings WHERE severity IN ('HIGH','CRITICAL')"
        ).fetchone()[0]

    # Registry image count
    catalog = registry_get("/v2/_catalog")
    image_count = len(catalog.get("repositories", [])) if catalog else 0

    # Gitea repo count
    repos_data = gitea_get("/repos/search?limit=50")
    repo_count = len(repos_data.get("data", [])) if repos_data else 0

    build_success_rate = round((success_builds / total_builds * 100), 1) if total_builds else 0

    return jsonify({
        "total_builds":        total_builds,
        "build_success_rate":  build_success_rate,
        "total_deployments":   total_deploys,
        "failed_deployments":  failed_deploys,
        "security_issues":     security_issues,
        "registry_images":     image_count,
        "git_repositories":    repo_count,
        "updated_at":          datetime.utcnow().isoformat(),
    })


@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/api/sync-status")
def sync_status():
    """Read sync engine queue state."""
    queue_file = os.getenv("QUEUE_FILE", "/data/queue.json")
    try:
        data = json.loads(Path(queue_file).read_text()) if Path(queue_file).exists() else {}
    except Exception:
        data = {}
    return jsonify(data)


# ── Start ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    log.info("ForgeOps Dashboard API starting on port %d", PORT)
    app.run(host="0.0.0.0", port=PORT, debug=False)

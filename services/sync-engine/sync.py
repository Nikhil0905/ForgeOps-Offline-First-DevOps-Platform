#!/usr/bin/env python3
"""
ForgeOps Sync Engine
====================
Detects internet connectivity and synchronises local Gitea repositories
with remote Git servers. All pending changes are queued in queue.json
and replayed when connectivity is restored.
"""

import os
import json
import time
import socket
import logging
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
SYNC_INTERVAL   = int(os.getenv("SYNC_INTERVAL_SECONDS", "60"))
REMOTE_GIT_URL  = os.getenv("REMOTE_GIT_URL", "")
GITEA_URL       = os.getenv("GITEA_URL", "http://gitea:3000")
GITEA_USER      = os.getenv("GITEA_ADMIN_USER", "forgeops")
GITEA_PASS      = os.getenv("GITEA_ADMIN_PASSWORD", "ForgeOps@2025")
QUEUE_FILE      = os.getenv("QUEUE_FILE", "/data/queue.json")
CHECK_HOSTS     = [("8.8.8.8", 53), ("1.1.1.1", 53)]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SYNC] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("forgeops.sync")

# ── Queue helpers ────────────────────────────────────────────────────────────

def load_queue() -> dict:
    path = Path(QUEUE_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    return {"pending_commits": [], "pending_images": [], "pending_logs": [], "last_sync": None}


def save_queue(queue: dict) -> None:
    Path(QUEUE_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(QUEUE_FILE).write_text(json.dumps(queue, indent=2))


def enqueue(category: str, payload: dict) -> None:
    queue = load_queue()
    payload["queued_at"] = datetime.utcnow().isoformat()
    queue.setdefault(category, []).append(payload)
    save_queue(queue)
    log.info("Queued %s: %s", category, payload)


def dequeue_all(category: str) -> list:
    queue = load_queue()
    items = queue.pop(category, [])
    save_queue(queue)
    return items

# ── Network detection ────────────────────────────────────────────────────────

def internet_available() -> bool:
    for host, port in CHECK_HOSTS:
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except OSError:
            pass
    return False

# ── Gitea helpers ────────────────────────────────────────────────────────────

def get_local_repos() -> list:
    try:
        resp = requests.get(
            f"{GITEA_URL}/api/v1/repos/search?limit=50",
            auth=(GITEA_USER, GITEA_PASS),
            timeout=10,
        )
        resp.raise_for_status()
        return [r["clone_url"] for r in resp.json().get("data", [])]
    except Exception as exc:
        log.warning("Could not fetch Gitea repos: %s", exc)
        return []

# ── Sync operations ──────────────────────────────────────────────────────────

def run(cmd: list, cwd: str = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def sync_repo(local_url: str, remote_url: str) -> bool:
    """Mirror-push a local Gitea repo to remote."""
    try:
        repo_name = local_url.rstrip("/").split("/")[-1]
        work_dir  = f"/tmp/sync_{repo_name}"

        # Fix local URL for internal container network
        # Replaces 'localhost/gitea' or similar with 'gitea:3000'
        internal_local_url = local_url.replace("localhost/gitea", "gitea:3000")
        if "localhost" in local_url and "gitea:3000" not in internal_local_url:
             internal_local_url = local_url.replace("localhost", "gitea:3000")

        # Cleanup old work dir if exists
        if os.path.exists(work_dir):
            subprocess.run(["rm", "-rf", work_dir])

        # Clone bare local repo
        result_clone = run(["git", "clone", "--mirror", internal_local_url, work_dir])
        if result_clone.returncode != 0:
            log.warning("Clone failed for %s: %s", repo_name, result_clone.stderr)
            return False

        # Push to remote
        result = run(["git", "push", "--mirror", remote_url], cwd=work_dir)
        if result.returncode == 0:
            log.info("✅ Synced %s → %s", repo_name, remote_url)
            return True
        else:
            log.warning("Push failed for %s: %s", repo_name, result.stderr)
            return False
    except Exception as exc:
        log.error("sync_repo error: %s", exc)
        return False


def process_queue() -> None:
    """Replay all queued operations now that internet is available."""
    pending_commits = dequeue_all("pending_commits")
    pending_images  = dequeue_all("pending_images")

    if not pending_commits and not pending_images:
        log.info("Queue is empty — nothing to replay.")
        return

    log.info("Replaying %d pending commit(s) and %d pending image(s)",
             len(pending_commits), len(pending_images))

    for item in pending_commits:
        log.info("Processing queued commit: %s", item)
        # Hook: trigger a git push to the remote for each repo
        if REMOTE_GIT_URL:
            local_repos = get_local_repos()
            for repo_url in local_repos:
                sync_repo(repo_url, REMOTE_GIT_URL)

    for item in pending_images:
        log.info("Processing queued image push: %s", item)
        image_tag = item.get("image_tag")
        remote    = item.get("remote")
        if image_tag and remote:
            result = run(["docker", "push", f"{remote}/{image_tag}"])
            if result.returncode == 0:
                log.info("✅ Image pushed: %s", image_tag)
            else:
                log.warning("Image push failed: %s", result.stderr)

# ── Main loop ────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("ForgeOps Sync Engine started — interval=%ds", SYNC_INTERVAL)
    while True:
        online = internet_available()
        log.info("Internet: %s", "✅ ONLINE" if online else "❌ OFFLINE")

        if online:
            process_queue()

            # Sync all local repos to remote if configured
            if REMOTE_GIT_URL:
                for repo_url in get_local_repos():
                    if not sync_repo(repo_url, REMOTE_GIT_URL):
                        enqueue("pending_commits", {"repo": repo_url, "remote": REMOTE_GIT_URL})
        else:
            log.info("Offline mode — changes will be queued until connectivity is restored.")
            # Record the offline event in queue for dashboard visibility
            queue = load_queue()
            queue["last_offline"] = datetime.utcnow().isoformat()
            queue["online"] = False
            save_queue(queue)

        # Update last_sync timestamp
        queue = load_queue()
        queue["last_sync"]  = datetime.utcnow().isoformat()
        queue["online"]     = online
        save_queue(queue)

        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()

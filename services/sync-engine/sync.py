#!/usr/bin/env python3
"""
ForgeOps Sync Engine
====================
Detects internet connectivity and synchronises local Gitea repositories
with the remote GitHub repository. Each local Gitea project is pushed as
a separate branch (projects/<repo-name>) in the single configured remote
repo, keeping your PAT scoped to just one repository.

All pending changes are queued in queue.json and replayed when
connectivity is restored.
"""

import os
import json
import time
import socket
import logging
import subprocess
import urllib.parse
import requests
from datetime import datetime
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
SYNC_INTERVAL   = int(os.getenv("SYNC_INTERVAL_SECONDS", "60"))
REMOTE_GIT_URL  = os.getenv("REMOTE_GIT_URL", "")
GITEA_URL       = os.getenv("GITEA_URL", "http://localhost/gitea")
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
    """Return list of dicts with clone_url and name for each local Gitea repo."""
    try:
        resp = requests.get(
            f"{GITEA_URL}/api/v1/repos/search?limit=50",
            auth=(GITEA_USER, GITEA_PASS),
            timeout=10,
        )
        resp.raise_for_status()
        repos = []
        for r in resp.json().get("data", []):
            repos.append({
                "clone_url": r["clone_url"],
                "name": r["name"],
                "full_name": r.get("full_name", r["name"]),
            })
        return repos
    except Exception as exc:
        log.warning("Could not fetch Gitea repos: %s", exc)
        return []

# ── Sync operations ──────────────────────────────────────────────────────────

def run(cmd: list, cwd: str = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def sync_repo(repo_info: dict, remote_url: str) -> bool:
    """Push a local Gitea repo as a dedicated branch in the single remote GitHub repo.

    Strategy:
    - Clone the local Gitea repo normally
    - Add the remote GitHub repo as 'github' remote
    - Push all local branches to the remote under the prefix 'projects/<repo_name>/'
    - The main branch becomes 'projects/<repo_name>' on GitHub

    This keeps every project separated as its own branch in one GitHub repo,
    so a single-repo PAT is sufficient.
    """
    clone_url  = repo_info["clone_url"]
    repo_name  = repo_info["name"]                          # e.g. "celebration-app"
    work_dir   = f"/tmp/sync_{repo_name}"
    branch_name = f"projects/{repo_name}"

    try:
        # Fix local URL for internal Docker network
        internal_url = clone_url.replace("localhost/gitea", "gitea:3000")
        if "localhost" in clone_url and "gitea:3000" not in internal_url:
            internal_url = clone_url.replace("localhost", "gitea:3000")

        # Inject Gitea credentials
        encoded_user = urllib.parse.quote(GITEA_USER, safe='')
        encoded_pass = urllib.parse.quote(GITEA_PASS, safe='')
        internal_url = internal_url.replace("http://", f"http://{encoded_user}:{encoded_pass}@")

        # Cleanup
        if os.path.exists(work_dir):
            subprocess.run(["rm", "-rf", work_dir])

        # Clone the local repo (full, not bare)
        result = run(["git", "clone", internal_url, work_dir])
        if result.returncode != 0:
            log.warning("Clone failed for %s: %s", repo_name, result.stderr)
            return False

        # Add GitHub as a remote
        result = run(["git", "remote", "add", "github", remote_url], cwd=work_dir)
        if result.returncode != 0:
            # Remote might already exist, try setting the URL
            run(["git", "remote", "set-url", "github", remote_url], cwd=work_dir)

        # Detect default branch of local repo
        result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=work_dir)
        local_branch = result.stdout.strip() or "main"

        # Push the default branch as projects/<repo_name>
        result = run(
            ["git", "push", "github", f"{local_branch}:{branch_name}", "--force"],
            cwd=work_dir,
        )
        if result.returncode == 0:
            log.info("Synced %s -> branch '%s'", repo_name, branch_name)
        else:
            log.warning("Push failed for %s: %s", repo_name, result.stderr)
            return False

        # Also push any additional branches under projects/<repo_name>/<branch>
        result = run(["git", "branch", "-r", "--list", "origin/*"], cwd=work_dir)
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                remote_branch = line.strip()
                if not remote_branch or "->" in remote_branch:
                    continue
                short_branch = remote_branch.replace("origin/", "")
                if short_branch == local_branch:
                    continue  # Already pushed as the main project branch
                target = f"projects/{repo_name}/{short_branch}"
                run(
                    ["git", "push", "github", f"{remote_branch}:{target}", "--force"],
                    cwd=work_dir,
                )

        return True

    except Exception as exc:
        log.error("sync_repo error for %s: %s", repo_name, exc)
        return False
    finally:
        # Cleanup work directory
        if os.path.exists(work_dir):
            subprocess.run(["rm", "-rf", work_dir])


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
        repo_info = {
            "clone_url": item.get("repo", ""),
            "name": item.get("name", ""),
        }
        if not repo_info["name"] and repo_info["clone_url"]:
            repo_info["name"] = repo_info["clone_url"].rstrip("/").split("/")[-1].replace(".git", "")
        remote_url = item.get("remote", REMOTE_GIT_URL)
        if repo_info["clone_url"] and remote_url:
            sync_repo(repo_info, remote_url)

    for item in pending_images:
        log.info("Processing queued image push: %s", item)
        image_tag = item.get("image_tag")
        remote    = item.get("remote")
        if image_tag and remote:
            result = run(["docker", "push", f"{remote}/{image_tag}"])
            if result.returncode == 0:
                log.info("Image pushed: %s", image_tag)
            else:
                log.warning("Image push failed: %s", result.stderr)

# ── Main loop ────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("ForgeOps Sync Engine started — interval=%ds", SYNC_INTERVAL)
    log.info("Remote: %s", REMOTE_GIT_URL.split("@")[-1] if "@" in REMOTE_GIT_URL else "(not set)")
    log.info("Strategy: Each local repo -> separate branch in single remote repo")

    while True:
        online = internet_available()
        log.info("Internet: %s", "ONLINE" if online else "OFFLINE")

        if online:
            process_queue()

            # Sync all local repos to remote if configured
            if REMOTE_GIT_URL:
                repos = get_local_repos()
                log.info("Found %d local Gitea repo(s) to sync", len(repos))
                for repo_info in repos:
                    if not sync_repo(repo_info, REMOTE_GIT_URL):
                        enqueue("pending_commits", {
                            "repo": repo_info["clone_url"],
                            "name": repo_info["name"],
                            "remote": REMOTE_GIT_URL,
                        })
        else:
            log.info("Offline mode — changes will be queued until connectivity is restored.")
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

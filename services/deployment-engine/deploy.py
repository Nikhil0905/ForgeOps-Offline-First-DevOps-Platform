#!/usr/bin/env python3
"""
ForgeOps Deployment Engine
===========================
Deploys Docker images from the local registry with:
- Health-check verification
- Automatic rollback on failure
- Deployment state reporting to dashboard API
"""

import os
import time
import json
import logging
import subprocess
import requests
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
REGISTRY_HOST   = os.getenv("REGISTRY_HOST", "registry:5000")
DASHBOARD_API   = os.getenv("DASHBOARD_API", "http://dashboard-backend:5050")
HEALTHCHECK_RETRIES   = 5
HEALTHCHECK_INTERVAL  = 10  # seconds between retries
ROLLBACK_LABEL  = "forgeops.previous_image"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DEPLOY] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("forgeops.deploy")

# ── Docker helpers ────────────────────────────────────────────────────────────

def docker(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["docker"] + list(args), capture_output=True, text=True)


def get_running_container(name: str) -> str | None:
    result = docker("inspect", "--format", "{{.Id}}", name)
    return result.stdout.strip() if result.returncode == 0 else None


def get_container_image(name: str) -> str | None:
    result = docker("inspect", "--format", "{{.Config.Image}}", name)
    return result.stdout.strip() if result.returncode == 0 else None


def container_healthy(name: str) -> bool:
    """Check container is running and passing its healthcheck."""
    result = docker("inspect", "--format",
                    "{{.State.Status}} {{.State.Health.Status}}", name)
    if result.returncode != 0:
        return False
    parts = result.stdout.strip().split()
    status  = parts[0] if parts else ""
    health  = parts[1] if len(parts) > 1 else "none"
    log.info("Container %s — status=%s health=%s", name, status, health)
    return status == "running" and health in ("healthy", "none")


def pull_image(image: str) -> bool:
    log.info("Pulling image: %s", image)
    result = docker("pull", image)
    if result.returncode != 0:
        log.error("Pull failed: %s", result.stderr)
        return False
    return True


def run_container(name: str, image: str, extra_args: list = None) -> bool:
    log.info("Starting container %s from %s", name, image)
    cmd = ["run", "-d", "--name", name, "--restart", "unless-stopped"]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(image)
    result = docker(*cmd)
    if result.returncode != 0:
        log.error("Run failed: %s", result.stderr)
        return False
    return True


def stop_and_remove(name: str) -> None:
    docker("stop", name)
    docker("rm", "-f", name)

# ── Dashboard reporting ───────────────────────────────────────────────────────

def report_deployment(payload: dict) -> None:
    try:
        requests.post(f"{DASHBOARD_API}/api/deployments",
                      json=payload, timeout=5)
    except Exception as exc:
        log.warning("Dashboard report failed: %s", exc)

# ── Core deploy logic ─────────────────────────────────────────────────────────

def deploy(name: str, image: str, extra_args: list = None) -> bool:
    """
    Deploy a container with health-check + auto rollback.
    Returns True if deployment succeeded.
    """
    log.info("═══ Deploying %s → %s ═══", name, image)
    started_at     = datetime.utcnow().isoformat()
    previous_image = get_container_image(name)

    # Pull new image
    if not pull_image(f"{REGISTRY_HOST}/{image}"):
        report_deployment({
            "service": name, "image": image,
            "status": "FAILED", "reason": "image_pull_failed",
            "started_at": started_at, "finished_at": datetime.utcnow().isoformat()
        })
        return False

    # Stop existing container
    if get_running_container(name):
        log.info("Stopping existing container: %s", name)
        stop_and_remove(name)

    # Start new container
    full_image = f"{REGISTRY_HOST}/{image}"
    if not run_container(name, full_image, extra_args):
        log.error("Failed to start container — attempting rollback...")
        _rollback(name, previous_image, started_at)
        return False

    # Health check loop
    log.info("Running health checks (%d retries, %ds interval)...",
             HEALTHCHECK_RETRIES, HEALTHCHECK_INTERVAL)
    for attempt in range(1, HEALTHCHECK_RETRIES + 1):
        time.sleep(HEALTHCHECK_INTERVAL)
        if container_healthy(name):
            log.info("✅ Health check passed (attempt %d/%d)", attempt, HEALTHCHECK_RETRIES)
            report_deployment({
                "service": name, "image": image,
                "status": "SUCCESS", "previous_image": previous_image,
                "started_at": started_at, "finished_at": datetime.utcnow().isoformat()
            })
            return True
        log.warning("Health check failed (attempt %d/%d)", attempt, HEALTHCHECK_RETRIES)

    # All checks failed → rollback
    log.error("❌ All health checks failed — rolling back to %s", previous_image)
    _rollback(name, previous_image, started_at)
    return False


def _rollback(name: str, previous_image: str | None, started_at: str) -> None:
    if not previous_image:
        log.warning("No previous image to rollback to — leaving container stopped.")
        report_deployment({
            "service": name, "status": "ROLLBACK_FAILED",
            "reason": "no_previous_image", "started_at": started_at,
            "finished_at": datetime.utcnow().isoformat()
        })
        return

    log.info("Rolling back %s → %s", name, previous_image)
    stop_and_remove(name)
    result = docker("run", "-d", "--name", name,
                    "--restart", "unless-stopped", previous_image)
    if result.returncode == 0:
        log.info("✅ Rollback successful")
        report_deployment({
            "service": name, "image": previous_image,
            "status": "ROLLBACK_SUCCESS", "started_at": started_at,
            "finished_at": datetime.utcnow().isoformat()
        })
    else:
        log.error("❌ Rollback also failed: %s", result.stderr)
        report_deployment({
            "service": name, "status": "ROLLBACK_FAILED",
            "reason": result.stderr, "started_at": started_at,
            "finished_at": datetime.utcnow().isoformat()
        })

# ── CLI / API entrypoint ──────────────────────────────────────────────────────

def main() -> None:
    """
    Example: called by Jenkins post-build via HTTP trigger or CLI.
    Usage:  python deploy.py <service-name> <image:tag>
    """
    import sys
    if len(sys.argv) < 3:
        print("Usage: deploy.py <service-name> <image:tag> [extra docker args...]")
        sys.exit(1)

    service = sys.argv[1]
    image   = sys.argv[2]
    extra   = sys.argv[3:] if len(sys.argv) > 3 else None
    success = deploy(service, image, extra)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

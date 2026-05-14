#!/usr/bin/env python3
"""
ForgeOps Offline Security Scanner
===================================
Scans for:
  1. Hardcoded secrets in source files (API keys, passwords, tokens)
  2. Vulnerable/outdated base images in Docker registry
  3. Exposed credentials patterns in Dockerfiles & config files
Reports findings to the dashboard API.
"""

import os
import re
import json
import time
import logging
import subprocess
import requests
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
REGISTRY_HOST  = os.getenv("REGISTRY_HOST", "registry:5000")
DASHBOARD_API  = os.getenv("DASHBOARD_API", "http://dashboard-backend:5050")
SCAN_INTERVAL  = int(os.getenv("SCAN_INTERVAL_SECONDS", "3600"))   # 1 hour
SCAN_PATHS     = os.getenv("SCAN_PATHS", "/registry").split(",")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCANNER] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("forgeops.scanner")

# ── Secret patterns ───────────────────────────────────────────────────────────
SECRET_PATTERNS = [
    # Generic API keys / tokens
    (r'(?i)(api[_\-]?key|apikey)\s*[=:]\s*["\']?([A-Za-z0-9_\-]{20,})["\']?',
     "Generic API Key"),
    # AWS keys
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'(?i)aws[_\-]?secret[_\-]?access[_\-]?key\s*[=:]\s*["\']?([A-Za-z0-9/+=]{40})["\']?',
     "AWS Secret Key"),
    # Passwords in env / config
    (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?([^\s"\']{6,})["\']?',
     "Hardcoded Password"),
    # Private keys
    (r'-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----', "Private Key Block"),
    # JWT tokens
    (r'eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}',
     "JWT Token"),
    # GitHub / GitLab tokens
    (r'gh[pousr]_[A-Za-z0-9]{36}', "GitHub Token"),
    (r'glpat-[A-Za-z0-9\-_]{20}', "GitLab Token"),
    # Generic secrets
    (r'(?i)(secret|token)\s*[=:]\s*["\']?([A-Za-z0-9_\-]{12,})["\']?',
     "Generic Secret/Token"),
    # Database connection strings
    (r'(?i)(postgres|mysql|mongodb):\/\/[^:]+:[^@]+@', "Database Credentials in URL"),
    # Docker Hub / registry credentials
    (r'(?i)docker[_\-]?password\s*[=:]\s*["\']?([^\s"\']{6,})["\']?',
     "Docker Registry Password"),
]

# File extensions to scan
SCAN_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".go", ".rb", ".php",
    ".sh", ".bash", ".env", ".yaml", ".yml", ".json",
    ".xml", ".properties", ".ini", ".conf", ".cfg",
    "Dockerfile", ".dockerfile",
}

# Paths to exclude
EXCLUDE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv",
    "vendor", "target", ".m2", "dist", "build",
}

# ── Known vulnerable base images ──────────────────────────────────────────────
KNOWN_VULNERABLE_IMAGES = {
    "ubuntu:18.04": "End-of-life Ubuntu — use 22.04+",
    "ubuntu:16.04": "End-of-life Ubuntu — use 22.04+",
    "python:2.7":   "Python 2.7 is EOL",
    "node:10":      "Node.js 10 is EOL",
    "node:12":      "Node.js 12 is EOL",
    "alpine:3.12":  "Alpine 3.12 EOL",
}

# ── Secret scanning ───────────────────────────────────────────────────────────

def should_scan_file(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return False
    return path.suffix in SCAN_EXTENSIONS or path.name in SCAN_EXTENSIONS


def scan_file_for_secrets(filepath: Path) -> list:
    findings = []
    try:
        content = filepath.read_text(errors="replace")
        for pattern, label in SECRET_PATTERNS:
            for match in re.finditer(pattern, content):
                line_no = content[:match.start()].count("\n") + 1
                findings.append({
                    "type":     "SECRET",
                    "label":    label,
                    "file":     str(filepath),
                    "line":     line_no,
                    "snippet":  match.group(0)[:60] + "…",  # truncate for safety
                    "severity": "HIGH",
                })
    except Exception as exc:
        log.debug("Could not read %s: %s", filepath, exc)
    return findings


def scan_directory(path: str) -> list:
    findings = []
    root = Path(path)
    if not root.exists():
        log.warning("Scan path does not exist: %s", path)
        return findings

    for fpath in root.rglob("*"):
        if fpath.is_file() and should_scan_file(fpath):
            findings.extend(scan_file_for_secrets(fpath))

    return findings

# ── Registry image scanning ───────────────────────────────────────────────────

def list_registry_images() -> list:
    """List all images from local Docker registry."""
    images = []
    try:
        resp = requests.get(f"http://{REGISTRY_HOST}/v2/_catalog", timeout=10)
        repos = resp.json().get("repositories", [])
        for repo in repos:
            tags_resp = requests.get(
                f"http://{REGISTRY_HOST}/v2/{repo}/tags/list", timeout=10)
            tags = tags_resp.json().get("tags") or []
            for tag in tags:
                images.append(f"{repo}:{tag}")
    except Exception as exc:
        log.warning("Could not list registry images: %s", exc)
    return images


def check_image_vulnerabilities(images: list) -> list:
    findings = []
    for image in images:
        # Check against known-vulnerable list
        base = image.split("/")[-1]  # strip registry prefix
        for vuln_image, reason in KNOWN_VULNERABLE_IMAGES.items():
            if vuln_image in base:
                findings.append({
                    "type":     "VULNERABLE_IMAGE",
                    "image":    image,
                    "reason":   reason,
                    "severity": "MEDIUM",
                })

        # Try Trivy if installed (optional)
        trivy = subprocess.run(
            ["which", "trivy"], capture_output=True)
        if trivy.returncode == 0:
            result = subprocess.run(
                ["trivy", "image", "--format", "json",
                 "--exit-code", "0", f"{REGISTRY_HOST}/{image}"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                try:
                    data   = json.loads(result.stdout)
                    vulns  = []
                    for r in data.get("Results", []):
                        vulns.extend(r.get("Vulnerabilities") or [])
                    critical = [v for v in vulns if v.get("Severity") == "CRITICAL"]
                    high     = [v for v in vulns if v.get("Severity") == "HIGH"]
                    if critical or high:
                        findings.append({
                            "type":     "TRIVY_SCAN",
                            "image":    image,
                            "critical": len(critical),
                            "high":     len(high),
                            "severity": "CRITICAL" if critical else "HIGH",
                        })
                except json.JSONDecodeError:
                    pass

    return findings

# ── Reporting ─────────────────────────────────────────────────────────────────

def report_findings(findings: list) -> None:
    if not findings:
        log.info("✅ No security findings — clean scan.")
        return

    log.warning("🔴 Found %d security issue(s)!", len(findings))
    for f in findings:
        log.warning("  [%s] %s — %s", f.get("severity"), f.get("type"),
                    f.get("label") or f.get("reason") or f.get("image"))

    try:
        requests.post(
            f"{DASHBOARD_API}/api/security-findings",
            json={"findings": findings, "scanned_at": datetime.utcnow().isoformat()},
            timeout=10,
        )
        log.info("Findings reported to dashboard.")
    except Exception as exc:
        log.warning("Could not report to dashboard: %s", exc)

# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("ForgeOps Security Scanner started — interval=%ds", SCAN_INTERVAL)
    while True:
        log.info("═══ Starting security scan ═══")
        all_findings = []

        # 1. Scan configured source paths for secrets
        for path in SCAN_PATHS:
            log.info("Scanning path: %s", path)
            all_findings.extend(scan_directory(path.strip()))

        # 2. Scan registry images
        log.info("Scanning Docker registry images...")
        images   = list_registry_images()
        all_findings.extend(check_image_vulnerabilities(images))

        report_findings(all_findings)
        log.info("Scan complete — next scan in %ds", SCAN_INTERVAL)
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()

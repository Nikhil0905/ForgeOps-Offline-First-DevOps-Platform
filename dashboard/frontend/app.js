/* ============================================================
   ForgeOps Dashboard — Frontend Application Logic
   Polls all API endpoints and renders the UI dynamically
   ============================================================ */

const API = window.location.port === '8888'
  ? 'http://localhost:5050'
  : '/api';

const REFRESH_INTERVAL_MS = 30_000;  // 30s auto-refresh

// ── State ────────────────────────────────────────────────────
let currentPage  = 'overview';
let refreshTimer = null;

// ── Page Metadata ────────────────────────────────────────────
const PAGE_META = {
  overview:     { title: 'System Overview',      subtitle: 'Real-time platform health' },
  builds:       { title: 'Build History',        subtitle: 'Jenkins CI pipeline runs'  },
  deployments:  { title: 'Deployment History',   subtitle: 'Container deployment log'  },
  repositories: { title: 'Git Repositories',     subtitle: 'Hosted on local Gitea'     },
  registry:     { title: 'Docker Registry',      subtitle: 'Local image storage'        },
  security:     { title: 'Security Findings',    subtitle: 'Offline vulnerability scan' },
  logs:         { title: 'Event Log Stream',     subtitle: 'Combined build & deploy log'},
};

// ── Utility ──────────────────────────────────────────────────
async function fetchJSON(path) {
  try {
    const res = await fetch(`${API}${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn(`[ForgeOps] fetch failed: ${path}`, e.message);
    return null;
  }
}

function fmtTime(ts) {
  if (!ts) return '—';
  try {
    // Handle space-separated dates from SQLite (e.g. 2026-05-14 01:19:15)
    const cleanTs = typeof ts === 'string' ? ts.replace(' ', 'T') : ts;
    const d = new Date(cleanTs);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleString('en-GB', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
    });
  } catch { return ts; }
}

function fmtDuration(ms) {
  if (!ms) return '—';
  const s = Math.floor(ms / 1000);
  if (s < 60)  return `${s}s`;
  if (s < 3600) return `${Math.floor(s/60)}m ${s%60}s`;
  return `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`;
}

function resultBadge(result) {
  const r = (result || 'UNKNOWN').toUpperCase();
  return `<span class="result-badge result-${r}">${r}</span>`;
}

function emptyState(icon, text) {
  return `<div class="empty-state"><div class="empty-icon">${icon}</div><div class="empty-text">${text}</div></div>`;
}

// SVG icon helpers for empty states and dynamic content
const ICONS = {
  builds: '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>',
  deploys: '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>',
  repos: '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>',
  docker: '<svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor"><path d="M13.983 11.078h2.119a.186.186 0 0 0 .186-.185V9.006a.186.186 0 0 0-.186-.186h-2.119a.185.185 0 0 0-.185.185v1.888c0 .102.083.185.185.185m-2.954-5.43h2.118a.186.186 0 0 0 .186-.186V3.574a.186.186 0 0 0-.186-.185h-2.118a.185.185 0 0 0-.185.185v1.888c0 .102.082.185.185.186m0 2.716h2.118a.187.187 0 0 0 .186-.186V6.29a.186.186 0 0 0-.186-.185h-2.118a.185.185 0 0 0-.185.185v1.887c0 .102.082.186.185.186m-2.93 0h2.12a.186.186 0 0 0 .184-.186V6.29a.185.185 0 0 0-.185-.185H8.1a.185.185 0 0 0-.185.185v1.887c0 .102.083.186.185.186m-2.964 0h2.119a.186.186 0 0 0 .185-.186V6.29a.186.186 0 0 0-.185-.185H5.136a.186.186 0 0 0-.186.185v1.887c0 .102.084.186.186.186m5.893 2.715h2.118a.186.186 0 0 0 .186-.185V9.006a.186.186 0 0 0-.186-.186h-2.118a.185.185 0 0 0-.185.185v1.888c0 .102.082.185.185.185m-2.93 0h2.12a.185.185 0 0 0 .184-.185V9.006a.185.185 0 0 0-.184-.186h-2.12a.185.185 0 0 0-.184.185v1.888c0 .102.083.185.185.185m-2.964 0h2.119a.185.185 0 0 0 .185-.185V9.006a.186.186 0 0 0-.185-.186H5.136a.186.186 0 0 0-.186.186v1.887c0 .102.084.185.186.185m-2.92 0h2.12a.185.185 0 0 0 .184-.185V9.006a.186.186 0 0 0-.184-.186h-2.12a.185.185 0 0 0-.184.186v1.887c0 .102.082.185.185.185M23.763 9.89c-.065-.051-.672-.51-1.954-.51-.338.001-.676.03-1.01.087-.248-1.7-1.653-2.53-1.716-2.566l-.344-.199-.227.328c-.29.419-.5.873-.62 1.349-.257 1.003-.124 1.943.383 2.749-.566.32-1.485.5-2.204.5H.526a.525.525 0 0 0-.526.522c-.015.976.093 1.95.325 2.899.337 1.23.882 2.15 1.622 2.735 1.307 1.024 3.423 1.612 5.768 1.612.548 0 1.097-.032 1.645-.094a11.783 11.783 0 0 0 3.598-1.14 9.168 9.168 0 0 0 2.46-1.79c1.347-1.42 2.153-3.008 2.746-4.375h.238c1.476 0 2.384-.597 2.884-1.098.333-.333.583-.726.735-1.16l.1-.343z"/></svg>',
  shield: '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
  check: '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
  inbox: '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>',
  file: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>',
  star: '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
  branch: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>',
  bolt: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
};

function setInner(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

// ── Navigation ───────────────────────────────────────────────
function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const pageEl = document.getElementById(`page-${page}`);
  const navEl  = document.getElementById(`nav-${page}`);
  if (pageEl) pageEl.classList.add('active');
  if (navEl)  navEl.classList.add('active');

  const meta = PAGE_META[page] || {};
  setInner('page-title',    meta.title    || page);
  setInner('page-subtitle', meta.subtitle || '');

  currentPage = page;
  loadPage(page);
}

function loadPage(page) {
  const loaders = {
    overview:     loadOverview,
    builds:       loadBuilds,
    deployments:  loadDeployments,
    repositories: loadRepositories,
    registry:     loadRegistry,
    security:     loadSecurity,
    logs:         loadLogs,
  };
  if (loaders[page]) loaders[page]();
}

// ── Sync Status ──────────────────────────────────────────────
async function updateSyncStatus() {
  const data = await fetchJSON('/sync-status');
  const dot   = document.getElementById('sync-dot');
  const label = document.getElementById('sync-label');
  if (!dot || !label) return;

  if (!data) {
    dot.className   = 'sync-dot offline';
    label.textContent = 'Sync offline';
    return;
  }

  if (data.online) {
    dot.className   = 'sync-dot online';
    label.textContent = 'Online — synced';
  } else {
    dot.className   = 'sync-dot offline';
    const pending = (data.pending_commits?.length || 0) + (data.pending_images?.length || 0);
    label.textContent = pending ? `Offline — ${pending} queued` : 'Offline mode';
  }
}

// ── Overview ─────────────────────────────────────────────────
async function loadOverview() {
  const [health, stats, logs] = await Promise.all([
    fetchJSON('/system-health'),
    fetchJSON('/stats'),
    fetchJSON('/logs?limit=20'),
  ]);

  renderHealth(health);
  renderStats(stats);
  renderActivity(logs);
  updateSyncStatus();
}

function renderHealth(data) {
  if (!data) return;

  const overall = data.overall || 'unknown';
  const badge   = document.getElementById('health-badge');
  if (badge) {
    badge.textContent = overall === 'healthy' ? 'All Systems Operational' : 'Degraded';
    badge.className   = `section-badge${overall !== 'healthy' ? ' danger' : ''}`;
  }

  const services = data.services || {};
  document.querySelectorAll('.health-card').forEach(card => {
    const svc = card.dataset.service;
    const s   = services[svc];
    if (!s) return;

    const isUp = s.status === 'up';
    card.classList.remove('skeleton', 'up', 'down');
    card.classList.add(isUp ? 'up' : 'down');

    const statusEl = card.querySelector('.health-status');
    if (statusEl) statusEl.textContent = isUp ? 'Operational' : 'Down';

    // Extra details
    const nameEl = card.querySelector('.health-name');
    if (nameEl && svc === 'gitea' && s.repo_count !== undefined) {
      nameEl.textContent = `Gitea (${s.repo_count} repos)`;
    }
    if (nameEl && svc === 'registry' && s.image_count !== undefined) {
      nameEl.textContent = `Registry (${s.image_count} imgs)`;
    }
  });
}

function renderStats(data) {
  if (!data) return;
  setInner('stat-total-builds',  data.total_builds ?? '—');
  setInner('stat-success-rate',  `${data.build_success_rate ?? '—'}% success rate`);
  setInner('stat-total-deploys', data.total_deployments ?? '—');
  setInner('stat-failed-deploys',`${data.failed_deployments ?? '—'} failed`);
  setInner('stat-repos-count',   data.git_repositories ?? '—');
  setInner('stat-images-count',  data.registry_images ?? '—');
  setInner('stat-security-count',data.security_issues ?? '—');
}

function renderActivity(logs) {
  const feed = document.getElementById('activity-feed');
  if (!feed) return;
  if (!logs || !logs.length) {
    feed.innerHTML = emptyState(ICONS.inbox, 'No recent activity found');
    return;
  }
  feed.innerHTML = logs.map(item => {
    const typeClass  = `badge-${item.event_type}`;
    const typeLabel  = item.event_type === 'build' ? 'Build' : 'Deploy';
    const statusCls  = `status-${(item.status || '').toUpperCase()}`;
    return `
      <div class="activity-item">
        <span class="activity-type-badge ${typeClass}">${typeLabel}</span>
        <span class="activity-name">${item.name || '—'}</span>
        <span class="activity-status ${statusCls}">${item.status || '—'}</span>
        <span class="activity-time">${fmtTime(item.created_at)}</span>
      </div>`;
  }).join('');
}

// ── Builds ───────────────────────────────────────────────────
async function loadBuilds() {
  const data = await fetchJSON('/builds');
  const tbody = document.getElementById('builds-tbody');
  if (!tbody) return;

  if (!data || !data.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="table-loading">${emptyState(ICONS.builds, 'No builds recorded yet')}</td></tr>`;
    return;
  }

  tbody.innerHTML = data.map(b => `
    <tr>
      <td><strong>${b.job || '—'}</strong></td>
      <td style="font-family:var(--font-mono)">#${b.build_number ?? '—'}</td>
      <td>${resultBadge(b.result)}</td>
      <td style="color:var(--text-muted)">${fmtDuration(b.duration_ms)}</td>
      <td style="color:var(--text-muted);font-family:var(--font-mono);font-size:11px">${
        b.timestamp ? fmtTime(new Date(b.timestamp).toISOString()) : fmtTime(b.created_at)
      }</td>
    </tr>`).join('');
}

// ── Deployments ──────────────────────────────────────────────
async function loadDeployments() {
  const data = await fetchJSON('/deployments');
  const tbody = document.getElementById('deployments-tbody');
  if (!tbody) return;

  if (!data || !data.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="table-loading">${emptyState(ICONS.deploys, 'No deployments recorded yet')}</td></tr>`;
    return;
  }

  tbody.innerHTML = data.map(d => `
    <tr>
      <td><strong>${d.service || '—'}</strong></td>
      <td style="font-family:var(--font-mono);font-size:11px">${d.image || '—'}</td>
      <td>${resultBadge(d.status)}</td>
      <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted)">${d.previous_image || '—'}</td>
      <td style="color:var(--text-muted);font-size:11px">${fmtTime(d.started_at || d.created_at)}</td>
    </tr>`).join('');
}

// ── Repositories ─────────────────────────────────────────────
async function loadRepositories() {
  const data = await fetchJSON('/repositories');
  const grid = document.getElementById('repo-grid');
  if (!grid) return;

  if (!data || !data.length) {
    grid.innerHTML = emptyState(ICONS.repos, 'No repositories found in Gitea');
    return;
  }

  grid.innerHTML = data.map(r => {
    // Extract the path from clone_url to make a relative link (e.g. /gitea/user/repo)
    const repoPath = r.clone_url.split('/api/v1/')[0] || ''; 
    const absoluteUrl = `http://localhost/gitea/${r.full_name}`;
    
    return `
    <a href="${absoluteUrl}" target="_blank" class="repo-card-link">
      <div class="repo-card">
        <div class="repo-name">${ICONS.repos} ${r.name || r.full_name || '—'}</div>
        <div class="repo-desc">${r.description || '<em style="opacity:0.5">No description</em>'}</div>
        <div class="repo-meta">
          ${r.language ? `<span class="repo-tag lang">${ICONS.bolt} ${r.language}</span>` : ''}
          <span class="repo-tag">${ICONS.star} ${r.stars ?? 0}</span>
          <span class="repo-tag">${ICONS.branch} ${r.default_branch || 'main'}</span>
          <span class="repo-tag" style="font-size:10px;color:var(--text-muted)">${fmtTime(r.updated_at)}</span>
        </div>
      </div>
    </a>`;
  }).join('');
}

// ── Registry ─────────────────────────────────────────────────
async function loadRegistry() {
  const data = await fetchJSON('/registry/images');
  const grid  = document.getElementById('registry-grid');
  const badge = document.getElementById('registry-count-badge');
  if (!grid) return;

  if (!data || !data.length) {
    grid.innerHTML = emptyState(ICONS.docker, 'No images found in local registry');
    if (badge) badge.textContent = '0 images';
    return;
  }

  if (badge) badge.textContent = `${data.length} image${data.length !== 1 ? 's' : ''}`;

  grid.innerHTML = data.map(img => `
    <div class="registry-card">
      <div class="registry-image-name">${ICONS.docker} ${img.repository}</div>
      <div class="registry-tag-count">${img.tag_count} tag${img.tag_count !== 1 ? 's' : ''}</div>
      <div class="registry-tags">
        ${(img.tags || []).slice(0, 8).map(t =>
          `<span class="registry-tag">${t}</span>`).join('')}
        ${img.tags && img.tags.length > 8
          ? `<span class="registry-tag" style="color:var(--text-muted)">+${img.tags.length - 8} more</span>`
          : ''}
      </div>
    </div>`).join('');
}

// ── Security ─────────────────────────────────────────────────
async function loadSecurity() {
  const data  = await fetchJSON('/security-findings');
  const list  = document.getElementById('findings-list');
  const badge = document.getElementById('security-count-badge');
  if (!list) return;

  if (!data || !data.length) {
    list.innerHTML = emptyState(ICONS.check, 'No security findings — clean scan!');
    if (badge) { badge.textContent = 'Clean'; badge.className = 'section-badge'; }
    return;
  }

  const critical = data.filter(f => f.severity === 'CRITICAL').length;
  const high      = data.filter(f => f.severity === 'HIGH').length;
  if (badge) badge.textContent = `${critical} Critical · ${high} High · ${data.length} Total`;

  list.innerHTML = data.map(f => `
    <div class="finding-card ${f.severity || 'MEDIUM'}">
      <div class="finding-header">
        <span class="finding-severity severity-${f.severity || 'MEDIUM'}">${f.severity || 'MEDIUM'}</span>
        <span class="finding-type">${f.type || '—'}</span>
        <span class="finding-label">${f.label || f.reason || ''}</span>
      </div>
      ${f.file ? `<div class="finding-file">${ICONS.file} ${f.file}${f.line ? ` : line ${f.line}` : ''}</div>` : ''}
      ${f.image ? `<div class="finding-file">${ICONS.docker} ${f.image}</div>` : ''}
      ${f.snippet ? `<div class="finding-snippet">${escapeHtml(f.snippet)}</div>` : ''}
    </div>`).join('');
}

// ── Logs ─────────────────────────────────────────────────────
async function loadLogs() {
  const data     = await fetchJSON('/logs?limit=150');
  const terminal = document.getElementById('log-terminal');
  if (!terminal) return;

  if (!data || !data.length) {
    terminal.innerHTML = '<div class="log-line" style="color:var(--text-muted)">No log events recorded yet.</div>';
    return;
  }

  terminal.innerHTML = data.map(item => {
    const ts  = fmtTime(item.created_at);
    const stt = (item.status || '').toUpperCase();
    return `<div class="log-line">
      <span class="log-time">[${ts}]</span>
      <span class="log-event"> ${item.event_type?.toUpperCase() || 'EVENT'} </span>
      <span class="log-name"> ${item.name || '—'} </span>
      <span class="log-status ${stt}">${stt}</span>
    </div>`;
  }).join('');

  // Auto-scroll to bottom
  terminal.scrollTop = terminal.scrollHeight;
}

// ── Helpers ──────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function updateLastRefreshed() {
  const el = document.getElementById('last-updated');
  if (el) el.textContent = `Updated ${new Date().toLocaleTimeString()}`;
}

// ── Auto-refresh ─────────────────────────────────────────────
function scheduleRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(() => {
    loadPage(currentPage);
    updateSyncStatus();
    updateLastRefreshed();
  }, REFRESH_INTERVAL_MS);
}

// ── Boot ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Wire navigation
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => navigate(item.dataset.page));
  });

  // Refresh button
  document.getElementById('btn-refresh')?.addEventListener('click', () => {
    loadPage(currentPage);
    updateSyncStatus();
    updateLastRefreshed();
  });

  // Initial load
  navigate('overview');
  scheduleRefresh();
  updateLastRefreshed();
});

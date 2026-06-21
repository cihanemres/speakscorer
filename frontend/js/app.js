/* ═══════════════════════════════════════════════════════════
   SpeakScorer — Çekirdek JavaScript
   API, auth, responsive shell, oyunlaştırma yardımcıları
   ⚠ API sözleşmesi (endpoint, FormData, response parse) DEĞİŞMEDİ.
   ═══════════════════════════════════════════════════════════ */

const API = window.location.origin;

// ── XSS Kaçışı (HTML) ────────────────────────────────────
function esc(value) {
    if (value === null || value === undefined) return '';
    return String(value).replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[ch]));
}

// ── Cookie yardımcısı (CSRF token'ını okumak için) ───────
function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m.pop()) : '';
}

// ── Auth Yönetimi ────────────────────────────────────────
const Auth = {
    getUser() { const u = localStorage.getItem('speakai_user'); return u ? JSON.parse(u) : null; },
    setUser(user) { localStorage.setItem('speakai_user', JSON.stringify(user)); },
    getCsrf() { return getCookie('speakai_csrf'); },
    async logout() {
        try {
            const headers = {};
            const csrf = this.getCsrf();
            if (csrf) headers['X-CSRF-Token'] = csrf;
            await fetch(`${API}/api/auth/logout`, { method: 'POST', credentials: 'include', headers });
        } catch (e) {}
        localStorage.removeItem('speakai_user');
        window.location.href = '/';
    },
    isLoggedIn() { return !!this.getUser(); },
    requireAuth() { if (!this.isLoggedIn()) { window.location.href = '/'; return false; } return true; },
};

// ── API Helpers (DEĞİŞMEDİ) ──────────────────────────────
async function api(endpoint, options = {}) {
    const headers = { ...options.headers };
    if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';

    const method = (options.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
        const csrf = Auth.getCsrf();
        if (csrf) headers['X-CSRF-Token'] = csrf;
    }

    const response = await fetch(`${API}${endpoint}`, { ...options, headers, credentials: 'include' });
    if (response.status === 401) {
        localStorage.removeItem('speakai_user');
        window.location.href = '/';
        return null;
    }
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'İstek başarısız' }));
        throw new Error(err.detail || 'İstek başarısız');
    }
    return response.json();
}

async function apiGet(ep) { return api(ep); }
async function apiPost(ep, d) { return api(ep, { method: 'POST', body: JSON.stringify(d) }); }
async function apiPut(ep, d) { return api(ep, { method: 'PUT', body: JSON.stringify(d) }); }
async function apiDelete(ep) { return api(ep, { method: 'DELETE' }); }
async function apiUpload(ep, fd) { return api(ep, { method: 'POST', body: fd }); }

// ── Motion tercihi ───────────────────────────────────────
function prefersReduced() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// ── UI Helpers ───────────────────────────────────────────
function showAlert(message, type = 'info', container = null) {
    const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
    const el = document.createElement('div');
    // İçeride hedef yoksa ekranda yüzen toast olarak göster (mobil dostu).
    const target = container || document.querySelector('.dashboard-content') || null;
    el.className = `alert alert-${type}` + (target ? '' : ' toast');
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');
    el.innerHTML = `<span aria-hidden="true">${icons[type] || ''}</span><span>${esc(message)}</span>`;
    (target || document.body).prepend(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .4s'; setTimeout(() => el.remove(), 400); }, 4600);
}

function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function getScoreColor(score) {
    if (score >= 80) return 'var(--green)';
    if (score >= 60) return 'var(--amber)';
    if (score >= 40) return 'var(--brand)';
    return 'var(--red)';
}

function getScoreBadge(score) {
    if (score === null || score === undefined) return '<span class="badge badge-info">Bekliyor</span>';
    const s = Math.round(score);
    if (s >= 80) return `<span class="badge badge-success">${s}</span>`;
    if (s >= 60) return `<span class="badge badge-warning">${s}</span>`;
    return `<span class="badge badge-danger">${s}</span>`;
}

function getStatusBadge(status) {
    const map = {
        pending: ['badge-warning', 'BEKLİYOR'],
        active: ['badge-success', 'AKTİF'],
        inactive: ['badge-danger', 'DEVRE DIŞI'],
        rejected: ['badge-danger', 'REDDEDİLDİ'],
        scored: ['badge-info', 'PUANLANDI'],
        reviewed: ['badge-success', 'DEĞERLENDİRİLDİ'],
    };
    const [cls, label] = map[status] || ['badge-info', status];
    return `<span class="badge ${cls}">${label}</span>`;
}

function getRoleName(rol) {
    const map = { ogrenci: 'Öğrenci', ogretmen: 'Öğretmen', veli: 'Veli', yonetici: 'Yönetici' };
    return map[rol] || rol;
}

// ── Oyunlaştırma yardımcıları ────────────────────────────
function buildScoreCircle(score) {
    const s = Math.round(score || 0);
    return `<div class="score-circle" data-score="${s}" style="--val:${s};--score-color:${getScoreColor(s)}">
        <span class="score-value">${s}</span>
    </div>`;
}

// Mor→cyan gradyan SVG halka (donut/gauge). Kılavuz #2 & #3 için.
// pct 0-100. Değer yayı önce boş başlar, activateAnimations ile dolar.
let _ringSeq = 0;
function svgRing({ pct = 0, size = 150, stroke = 14, big = '', small = '', from = '#a855f7', to = '#22d3ee' }) {
    const p = Math.max(0, Math.min(100, pct));
    const r = 50 - stroke / 2;
    const circ = 2 * Math.PI * r;
    const off = circ * (1 - p / 100);
    const gid = 'ring-g-' + (++_ringSeq);
    return `<div class="neon-ring" style="width:${size}px;height:${size}px">
        <svg viewBox="0 0 100 100">
            <defs><linearGradient id="${gid}" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="${from}"/><stop offset="100%" stop-color="${to}"/>
            </linearGradient></defs>
            <circle class="ring-track" cx="50" cy="50" r="${r}" stroke-width="${stroke}"/>
            <circle class="ring-val" cx="50" cy="50" r="${r}" stroke-width="${stroke}" stroke="url(#${gid})"
                    stroke-dasharray="${circ.toFixed(2)}" stroke-dashoffset="${circ.toFixed(2)}" data-off="${off.toFixed(2)}"/>
        </svg>
        <div class="ring-center">${big ? `<div class="ring-big">${big}</div>` : ''}${small ? `<div class="ring-small">${small}</div>` : ''}</div>
    </div>`;
}

// Puan dairesini 0'dan değere doldurur + sayıyı say-up yapar.
function animateScoreCircle(el, value) {
    if (!el) return;
    const v = Math.max(0, Math.min(100, Math.round(value || 0)));
    el.style.setProperty('--score-color', getScoreColor(v));
    el.setAttribute('aria-label', `Puan: ${v} / 100`);
    const valEl = el.querySelector('.score-value');
    if (prefersReduced()) { el.style.setProperty('--val', v); if (valEl) valEl.textContent = v; return; }
    const dur = 1100, start = performance.now();
    function frame(t) {
        const p = Math.min(1, (t - start) / dur);
        const eased = 1 - Math.pow(1 - p, 3);
        const cur = Math.round(v * eased);
        el.style.setProperty('--val', cur);
        if (valEl) valEl.textContent = cur;
        if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
}

// Bir sayıyı 0'dan hedefe say-up animasyonu.
function countUp(el, to, dur = 900) {
    if (!el) return;
    const target = Math.round(to || 0);
    if (prefersReduced()) { el.textContent = target; return; }
    const start = performance.now();
    function frame(t) {
        const p = Math.min(1, (t - start) / dur);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * eased);
        if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
}

// Sayfa render edildikten sonra tüm [data-score] dairelerini ve
// .countup elemanlarını canlandırır (IntersectionObserver ile).
function activateAnimations(root = document) {
    if (prefersReduced()) {
        root.querySelectorAll('.countup').forEach(el => { el.textContent = el.dataset.to || el.textContent; });
        root.querySelectorAll('.xp-bar-fill[data-fill]').forEach(el => { el.style.width = el.dataset.fill + '%'; });
        root.querySelectorAll('.ring-val[data-off]').forEach(el => { el.style.strokeDashoffset = el.dataset.off; });
        return;
    }
    const io = new IntersectionObserver((entries, obs) => {
        entries.forEach(e => {
            if (!e.isIntersecting) return;
            const el = e.target;
            if (el.matches('.score-circle')) animateScoreCircle(el, parseFloat(el.dataset.score));
            else if (el.matches('.countup')) countUp(el, parseFloat(el.dataset.to));
            else if (el.matches('.xp-bar-fill')) requestAnimationFrame(() => { el.style.width = el.dataset.fill + '%'; });
            else if (el.matches('.ring-val')) requestAnimationFrame(() => { el.style.strokeDashoffset = el.dataset.off; });
            obs.unobserve(el);
        });
    }, { threshold: 0.25 });
    root.querySelectorAll('.score-circle[data-score], .countup, .xp-bar-fill[data-fill], .ring-val[data-off]').forEach(el => io.observe(el));
}

// Konfeti kutlaması (harici kütüphane yok).
function launchConfetti() {
    if (prefersReduced()) return;
    const cv = document.createElement('canvas');
    cv.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:500';
    cv.width = window.innerWidth; cv.height = window.innerHeight;
    document.body.appendChild(cv);
    const ctx = cv.getContext('2d');
    const colors = ['#06b6d4', '#22d3ee', '#10b981', '#a3e635', '#67e8f9', '#fbbf24'];
    const N = 140;
    const parts = Array.from({ length: N }, (_, i) => ({
        x: cv.width / 2 + (i % 7 - 3) * 8,
        y: cv.height * 0.34,
        vx: (((i * 73) % 100) / 100 - 0.5) * 14,
        vy: -8 - (((i * 31) % 100) / 100) * 9,
        r: 4 + (i % 4) * 2,
        rot: (i * 0.6),
        vr: (((i * 17) % 100) / 100 - 0.5) * 0.5,
        c: colors[i % colors.length],
    }));
    let frames = 0;
    (function tick() {
        ctx.clearRect(0, 0, cv.width, cv.height);
        parts.forEach(p => {
            p.vy += 0.4; p.x += p.vx; p.y += p.vy; p.vx *= 0.99; p.rot += p.vr;
            ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot);
            ctx.fillStyle = p.c; ctx.fillRect(-p.r / 2, -p.r / 2, p.r, p.r * 1.6);
            ctx.restore();
        });
        frames++;
        if (frames < 130) requestAnimationFrame(tick);
        else cv.remove();
    })();
}

// ── Responsive Shell (sidebar + topbar + bottom nav) ─────
const NAV_MENUS = {
    ogrenci: [
        { icon: '🏠', label: 'Panel', page: 'dashboard' },
        { icon: '📝', label: 'Ödevler', page: 'tasks' },
        { icon: '🎯', label: 'Gönderim', page: 'results' },
        { icon: '📈', label: 'İlerleme', page: 'progress' },
        { icon: '🏆', label: 'Sıralama', page: 'leaderboard' },
        { icon: '🎖️', label: 'Rozetler', page: 'badges' },
    ],
    ogretmen: [
        { icon: '🏠', label: 'Panel', page: 'dashboard' },
        { icon: '📝', label: 'Ödevler', page: 'assignments' },
        { icon: '📋', label: 'Gönderimler', page: 'submissions' },
        { icon: '👨‍🎓', label: 'Öğrenciler', page: 'students' },
        { icon: '📄', label: 'Paragraflar', page: 'paragraphs' },
    ],
    veli: [
        { icon: '🏠', label: 'Panel', page: 'dashboard' },
        { icon: '👨‍👧', label: 'Çocuklarım', page: 'children' },
    ],
    yonetici: [
        { icon: '🏠', label: 'Panel', page: 'dashboard' },
        { icon: '👥', label: 'Kullanıcılar', page: 'users' },
        { icon: '📋', label: 'Gönderimler', page: 'submissions' },
        { icon: '📄', label: 'Paragraflar', page: 'paragraphs' },
        { icon: '📈', label: 'İstatistik', page: 'stats' },
    ],
};

function buildShell(user) {
    const sb = document.getElementById('sidebar');
    if (!sb) return;

    const initial = user.ad_soyad ? user.ad_soyad[0].toUpperCase() : '?';
    const roleName = getRoleName(user.rol);
    const items = NAV_MENUS[user.rol] || [];

    // ── Sidebar ──
    sb.setAttribute('role', 'navigation');
    sb.setAttribute('aria-label', 'Ana menü');
    sb.innerHTML = `
        <div class="sidebar-brand">
            <div class="brand-icon" aria-hidden="true">🎙️</div>
            <span class="brand-text">SpeakScorer</span>
        </div>
        <ul class="sidebar-nav" id="sidebar-nav">
            ${items.map((m, i) => `
                <li><a href="#" class="${i === 0 ? 'active' : ''}" data-page="${m.page}"
                       ${i === 0 ? 'aria-current="page"' : ''}
                       onclick="navigate('${m.page}'); return false;" title="${esc(m.label)}">
                    <span class="nav-icon" aria-hidden="true">${m.icon}</span> <span>${esc(m.label)}</span>
                </a></li>
            `).join('')}
        </ul>
        <div class="sidebar-user">
            <button class="sidebar-user-info" onclick="navigate('profile')" title="Profil ayarları">
                <div class="user-avatar" aria-hidden="true">${esc(initial)}</div>
                <div class="user-meta">
                    <div class="user-name">${esc(user.ad_soyad)}</div>
                    <div class="user-role">${esc(roleName)}</div>
                </div>
            </button>
            <button class="sidebar-logout" onclick="Auth.logout()">
                <span aria-hidden="true">🚪</span> <span>Çıkış Yap</span>
            </button>
        </div>
    `;

    // ── Topbar (mobil/tablet) ──
    let topbar = document.getElementById('app-topbar');
    if (!topbar) {
        topbar = document.createElement('header');
        topbar.id = 'app-topbar';
        topbar.className = 'topbar';
        // Tam genişlik için layout'un DIŞINA, body'nin en üstüne yerleştir.
        const layout = document.querySelector('.dashboard-layout');
        if (layout && layout.parentNode) layout.parentNode.insertBefore(topbar, layout);
        else document.body.insertBefore(topbar, document.body.firstChild);
    }
    topbar.innerHTML = `
        <button class="icon-btn" onclick="toggleSidebar()" aria-label="Menüyü aç/kapat">☰</button>
        <div class="topbar-brand"><span class="brand-icon" aria-hidden="true">🎙️</span> SpeakScorer</div>
        <div style="flex:1"></div>
        <button class="icon-btn" onclick="navigate('profile')" aria-label="Profil">
            <span class="user-avatar" style="width:34px;height:34px;font-size:.8rem">${esc(initial)}</span>
        </button>
    `;

    // ── Scrim (drawer arka planı) ──
    let scrim = document.getElementById('app-scrim');
    if (!scrim) {
        scrim = document.createElement('div');
        scrim.id = 'app-scrim';
        scrim.className = 'scrim';
        scrim.onclick = closeDrawer;
        document.body.appendChild(scrim);
    }

    // ── Bottom nav (telefon) ──
    let bn = document.getElementById('app-bottomnav');
    if (!bn) {
        bn = document.createElement('nav');
        bn.id = 'app-bottomnav';
        bn.className = 'bottomnav';
        bn.setAttribute('aria-label', 'Hızlı gezinme');
        document.body.appendChild(bn);
    }
    // En fazla 5 öğe; daha fazlaysa 4 öğe + "Menü" (çekmeceyi açar).
    let bnItems = items;
    let more = false;
    if (items.length > 5) { bnItems = items.slice(0, 4); more = true; }
    bn.innerHTML = bnItems.map((m, i) => `
        <a href="#" class="${i === 0 ? 'active' : ''}" data-page="${m.page}"
           ${i === 0 ? 'aria-current="page"' : ''}
           onclick="navigate('${m.page}'); return false;">
            <span class="nav-icon" aria-hidden="true">${m.icon}</span><span>${esc(m.label)}</span>
        </a>
    `).join('') + (more ? `
        <a href="#" onclick="toggleSidebar(); return false;">
            <span class="nav-icon" aria-hidden="true">⋯</span><span>Menü</span>
        </a>` : '');
}

// Eski isimle uyumluluk (dashboard.html updateProfile çağırıyor).
function buildSidebar(user) { buildShell(user); }

function toggleSidebar() {
    const sb = document.getElementById('sidebar');
    const scrim = document.getElementById('app-scrim');
    if (window.matchMedia('(max-width: 720px)').matches) {
        const open = sb.classList.toggle('open');
        if (scrim) scrim.classList.toggle('open', open);
        document.body.style.overflow = open ? 'hidden' : '';
    } else {
        sb.classList.toggle('expanded');
    }
}

function closeDrawer() {
    const sb = document.getElementById('sidebar');
    const scrim = document.getElementById('app-scrim');
    if (sb) sb.classList.remove('open');
    if (scrim) scrim.classList.remove('open');
    document.body.style.overflow = '';
}

// Tüm gezinme öğelerinde aktif durumu eşitler.
function setActiveNav(page) {
    document.querySelectorAll('[data-page]').forEach(a => {
        const on = a.dataset.page === page;
        a.classList.toggle('active', on);
        if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
}

// ── Init Dashboard ───────────────────────────────────────
function initDashboard() {
    if (!Auth.requireAuth()) return null;
    const user = Auth.getUser();
    buildShell(user);
    return user;
}

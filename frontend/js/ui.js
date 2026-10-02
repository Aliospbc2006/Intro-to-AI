// Tiện ích giao diện dùng chung
const app = { tab: 'path' };

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtKm = (m) => (m / 1000).toFixed(2) + ' km';

function debounce(fn, ms) {
    let t;
    return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

// Chọn màu chữ (đen/trắng) dễ đọc trên nền màu tuyến
function textOn(hex) {
    const n = parseInt(hex.replace('#', ''), 16);
    const lum = (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
    return lum > 0.68 ? '#1e293b' : '#ffffff';
}

function lineBadge(code) {
    const l = store.lines.get(code);
    const c = l ? '#' + l.color : '#64748b';
    return `<span class="badge-line" style="--c:${c};--t:${textOn(c)}">${esc(code)}</span>`;
}

function statusPill(active) {
    return `<span class="pill ${active ? 'pill-active' : 'pill-inactive'}">${active ? 'Active' : 'Inactive'}</span>`;
}

const ICON = {
    search: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
    ban: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/></svg>',
    undo: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/></svg>',
    swap: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 4v16m0 0-3-3m3 3 3-3M17 20V4m0 0-3 3m3-3 3 3"/></svg>',
};

function toast(msg, opts = {}) {
    const box = document.getElementById('toasts');
    const el = document.createElement('div');
    el.className = 'toast' + (opts.error ? ' error' : '');
    el.innerHTML = `<span>${esc(msg)}</span>`;
    if (opts.action) {
        const b = document.createElement('button');
        b.textContent = opts.action.label;
        b.onclick = () => { opts.action.fn(); el.remove(); };
        el.appendChild(b);
    }
    box.appendChild(el);
    setTimeout(() => el.remove(), opts.action ? 6000 : 3200);
}

// Segmented control: gọi onChange(value) khi đổi
function bindSegmented(root, onChange) {
    root.addEventListener('click', (e) => {
        const b = e.target.closest('button[data-v]');
        if (!b) return;
        root.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
        onChange(b.dataset.v);
    });
}

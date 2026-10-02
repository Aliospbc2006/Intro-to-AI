// Tab Segments + Stations: tìm kiếm / lọc / chọn, đồng bộ hai chiều với bản đồ
function makeListPanel(cfg) {
    const p = {
        el: document.getElementById(cfg.panelId),
        q: '', line: '', status: 'all',

        init() {
            const lineOpts = '<option value="">All lines</option>' + store.sortedLines(store.lines.keys())
                .map((c) => `<option value="${c}">${c} · ${esc(store.lines.get(c).name)}</option>`).join('');
            this.el.innerHTML = `<div class="filters">
                    <div class="search">${ICON.search}<input type="search" placeholder="${cfg.placeholder}" autocomplete="off"></div>
                    <select aria-label="Filter by line">${lineOpts}</select>
                    <div class="seg" role="group" aria-label="Filter by status">
                        <button data-v="all" class="on">All</button><button data-v="active">Active</button><button data-v="inactive">Inactive</button>
                    </div>
                    <div class="count"></div>
                </div>
                <div class="list"></div>`;
            this.input = this.el.querySelector('input');
            this.listEl = this.el.querySelector('.list');
            this.countEl = this.el.querySelector('.count');

            this.input.addEventListener('input', debounce(() => { this.q = this.input.value.trim().toLowerCase(); this.renderList(); }, 120));
            this.el.querySelector('select').addEventListener('change', (e) => { this.line = e.target.value; this.renderList(); });
            bindSegmented(this.el.querySelector('.seg'), (v) => { this.status = v; this.renderList(); });

            this.listEl.addEventListener('click', (ev) => {
                const row = ev.target.closest('[data-id]');
                if (!row) return;
                const id = Number(row.dataset.id);
                if (ev.target.closest('[data-act="toggle"]')) { net.toggle(cfg.kind, id); return; }
                net.select(cfg.kind, id);
            });
            this.listEl.addEventListener('mouseover', (ev) => {
                const row = ev.target.closest('[data-id]');
                if (row) net.setHover(cfg.kind, Number(row.dataset.id));
            });
            this.listEl.addEventListener('mouseleave', () => net.setHover(null));

            store.on('active', ({ kind }) => { if (kind === 'node' || cfg.kind === 'edge') this.renderList(); });
            store.on('selection', () => this.markSelected(true));
            this.renderList();
        },

        match(it) {
            if (this.status === 'active' && !it.active) return false;
            if (this.status === 'inactive' && it.active) return false;
            return cfg.match(it, this.q, this.line);
        },

        renderList() {
            const items = [...cfg.source().values()].filter((it) => this.match(it)).sort(cfg.sort);
            this.countEl.textContent = `${items.length} of ${cfg.source().size} ${cfg.noun}`;
            this.listEl.innerHTML = items.length ? items.map((it) => cfg.row(it)).join('') : `<div class="empty">No ${cfg.noun} match your filters.</div>`;
            this.markSelected(false);
        },

        markSelected(scroll) {
            const s = net.state.selected;
            let found = null;
            this.listEl.querySelectorAll('.item').forEach((r) => {
                const on = !!s && s.kind === cfg.kind && Number(r.dataset.id) === s.id;
                r.classList.toggle('selected', on);
                if (on) found = r;
            });
            if (scroll && found && app.tab === cfg.tab) found.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        },
    };
    return p;
}

const toggleBtn = (it) => `<button class="icon-btn ${it.active ? '' : 'unban'}" data-act="toggle" title="${it.active ? 'Ban' : 'Unban'}" aria-label="${it.active ? 'Ban' : 'Unban'}">${it.active ? ICON.ban : ICON.undo}</button>`;

const segmentsPanel = makeListPanel({
    panelId: 'panel-segments', tab: 'segments', kind: 'edge', noun: 'segments',
    placeholder: 'Search by station, line or ID…',
    source: () => store.edges,
    match: (e, q, line) => {
        if (line && e.line !== line) return false;
        if (!q) return true;
        const l = store.lines.get(e.line);
        return `${store.edgeTitle(e)} ${l.name} ${e.line} ${e.id}`.toLowerCase().includes(q);
    },
    sort: (a, b) => LINE_ORDER.indexOf(a.line) - LINE_ORDER.indexOf(b.line) || a.id - b.id,
    row: (e) => `<div class="card item ${e.active ? '' : 'is-inactive'}" style="--c:#${e.color}" data-id="${e.id}" tabindex="0">
        <div class="item-main">
            <div class="item-top">${lineBadge(e.line)}<span class="item-title">${esc(store.nodeName(e.start))}<span class="arrow">→</span>${esc(store.nodeName(e.end))}</span></div>
            <div class="item-sub"><span class="badge-id">#${e.id}</span>${statusPill(e.active)}<span>${fmtKm(e.length)}</span>
                ${store.isBlocked(e) ? '<span class="item-warn">station banned</span>' : ''}</div>
        </div>${toggleBtn(e)}</div>`,
});

const stationsPanel = makeListPanel({
    panelId: 'panel-stations', tab: 'stations', kind: 'node', noun: 'stations',
    placeholder: 'Search station name or ID…',
    source: () => store.nodes,
    match: (n, q, line) => {
        if (line && !n.lines.has(line)) return false;
        return !q || `${n.name} ${n.id}`.toLowerCase().includes(q);
    },
    sort: (a, b) => a.name.localeCompare(b.name) || a.id - b.id,
    row: (n) => `<div class="card item ${n.active ? '' : 'is-inactive'}" style="--c:${n.lines.size ? '#' + store.lines.get(store.sortedLines(n.lines)[0]).color : '#94a3b8'}" data-id="${n.id}" tabindex="0">
        <div class="item-main">
            <div class="item-top"><span class="item-title">${esc(n.name)}</span></div>
            <div class="item-sub"><span class="badge-id">#${n.id}</span>${statusPill(n.active)}
                <span class="line-dots">${store.sortedLines(n.lines).map(lineBadge).join('')}</span></div>
        </div>${toggleBtn(n)}</div>`,
});

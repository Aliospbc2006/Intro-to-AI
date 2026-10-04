// Tab Path: chọn ga đi/đến trên bản đồ, gọi /path/ và hiển thị kết quả
const pathPanel = {
    el: document.getElementById('panel-path'),
    start: null,          // id ga
    end: null,
    picking: 'start',     // 'start' | 'end' | null
    // Phí đổi tuyến (mét) gửi lên backend; cộng vào chi phí của A* mỗi lần đổi tuyến
    penalty: 2000,
    result: null,         // {fc, legs, ids, lines}
    busy: false,
    error: null,

    init() {
        this.render();
        map.on('click', (ev) => this.onMapClick(ev));
        store.on('active', () => this.onActiveChange());
        this.el.addEventListener('click', (ev) => this.onClick(ev));
        this.el.addEventListener('input', (ev) => {
            if (ev.target.id === 'penaltyInput') this.penalty = ev.target.value;
        });
    },

    // Chỉ nhận click bản đồ khi ở tab Path và không ở Ban Mode
    onMapClick(ev) {
        if (app.tab !== 'path' || net.state.banMode || !this.picking) return;
        // ev.latlng bị Leaflet gán bằng tâm node trên cùng khi click vào layer → lấy vị trí chuột thật
        const ll = ev.originalEvent ? map.mouseEventToLatLng(ev.originalEvent) : ev.latlng;
        const n = store.nearestActive(ll.lat, ll.lng);
        if (!n) { toast('No active station available', { error: true }); return; }
        this.setPoint(this.picking, n.id);
    },

    // Đặt ga đi/đến. Đổi điểm thì kết quả cũ không còn đúng nên xóa.
    // Tự chuyển sang chọn điểm còn thiếu; đủ cả hai điểm thì dừng chọn (picking = null).
    setPoint(which, id) {
        this[which] = id;
        net.setPin(which, id);
        this.clearResult();
        this.picking = which === 'start' ? (this.end == null ? 'end' : null) : (this.start == null ? 'start' : null);
        this.render();
    },

    clearResult() {
        this.result = null;
        this.error = null;
        net.clearRoute();
    },

    reset() {
        this.start = this.end = null;
        this.picking = 'start';
        net.setPin('start', null);
        net.setPin('end', null);
        this.clearResult();
        this.render();
    },

    swap() {
        [this.start, this.end] = [this.end, this.start];
        net.setPin('start', this.start);
        net.setPin('end', this.end);
        this.clearResult();
        this.render();
    },

    // Ga đã chọn bị ban → bỏ chọn, kết quả cũ không còn đúng
    onActiveChange() {
        let changed = false;
        ['start', 'end'].forEach((w) => {
            const n = this[w] != null && store.nodes.get(this[w]);
            if (n && !n.active) { this[w] = null; net.setPin(w, null); changed = true; }
        });
        if (changed) {
            this.picking = this.start == null ? 'start' : 'end';
            this.clearResult();
            this.render();
        }
    },

    // Gọi backend tìm đường. busy chặn bấm nhiều lần khi đang chờ phản hồi.
    async find() {
        const a = store.nodes.get(this.start), b = store.nodes.get(this.end);
        if (!a || !b || this.busy) return;
        this.busy = true;
        this.error = null;
        this.render();
        try {
            const pen = Number(this.penalty);
            // Backend nhận tọa độ chứ không nhận id ga: gửi đúng tọa độ hai ga đã chọn thì
            // find_nearest_node sẽ trả lại chính hai ga đó. penalty không hợp lệ thì dùng mặc định 2000.
            const q = new URLSearchParams({
                lon1: a.lon, lat1: a.lat, lon2: b.lon, lat2: b.lat,
                penalty: Number.isFinite(pen) && pen >= 0 ? pen : 2000,
            });
            // GET /path/ → GeoJSON FeatureCollection của đường đi (xem net.showRoute),
            // hoặc { message: "Path not found" } không có "features" khi hai ga không nối được
            const res = await fetch(`${API}/path/?${q}`);
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const fc = await res.json();
            if (!fc.features) {
                this.result = null;
                this.error = 'No route found between these stations with the current banned items.';
                net.clearRoute();
            } else {
                this.result = this.summarize(fc);
                net.showRoute(fc);
            }
        } catch (err) {
            this.result = null;
            this.error = 'Could not reach the route service: ' + err.message;
        } finally {
            this.busy = false;
            this.render();
        }
    },

    // Gom các chặng liên tiếp cùng tuyến
    // ids có n ga, lines có n - 1 phần tử: lines[i] là tuyến đi từ ids[i] tới ids[i+1].
    // Mỗi leg = { line, from, to, hops }: from/to là chỉ số trong ids, hops là số đoạn trong chặng.
    summarize(fc) {
        const p = fc.properties;
        const ids = p.id, lines = p.line;
        const legs = [];
        lines.forEach((code, i) => {
            const last = legs[legs.length - 1];
            if (last && last.line === code) { last.to = i + 1; last.hops++; } else legs.push({ line: code, from: i, to: i + 1, hops: 1 });
        });
        return { fc, ids, lines, legs, transfers: p.total_transfers, length: p.length };
    },

    // Event delegation: panel được render lại bằng innerHTML nên chỉ gắn một listener ở panel,
    // nút nào được bấm thì xác định qua thuộc tính data-act của nó
    onClick(ev) {
        const t = ev.target.closest('[data-act]');
        if (!t) return;
        const act = t.dataset.act;
        if (act === 'pick') { this.picking = t.dataset.w; this.render(); }
        else if (act === 'swap') this.swap();
        else if (act === 'find') this.find();
        else if (act === 'reset') this.reset();
        else if (act === 'chip') { this.penalty = Number(t.dataset.v); this.render(); }
        else if (act === 'station') {
            const n = store.nodes.get(Number(t.dataset.id));
            map.flyTo([n.lat, n.lon], Math.max(map.getZoom(), 14), { duration: 0.5 });
        }
    },

    pointRow(which, label) {
        const n = this[which] != null ? store.nodes.get(this[which]) : null;
        return `<div class="point ${this.picking === which ? 'picking' : ''}" data-act="pick" data-w="${which}">
            <span class="pt-pin pin-${which}">${which === 'start' ? 'A' : 'B'}</span>
            <div class="grow"><small>${label}</small>${n ? `<b>${esc(n.name)}</b>` : `<i>${this.picking === which ? 'Click a station on the map…' : 'Click to choose on map'}</i>`}</div>
            ${n ? store.sortedLines(n.lines).map(lineBadge).join('') : ''}
        </div>`;
    },

    // Dựng lại toàn bộ HTML của tab từ trạng thái hiện tại (start, end, picking, penalty, result, error)
    render() {
        const ready = this.start != null && this.end != null;
        const chips = [0, 500, 1000, 2000, 5000].map((v) =>
            `<button class="chip ${Number(this.penalty) === v ? 'on' : ''}" data-act="chip" data-v="${v}">${v} m</button>`).join('');

        let html = `<div class="section">
            <h3>Route</h3>
            ${this.pointRow('start', 'Start station')}
            <div class="swap"><button data-act="swap" title="Swap start and end" aria-label="Swap start and end">${ICON.swap}</button></div>
            ${this.pointRow('end', 'End station')}
        </div>
        <div class="section">
            <h3>Transfer penalty</h3>
            <div class="penalty"><input type="number" id="penaltyInput" min="0" step="100" value="${esc(this.penalty)}"><span>metres per line change</span></div>
            <div class="chips">${chips}</div>
        </div>
        <div class="actions">
            <button class="btn btn-primary" data-act="find" ${ready && !this.busy ? '' : 'disabled'}>${this.busy ? 'Finding…' : 'Find path'}</button>
            <button class="btn btn-ghost" data-act="reset">Reset</button>
        </div>`;

        if (!ready && !this.error) html += `<p class="hint">Pick the start and end stations by clicking on the map. The nearest active station is selected.</p>`;
        if (this.error) html += `<div class="alert alert-error" style="margin:0 0 12px">${esc(this.error)}</div>`;
        if (this.result) html += this.renderResult();
        this.el.innerHTML = html;
        if (typeof updateBanner === 'function') updateBanner();
    },

    renderResult() {
        const r = this.result;
        const name = (id) => esc(store.nodeName(id));
        const legs = r.legs.map((lg, i) => {
            const l = store.lines.get(lg.line);
            const c = '#' + l.color;
            const row = `<div class="card leg" style="--c:${c}">
                ${lineBadge(lg.line)}
                <div class="grow"><b>${esc(l.name)} Line</b><small>${name(r.ids[lg.from])} → ${name(r.ids[lg.to])}</small></div>
                <span class="leg-n">${lg.hops} ${lg.hops === 1 ? 'stop' : 'stops'}</span>
            </div>`;
            const next = r.legs[i + 1];
            return row + (next ? `<div class="transfer">Transfer at ${name(r.ids[lg.to])} → ${esc(store.lines.get(next.line).name)}</div>` : '');
        }).join('');

        // Màu của ga i theo chặng đi tới nó (ga đầu theo chặng đầu)
        const stops = r.ids.map((id, i) => {
            const code = r.lines[Math.min(i, r.lines.length - 1)];
            const incoming = i > 0 ? r.lines[i - 1] : null;
            const outgoing = i < r.lines.length ? r.lines[i] : null;
            const isTransfer = incoming && outgoing && incoming !== outgoing;
            const c = '#' + store.lines.get(isTransfer ? outgoing : code).color;
            return `<li style="--c:${c}" data-act="station" data-id="${id}"><span>${name(id)}</span>${isTransfer ? '<span class="tag">Transfer</span>' : ''}</li>`;
        }).join('');

        return `<div class="stats">
                <div class="card stat"><span class="stat-v">${(r.length / 1000).toFixed(2)}<small> km</small></span><span class="stat-k">Distance</span></div>
                <div class="card stat"><span class="stat-v">${r.transfers}</span><span class="stat-k">Transfers</span></div>
                <div class="card stat"><span class="stat-v">${r.ids.length}</span><span class="stat-k">Stations</span></div>
            </div>
            <div class="section"><h3>Line sequence</h3><div class="legs">${legs}</div></div>
            <div class="section"><h3>Stations on route</h3><ul class="timeline card" style="padding:8px 8px 8px 12px">${stops}</ul></div>`;
    },
};

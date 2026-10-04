// Dữ liệu dùng chung: tải một lần từ API hiện có, tính thêm thông tin phụ cho UI
const API = 'http://localhost:8000';
const LINE_ORDER = ['G', 'M', 'H', 'T', 'C', 'Y', 'Z', 'N', 'F'];
const LINE_NAMES = {
    G: 'Ginza', M: 'Marunouchi', H: 'Hibiya', T: 'Tozai', C: 'Chiyoda',
    Y: 'Yurakucho', Z: 'Hanzomon', N: 'Namboku', F: 'Fukutoshin',
};

const store = {
    nodes: new Map(),   // id -> {id, name, lat, lon, active, lines:Set}
    edges: new Map(),   // id -> {id, start, end, line, color, length, active, coords:[[lat,lon],...]}
    lines: new Map(),   // code -> {code, name, color, nodeIds:Set, edgeIds:[]}
    _h: {},

    // Event bus đơn giản: các panel và bản đồ không gọi nhau trực tiếp mà đăng ký lắng nghe sự kiện.
    // Sự kiện đang dùng: 'active' (ban/unban), 'selection' (chọn/bỏ chọn ga hoặc đoạn), 'lineFocus' (highlight tuyến).
    on(evt, fn) { (this._h[evt] ||= []).push(fn); },
    emit(evt, data) { (this._h[evt] || []).forEach((fn) => fn(data)); },

    async load() {
        const get = async (p) => {
            const res = await fetch(API + p);
            if (!res.ok) throw new Error(`${p} → HTTP ${res.status}`);
            return res.json();
        };
        // GET /nodes/ và GET /edges/ đều trả GeoJSON FeatureCollection:
        //   Point      → một ga (properties: id, name, active)
        //   LineString → một đoạn nối giữa hai ga (properties: id, start, end, line, color, length, active)
        const [nodeFc, edgeFc] = await Promise.all([get('/nodes/'), get('/edges/')]);

        nodeFc.features.forEach((f) => {
            const p = f.properties;
            this.nodes.set(p.id, {
                id: p.id, name: p.name, active: p.active,
                lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1],
                lines: new Set(),
            });
        });

        edgeFc.features.forEach((f) => {
            const p = f.properties;
            this.edges.set(p.id, {
                id: p.id, start: p.start, end: p.end, line: p.line, color: p.color,
                length: p.length, active: p.active,
                // GeoJSON lưu [lon, lat] còn Leaflet cần [lat, lon] nên đảo thứ tự ở đây một lần
                coords: f.geometry.coordinates.map(([lo, la]) => [la, lo]),
            });
        });

        // Dựng thông tin theo tuyến từ danh sách edge (API không có endpoint riêng cho tuyến):
        // mỗi tuyến gom các edge + ga của nó, và mỗi ga ghi nhớ nó thuộc những tuyến nào (n.lines)
        this.edges.forEach((e) => {
            let l = this.lines.get(e.line);
            if (!l) {
                l = { code: e.line, name: LINE_NAMES[e.line] || e.line, color: e.color, nodeIds: new Set(), edgeIds: [] };
                this.lines.set(e.line, l);
            }
            l.edgeIds.push(e.id);
            [e.start, e.end].forEach((id) => {
                l.nodeIds.add(id);
                const n = this.nodes.get(id);
                if (n) n.lines.add(e.line);
            });
        });
    },

    // PATCH giữ nguyên hợp đồng API cũ: body là true/false
    async setActive(kind, id, active) {
        const res = await fetch(`${API}/${kind === 'node' ? 'nodes' : 'edges'}/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(active),
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        // Chỉ cập nhật trạng thái cục bộ sau khi server xác nhận, rồi phát 'active'
        // để bản đồ và các panel tự vẽ lại
        (kind === 'node' ? this.nodes : this.edges).get(id).active = active;
        this.emit('active', { kind, id, active });
    },

    nodeName(id) { return this.nodes.get(id)?.name ?? `#${id}`; },
    edgeTitle(e) { return `${this.nodeName(e.start)} → ${this.nodeName(e.end)}`; },
    sortedLines(set) { return [...set].sort((a, b) => LINE_ORDER.indexOf(a) - LINE_ORDER.indexOf(b)); },

    // Đoạn nối còn "active" nhưng một đầu ga đã bị ban thì không dùng được khi tìm đường
    isBlocked(e) {
        return e.active && (!this.nodes.get(e.start)?.active || !this.nodes.get(e.end)?.active);
    },

    // Ga active gần nhất (haversine) — dùng để hiện ga xuất phát/đích ngay khi click
    nearestActive(lat, lon) {
        const R = 6371000, rad = Math.PI / 180;
        let best = null, bestD = Infinity;
        this.nodes.forEach((n) => {
            if (!n.active) return;
            const dp = (n.lat - lat) * rad, dl = (n.lon - lon) * rad;
            const a = Math.sin(dp / 2) ** 2 + Math.cos(lat * rad) * Math.cos(n.lat * rad) * Math.sin(dl / 2) ** 2;
            const d = 2 * R * Math.asin(Math.sqrt(a));
            if (d < bestD) { bestD = d; best = n; }
        });
        return best;
    },
};

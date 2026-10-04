// Vẽ mạng lưới lên bản đồ + trạng thái hover/selected/inactive/route
const net = {
    // id → layer Leaflet của từng đoạn nối / ga. Tạo một lần trong net.build(),
    // sau đó chỉ đổi style bằng setStyle chứ không tạo lại layer.
    edgeLayers: new Map(),
    nodeLayers: new Map(),
    // Chứa đường đi tìm được từ /path/ (vẽ đè lên mạng lưới) và hai ghim A/B ('start' | 'end')
    routeGroup: L.layerGroup().addTo(map),
    pins: {},
    // Một popup dùng chung, mỗi lần chọn chỉ đổi vị trí + nội dung
    popup: L.popup({ className: 'tk-popup', maxWidth: 300, minWidth: 230, offset: [0, -2], autoPanPadding: [50, 50] }),
    // true khi chính code đang mở/đổi popup, để handler 'popupclose' không nhầm là người dùng tự đóng popup
    _opening: false,
    // Trạng thái giao diện; style của mọi layer được tính lại từ đây (xem edgeStyle / nodeStyle)
    // showAll / showBanned: công tắc hiển thị ga-đoạn active / đã bị ban; banMode: click là ban ngay
    // lineFocus: mã tuyến đang highlight; selected / hover: { kind: 'node' | 'edge', id }
    // routeActive: đang hiển thị đường đi, mạng lưới nền bị làm mờ
    state: {
        showAll: true, showBanned: false, banMode: false,
        lineFocus: null, selected: null, hover: null, routeActive: false,
    },
};

const same = (s, kind, id) => s && s.kind === kind && s.id === id;
net.isSel = (kind, id) => same(net.state.selected, kind, id);
net.isHover = (kind, id) => same(net.state.hover, kind, id);

/* ---------- Style system: normal / hover / selected / inactive / dim / route ---------- */
// Style của mỗi layer là hàm thuần của (item, net.state): luôn tính từ đầu theo thứ tự
// kiểu gốc (active / banned) → làm mờ khi highlight tuyến hoặc đang có route → hover → selected,
// bước sau ghi đè bước trước, nên selected có ưu tiên cao nhất.

// Đoạn nối hiện ra khi: đang chọn/hover, thuộc tuyến đang highlight, hoặc đúng công tắc
// (Show All cho đoạn active, Show Banned cho đoạn bị ban)
net.edgeVisible = (e) => {
    const s = net.state;
    return net.isSel('edge', e.id) || net.isHover('edge', e.id) || s.lineFocus === e.line ||
        (e.active ? s.showAll : s.showBanned);
};

net.edgeStyle = (e) => {
    // stroke: false = ẩn đoạn nối này
    if (!net.edgeVisible(e)) return { stroke: false };
    const s = net.state;
    // Đoạn active vẽ nét liền theo màu tuyến; đoạn bị ban vẽ nét đứt màu đỏ
    const st = e.active
        ? { stroke: true, color: '#' + e.color, weight: 5, opacity: 0.8, dashArray: null, lineCap: 'round' }
        : { stroke: true, color: '#e11d48', weight: 4, opacity: 0.9, dashArray: '7 7', lineCap: 'butt' };
    if (s.lineFocus) {
        if (e.line === s.lineFocus) { st.weight = 7; st.opacity = 1; } else st.opacity = 0.15;
    } else if (s.routeActive) {
        st.opacity = e.active ? 0.22 : 0.5;
    }
    if (net.isHover('edge', e.id)) { st.weight += 3; st.opacity = 1; }
    if (net.isSel('edge', e.id)) { st.weight = 10; st.opacity = 1; }
    return st;
};

// Quy tắc hiển thị giống edgeVisible; khi highlight tuyến thì hiện mọi ga thuộc tuyến đó
net.nodeVisible = (n) => {
    const s = net.state;
    return net.isSel('node', n.id) || net.isHover('node', n.id) ||
        (s.lineFocus && n.lines.has(s.lineFocus)) || (n.active ? s.showAll : s.showBanned);
};

net.nodeStyle = (n) => {
    if (!net.nodeVisible(n)) return { stroke: false, fill: false };
    const s = net.state;
    const st = n.active
        ? { radius: 5, stroke: true, fill: true, fillColor: '#ffffff', color: '#1e293b', weight: 2, opacity: 1, fillOpacity: 1, dashArray: null }
        : { radius: 5, stroke: true, fill: true, fillColor: '#ffe4e6', color: '#e11d48', weight: 2, opacity: 1, fillOpacity: 1, dashArray: '3 3' };
    if (s.lineFocus) {
        if (!n.lines.has(s.lineFocus)) { st.opacity = 0.2; st.fillOpacity = 0.2; }
    } else if (s.routeActive) {
        st.opacity = 0.35; st.fillOpacity = 0.35;
    }
    if (net.isHover('node', n.id)) { st.radius = 8; st.opacity = 1; st.fillOpacity = 1; }
    if (net.isSel('node', n.id)) {
        st.radius = 9; st.weight = 3; st.color = '#2563eb'; st.fillColor = '#dbeafe'; st.opacity = 1; st.fillOpacity = 1; st.dashArray = null;
    }
    return st;
};

// Áp style mới cho một layer. Layer bị ẩn cũng phải tắt interactive, nếu không vẫn nhận hover/click dù không nhìn thấy.
net.restyleEdge = (id) => {
    const e = store.edges.get(id), l = net.edgeLayers.get(id);
    if (!e || !l) return;
    l.setStyle(net.edgeStyle(e));
    l.options.interactive = net.edgeVisible(e);
};
net.restyleNode = (id) => {
    const n = store.nodes.get(id), l = net.nodeLayers.get(id);
    if (!n || !l) return;
    l.setStyle(net.nodeStyle(n));
    l.options.interactive = net.nodeVisible(n);
};
net.restyleItem = (kind, id) => (kind === 'edge' ? net.restyleEdge(id) : net.restyleNode(id));
// Vẽ lại toàn bộ khi đổi trạng thái chung (công tắc, highlight tuyến, route); đổi một mục thì dùng restyleItem
net.refresh = () => {
    store.edges.forEach((_, id) => net.restyleEdge(id));
    store.nodes.forEach((_, id) => net.restyleNode(id));
};

/* ---------- Tooltip + popup ---------- */
net.edgeTip = (e) => {
    const l = store.lines.get(e.line);
    return `${lineBadge(e.line)} <b>${esc(l.name)}</b><br>${esc(store.edgeTitle(e))}<br>` +
        `<span class="muted">${fmtKm(e.length)}${e.active ? '' : ' · banned'}</span>`;
};
net.nodeTip = (n) =>
    `<b>${esc(n.name)}</b><br>${store.sortedLines(n.lines).map(lineBadge).join(' ')}` +
    (n.active ? '' : '<br><span class="muted">banned</span>');

// Trả về phần tử DOM (không phải chuỗi HTML) để gắn được listener cho nút Ban/Unban ngay bên dưới
net.popupContent = (kind, id) => {
    const div = document.createElement('div');
    div.className = 'pop';
    if (kind === 'edge') {
        const e = store.edges.get(id), l = store.lines.get(e.line);
        div.innerHTML = `
            <div class="pop-head">${lineBadge(e.line)}<span class="pop-title">${esc(l.name)} Line</span></div>
            <div class="pop-route">${esc(store.nodeName(e.start))} <span class="arrow">→</span> ${esc(store.nodeName(e.end))}</div>
            <div class="pop-meta"><span class="badge-id">#${e.id}</span>${statusPill(e.active)}<span>${fmtKm(e.length)}</span></div>
            ${store.isBlocked(e) ? '<div class="pop-warn">A station at one end is banned, so this segment cannot be used.</div>' : ''}
            <button class="btn btn-sm ${e.active ? 'btn-danger' : 'btn-primary'}" data-act="toggle">${e.active ? 'Ban segment' : 'Unban segment'}</button>`;
    } else {
        const n = store.nodes.get(id);
        div.innerHTML = `
            <div class="pop-head"><span class="pop-title">${esc(n.name)}</span></div>
            <div class="pop-meta"><span class="badge-id">#${n.id}</span>${statusPill(n.active)}</div>
            <div class="pop-meta">${store.sortedLines(n.lines).map((c) => lineBadge(c) + ' ' + esc(store.lines.get(c).name)).join(' · ')}</div>
            <button class="btn btn-sm ${n.active ? 'btn-danger' : 'btn-primary'}" data-act="toggle">${n.active ? 'Ban station' : 'Unban station'}</button>`;
    }
    div.querySelector('[data-act="toggle"]').addEventListener('click', () => net.toggle(kind, id));
    return div;
};

/* ---------- Ban / unban ---------- */
// Đảo trạng thái active của một ga/đoạn: gọi PATCH qua store.setActive, rồi báo bằng toast kèm nút Undo
// (Undo chỉ là gọi lại toggle). Mọi nguồn ban/unban (popup, sidebar, Ban Mode, Undo) đều đi qua hàm này.
net.toggle = async (kind, id) => {
    const it = (kind === 'edge' ? store.edges : store.nodes).get(id);
    const was = it.active;
    const label = kind === 'edge' ? 'segment ' + store.edgeTitle(it) : 'station ' + it.name;
    try {
        await store.setActive(kind, id, !was);
        toast((was ? 'Banned ' : 'Unbanned ') + label, { action: { label: 'Undo', fn: () => net.toggle(kind, id) } });
    } catch (err) {
        toast('Update failed: ' + err.message, { error: true });
    }
};

// Đồng bộ bản đồ sau ban/unban: store phát 'active' sau khi server đã cập nhật, ở đây vẽ lại phần bị ảnh hưởng
store.on('active', ({ kind, id }) => {
    net.restyleItem(kind, id);
    if (kind === 'node') {
        // Ga bị ban làm các đoạn nối chạm vào nó trở nên không dùng được → cập nhật popup đang mở
        store.edges.forEach((e) => { if (e.start === id || e.end === id) net.restyleEdge(e.id); });
    }
    const s = net.state.selected;
    // Popup đang mở phải dựng lại để nút đổi Ban ↔ Unban; _opening ngăn handler 'popupclose' xóa selection
    if (s && map.hasLayer(net.popup)) {
        net._opening = true;
        net.popup.setContent(net.popupContent(s.kind, s.id));
        net._opening = false;
    }
});

/* ---------- Hover / select ---------- */
// Chỉ có tối đa một mục hover; restyle mục cũ (trả về style thường) và mục mới.
// setHover(null) để bỏ hover. Đoạn nối được đưa lên trên cùng để không bị các đoạn khác che.
net.setHover = (kind, id) => {
    const prev = net.state.hover;
    net.state.hover = kind ? { kind, id } : null;
    if (prev) net.restyleItem(prev.kind, prev.id);
    if (kind) {
        net.restyleItem(kind, id);
        if (kind === 'edge') net.edgeLayers.get(id).bringToFront();
    }
};

// Chọn một ga/đoạn: highlight, mở popup, rồi phát 'selection' để sidebar đánh dấu hàng tương ứng.
// fly = true khi chọn từ sidebar (bản đồ di chuyển tới mục đó); fly = false khi click ngay trên bản đồ
// (giữ nguyên khung nhìn). Đây là chiều bản đồ ↔ sidebar: chiều ngược lại do panel_lists.js gọi net.select.
net.select = (kind, id, { fly = true } = {}) => {
    const prev = net.state.selected;
    net._opening = true;
    net.state.selected = { kind, id };
    if (prev) net.restyleItem(prev.kind, prev.id);
    net.restyleItem(kind, id);

    const layer = (kind === 'edge' ? net.edgeLayers : net.nodeLayers).get(id);
    let pos;
    // pos = vị trí neo của popup (giữa đoạn nối, hoặc tại ga)
    if (kind === 'edge') {
        layer.bringToFront();
        // Đưa các ga lên lại trên cùng để chúng không bị đoạn nối vừa được chọn che mất
        net.nodeLayers.forEach((l) => l.bringToFront());
        pos = layer.getCenter();
        if (fly) map.fitBounds(layer.getBounds(), { maxZoom: 15, padding: [90, 90] });
    } else {
        pos = layer.getLatLng();
        layer.bringToFront();
        if (fly) map.flyTo(pos, Math.max(map.getZoom(), 14), { duration: 0.6 });
    }
    // Khi bản đồ đã tự bay tới (fly) thì không cần autoPan của popup nữa
    net.popup.options.autoPan = !fly;
    net.popup.setLatLng(pos).setContent(net.popupContent(kind, id)).openOn(map);
    net._opening = false;
    store.emit('selection', net.state.selected);
};

net.clearSelection = () => {
    const prev = net.state.selected;
    if (!prev) return;
    net.state.selected = null;
    net.restyleItem(prev.kind, prev.id);
    if (map.hasLayer(net.popup)) map.closePopup(net.popup);
    store.emit('selection', null);
};

// Người dùng tự đóng popup (bấm X, click ra ngoài) thì bỏ selection; thay đổi popup do code gây ra (_opening) thì bỏ qua
map.on('popupclose', (e) => {
    if (e.popup === net.popup && !net._opening) net.clearSelection();
});

// Click trên layer: ban ngay (Ban Mode) / chọn xem thông tin / để map xử lý (tab Path chọn điểm)
net.onItemClick = (kind, id, ev) => {
    const it = (kind === 'edge' ? store.edges : store.nodes).get(id);
    // Click trên layer cũng nổi lên map.on('click') (panel_path dùng để chọn ga A/B).
    // Chỉ ở tab Path (không Ban Mode) mới để nó nổi lên; các trường hợp khác chặn lại.
    if (net.state.banMode || app.tab !== 'path') L.DomEvent.stopPropagation(ev);
    // Ban Mode: click vào mục đang active là ban ngay; unban dùng popup/sidebar/Undo
    if (net.state.banMode && it.active) { net.toggle(kind, id); return; }
    if (app.tab === 'path') return;
    if (app.tab === 'lines' && kind === 'edge') { linesPanel.focus(it.line); return; }
    net.select(kind, id, { fly: false });
};

/* ---------- Line focus ---------- */
// Highlight một tuyến (code = null để bỏ): đổi state.lineFocus, vẽ lại, tùy chọn zoom vừa khít toàn tuyến,
// rồi phát 'lineFocus' để tab Lines vẽ lại danh sách
net.focusLine = (code, { fit = true } = {}) => {
    net.clearSelection();
    net.state.lineFocus = code;
    net.refresh();
    if (code && fit) {
        const pts = store.lines.get(code).edgeIds.flatMap((id) => store.edges.get(id).coords);
        map.fitBounds(L.latLngBounds(pts), { padding: [60, 60] });
    }
    store.emit('lineFocus', code);
};

/* ---------- Route ---------- */
// Vẽ kết quả của GET /path/ (GeoJSON FeatureCollection):
//   LineString → các đoạn nối của đường đi, có properties.color của tuyến
//   Point      → các ga; không vẽ từ đây vì thứ tự Point trong features không theo đường đi
//                (thứ tự ga thật nằm ở fc.properties.id), nên ga được vẽ từ store ở bên dưới
//   fc.properties → { id[], name[], line[], total_transfers, length }
net.showRoute = (fc) => {
    net.clearRoute();
    const g = net.routeGroup;
    const segs = fc.features.filter((f) => f.geometry.type === 'LineString');
    // Đảo [lon, lat] của GeoJSON thành [lat, lon] cho Leaflet
    const ll = (f) => f.geometry.coordinates.map(([lo, la]) => [la, lo]);
    // Mỗi đoạn vẽ hai lần: nét trắng dày làm viền, nét màu tuyến mỏng hơn phủ lên trên
    segs.forEach((f) => g.addLayer(L.polyline(ll(f), { renderer, color: '#ffffff', weight: 13, opacity: 0.95, lineCap: 'round', interactive: false })));
    segs.forEach((f) => g.addLayer(L.polyline(ll(f), { renderer, color: '#' + f.properties.color, weight: 7, opacity: 1, lineCap: 'round', interactive: false })));
    // Vẽ ga theo đúng thứ tự đi; ga đầu và ga cuối vẽ to hơn
    fc.properties.id.forEach((id, i, arr) => {
        const n = store.nodes.get(id);
        const end = i === 0 || i === arr.length - 1;
        const c = L.circleMarker([n.lat, n.lon], {
            renderer, radius: end ? 7 : 5, color: '#0f172a', weight: 2, fillColor: '#ffffff', fillOpacity: 1,
        });
        c.bindTooltip(net.nodeTip(n), { className: 'tk-tip', direction: 'top', offset: [0, -6], opacity: 1 });
        g.addLayer(c);
    });
    // routeActive làm mờ mạng lưới nền để đường đi nổi bật
    net.state.routeActive = true;
    net.refresh();
    map.fitBounds(L.latLngBounds(segs.flatMap(ll)), { padding: [80, 80] });
};

net.clearRoute = () => {
    net.routeGroup.clearLayers();
    if (net.state.routeActive) {
        net.state.routeActive = false;
        net.refresh();
    }
};

// Đặt/xóa ghim A (which = 'start') hoặc B ('end') tại một ga; nodeId = null để xóa
net.setPin = (which, nodeId) => {
    if (net.pins[which]) { map.removeLayer(net.pins[which]); delete net.pins[which]; }
    if (nodeId == null) return;
    const n = store.nodes.get(nodeId);
    const icon = L.divIcon({
        className: 'pin-wrap',
        html: `<div class="pin pin-${which}"><span>${which === 'start' ? 'A' : 'B'}</span></div>`,
        iconSize: [30, 30], iconAnchor: [15, 36],
    });
    net.pins[which] = L.marker([n.lat, n.lon], { icon, interactive: false, keyboard: false, zIndexOffset: 1000 }).addTo(map);
};

/* ---------- Build ---------- */
// Tạo layer Leaflet cho mọi đoạn nối rồi mọi ga (một lần, sau khi store.load xong). Đoạn nối được thêm
// trước nên ga nằm đè lên trên. Tooltip nhận hàm để nội dung luôn lấy trạng thái mới nhất lúc hover.
net.build = () => {
    store.edges.forEach((e) => {
        const l = L.polyline(e.coords, { renderer, ...net.edgeStyle(e), interactive: net.edgeVisible(e) });
        l.bindTooltip(() => net.edgeTip(e), { sticky: true, className: 'tk-tip', direction: 'top', opacity: 1 });
        l.on({
            mouseover: () => net.setHover('edge', e.id),
            mouseout: () => net.setHover(null),
            click: (ev) => net.onItemClick('edge', e.id, ev),
        });
        l.addTo(map);
        net.edgeLayers.set(e.id, l);
    });
    store.nodes.forEach((n) => {
        const l = L.circleMarker([n.lat, n.lon], { renderer, ...net.nodeStyle(n), interactive: net.nodeVisible(n) });
        l.bindTooltip(() => net.nodeTip(n), { className: 'tk-tip', direction: 'top', offset: [0, -8], opacity: 1 });
        l.on({
            mouseover: () => net.setHover('node', n.id),
            mouseout: () => net.setHover(null),
            click: (ev) => net.onItemClick('node', n.id, ev),
        });
        l.addTo(map);
        net.nodeLayers.set(n.id, l);
    });
    // Route (nếu có) luôn nằm trên mạng lưới
    net.routeGroup.eachLayer((l) => l.bringToFront && l.bringToFront());
};

net.fitAll = () => {
    const pts = [];
    store.nodes.forEach((n) => pts.push([n.lat, n.lon]));
    map.fitBounds(L.latLngBounds(pts), { padding: [40, 40] });
};

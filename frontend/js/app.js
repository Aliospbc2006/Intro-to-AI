// Khởi động ứng dụng: tải dữ liệu, dựng bản đồ + các panel, nối công tắc và tab
function setTab(tab) {
    if (app.tab === tab) return;
    const leaving = app.tab;
    app.tab = tab;
    document.querySelectorAll('.tab').forEach((b) => {
        const on = b.dataset.tab === tab;
        b.classList.toggle('on', on);
        b.setAttribute('aria-selected', on);
    });
    document.querySelectorAll('.panel').forEach((p) => { p.hidden = p.dataset.panel !== tab; });
    // Mỗi tab có trạng thái chọn riêng: bỏ highlight khi rời đi
    net.clearSelection();
    if (leaving === 'lines' && net.state.lineFocus) net.focusLine(null);
    if (tab === 'path') pathPanel.render();
    if (tab === 'segments') segmentsPanel.markSelected(false);
}

function updateBanner() {
    const b = document.getElementById('mapBanner');
    const s = net.state;
    document.body.classList.toggle('ban-mode', s.banMode);
    if (s.banMode) {
        b.className = 'map-banner ban';
        b.textContent = 'Ban Mode — click a station or segment to ban it';
        b.hidden = false;
    } else if (app.tab === 'path' && pathPanel.picking) {
        b.className = 'map-banner';
        b.textContent = pathPanel.picking === 'start' ? 'Click the map to choose the start station' : 'Click the map to choose the end station';
        b.hidden = false;
    } else {
        b.hidden = true;
    }
}

function bindToggle(id, key) {
    document.getElementById(id).addEventListener('change', (e) => {
        net.state[key] = e.target.checked;
        if (key === 'banMode') net.clearSelection();
        net.refresh();
        updateBanner();
    });
}

(async function main() {
    const err = document.getElementById('loadError');
    try {
        await store.load();
    } catch (e) {
        err.hidden = false;
        err.textContent = 'Cannot load the network from the API (' + e.message + '). Make sure the backend is running on ' + API + '.';
        return;
    }
    net.build();
    net.fitAll();

    pathPanel.init();
    linesPanel.init();
    segmentsPanel.init();
    stationsPanel.init();

    document.querySelectorAll('.tab').forEach((b) => b.addEventListener('click', () => { setTab(b.dataset.tab); updateBanner(); }));
    bindToggle('showAllSwitch', 'showAll');
    bindToggle('showBannedSwitch', 'showBanned');
    bindToggle('banModeSwitch', 'banMode');

    // Ban/Unban có thể xảy ra ở bất kỳ tab nào → bản đồ tự cập nhật qua store 'active' (xem map_layers.js)
    updateBanner();
})();

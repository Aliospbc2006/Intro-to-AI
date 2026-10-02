const map = L.map('map', {
    center: [35.6812, 139.7671],
    zoom: 12,
});

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
}).addTo(map);

if (!map.getPane('nodesPane')) {
    map.createPane('nodesPane');
    map.getPane('nodesPane').style.zIndex = 650;
    map.getPane('nodesPane').style.pointerEvents = 'none';
}
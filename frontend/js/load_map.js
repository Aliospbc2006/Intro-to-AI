// Khởi tạo bản đồ Leaflet ở trung tâm Tokyo; biến toàn cục `map` được các file js khác dùng chung
const map = L.map('map', {
    center: [35.6812, 139.7671],
    zoom: 12,
});

L.tileLayer('https://tile.openstreetmap.de/{z}/{x}/{y}.png', {
    attribution: 'Data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors (<a href="https://opendatacommons.org/licenses/odbl/">ODbL</a>), tiles <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a> by <a href="https://www.openstreetmap.de/">OpenStreetMap Deutschland</a> (FOSSGIS e.V.), <a href="https://www.openstreetmap.org/fixthemap">report a map error</a>',
    maxZoom: 19,
}).addTo(map);

// Một canvas duy nhất cho toàn bộ ga/đoạn nối: nhẹ hơn SVG và mọi layer cùng nhận chuột
const renderer = L.canvas({ padding: 0.5, tolerance: 5 });

let selectedPoints = [];
let isPathDisplaying = false;
let canSelectPoints = false;

const userClickLayer = L.layerGroup().addTo(map);

const pathEdgesLayer = L.geoJSON(null, {
    style: (feature) => ({
        color: `#${feature.properties.color}`,
        weight: 8,
        opacity: 0.8,
        lineJoin: 'round'
    })
}).addTo(map);

const pathNodesLayer = L.geoJSON(null, {
    pointToLayer: (feature, latlng) => {
        const marker = L.circleMarker(latlng, {
            radius: 6,
            fillColor: "#ffffff",
            color: "#000000",
            weight: 2,
            fillOpacity: 1,
            interactive: false
        });

        const hitArea = L.circleMarker(latlng, {
            radius: 16,
            stroke: false,
            fillColor: 'transparent',
            fillOpacity: 0,
            interactive: true
        });

        hitArea.bindPopup(`<b>${feature.properties.name}</b>`, { closeButton: false });

        hitArea.on('mouseover', () => {
            marker.setRadius(10);
            hitArea.openPopup();
        });

        hitArea.on('mouseout', () => {
            marker.setRadius(6);
            hitArea.closePopup();
        });

        return L.layerGroup([marker, hitArea]);
    }
}).addTo(map);

function updatePanelUI(mode, data = {}) {
    const panel = document.querySelector('.custom-panel');

    if (mode === 'inputPenalty') {
        panel.innerHTML = `
            <div class="mb-3">
                <label class="form-label fw-bold fs-5" for="penaltyInput">Transfer Penalty (m)</label>
                <input type="number" id="penaltyInput" class="form-control fs-5" value="2000">
            </div>
            <div class="d-grid gap-2">
                <button class="btn btn-primary" id="executeSearchBtn">
                    <i class="bi bi-search"></i> Find Path
                </button>
                <button class="btn btn-outline-secondary" onclick="location.reload()">Cancel</button>
            </div>
        `;
        document.getElementById('executeSearchBtn').addEventListener('click', getPath);
    }
    else if (mode === 'result') {
        panel.innerHTML = `
            <div class="result-box mb-3">
                <h5 class="text-primary border-bottom pb-2">Path Statistics</h5>
                <div class="fs-5 mb-2">
                    <b>Transfers:</b> <span class="badge bg-info text-dark">${data.total_transfers}</span>
                </div>
                <div class="fs-5 mb-3">
                    <b>Length:</b> <span class="text-success fw-bold">${(data.length / 1000).toFixed(2)} km</span>
                </div>
            </div>
            <div class="d-grid gap-2">
                <button class="btn btn-primary" onclick="location.reload()">
                    <i class="bi bi-arrow-clockwise"></i> New Search
                </button>
            </div>
        `;
    }
    else if (mode === 'error') {
        panel.innerHTML = `
            <div class="result-box mb-3">
                <h5 class="text-danger border-bottom pb-2">No Path Found</h5>
                <p class="fs-5 text-muted mb-3">
                    Try picking different locations.
                </p>
            </div>
            <div class="d-grid gap-2">
                <button class="btn btn-secondary" onclick="location.reload()">
                    <i class="bi bi-arrow-left"></i> Try Again
                </button>
            </div>
        `;
    }
}

async function getPath() {
    const penaltyInput = document.getElementById('penaltyInput');
    const penalty = penaltyInput ? penaltyInput.value : 2000;
    const [p1, p2] = selectedPoints;

    const btn = document.getElementById('executeSearchBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Searching...';
    }

    const url = `http://localhost:8000/path?lon1=${p1.lng}&lat1=${p1.lat}&lon2=${p2.lng}&lat2=${p2.lat}&penalty=${penalty}`;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error("Network error");

        const featureCollection = await response.json();

        pathEdgesLayer.clearLayers();
        pathNodesLayer.clearLayers();

        const edges = {
            type: "FeatureCollection",
            features: featureCollection.features.filter(f => f.geometry.type === "LineString")
        };

        const nodes = {
            type: "FeatureCollection",
            features: featureCollection.features.filter(f => f.geometry.type === "Point")
        };

        if (edges.features.length === 0) {
            updatePanelUI('error');
            return;
        }

        pathEdgesLayer.addData(edges);
        pathNodesLayer.addData(nodes);

        const meta = featureCollection.properties;
        updatePanelUI('result', {
            total_transfers: meta.total_transfers,
            length: meta.length
        });

        map.fitBounds(pathEdgesLayer.getBounds(), { padding: [50, 50] });
        isPathDisplaying = true;
        canSelectPoints = false;

    } catch (err) {
        console.error(err);
        updatePanelUI('error');
        isPathDisplaying = false;
        canSelectPoints = false;
    }
}
document.getElementById('findPathBtn').addEventListener('click', function () {
    canSelectPoints = true;
    isPathDisplaying = false;
    selectedPoints = [];

    userClickLayer.clearLayers();
    pathEdgesLayer.clearLayers();
    pathNodesLayer.clearLayers();

    const panel = document.querySelector('.custom-panel');
    panel.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-grow spinner-grow-sm text-primary mb-2" role="status"></div>
            <p class="mb-0 fw-bold fs-5">Select 2 points</p>
            <p class="text-muted">Click on map to set Start and End</p>
            <button class="btn btn-outline-danger mt-2" onclick="location.reload()">Cancel</button>
        </div>
    `;
});

map.on('click', function (e) {
    if (!canSelectPoints || isPathDisplaying) return;

    const { lat, lng } = e.latlng;

    if (selectedPoints.length < 2) {
        selectedPoints.push({ lat, lng });

        L.marker([lat, lng]).addTo(userClickLayer);

        if (selectedPoints.length === 2) {
            updatePanelUI('inputPenalty');
        }
    }
});
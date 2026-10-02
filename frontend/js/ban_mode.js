let banModeLayers = null;
document.getElementById('banModeSwitch').addEventListener('change', function (e) {
    if (e.target.checked) {
        Promise.all([
            fetch('http://localhost:8000/edges/?active=true').then(res => res.json()),
            fetch('http://localhost:8000/nodes/?active=true').then(res => res.json())
        ]).then(([edgesGeoJson, nodesGeoJson]) => {

            const edgesLayer = L.geoJSON(edgesGeoJson, {
                style: (feature) => ({
                    color: `#${feature.properties.color}`,
                    weight: 8,
                    opacity: 0.8,
                    lineCap: 'round'
                }),
                onEachFeature: (feature, layer) => {
                    layer.on({
                        mouseover: (ev) => {
                            ev.target.setStyle({ weight: 16, opacity: 1 });
                            ev.target.bringToFront();
                        },
                        mouseout: (ev) => edgesLayer.resetStyle(ev.target),
                        click: (ev) => {
                            edgesLayer.removeLayer(ev.target);
                            const edgeId = feature.properties.id;
                            fetch(`http://localhost:8000/edges/${edgeId}`, {
                                method: 'PATCH',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(false)
                            });
                        }
                    });
                }
            });

            const nodesLayer = L.geoJSON(nodesGeoJson, {
                pointToLayer: (feature, latlng) => {
                    const marker = L.circleMarker(latlng, {
                        radius: 6, fillColor: "#ffffff", color: "#000000",
                        weight: 2, fillOpacity: 1, interactive: false, pane: 'nodesPane'
                    });
                    const hitArea = L.circleMarker(latlng, {
                        radius: 16, stroke: false, fillColor: 'transparent',
                        fillOpacity: 0, interactive: true, pane: 'nodesPane'
                    });

                    const nodeGroup = L.layerGroup([marker, hitArea]);
                    hitArea.bindPopup(`<b>${feature.properties.name}</b>`, { closeButton: false });

                    hitArea.on('mouseover', () => { marker.setRadius(10); hitArea.openPopup(); });
                    hitArea.on('mouseout', () => { marker.setRadius(6); hitArea.closePopup(); });

                    hitArea.on('click', () => {
                        nodesLayer.removeLayer(nodeGroup);
                        const nodeId = feature.properties.id;
                        fetch(`http://localhost:8000/nodes/${nodeId}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(false)
                        });
                    });

                    return nodeGroup;
                }
            });

            banModeLayers = L.layerGroup([edgesLayer, nodesLayer]).addTo(map);
        });
    } else {
        if (banModeLayers) {
            map.removeLayer(banModeLayers);
            banModeLayers = null;
        }
    }
});
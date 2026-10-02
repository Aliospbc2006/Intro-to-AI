let allRoutesLayers = null;

document.getElementById('showAllSwitch').addEventListener('change', function (e) {
    if (e.target.checked) {
        Promise.all([
            fetch('http://localhost:8000/edges').then(res => res.json()),
            fetch('http://localhost:8000/nodes').then(res => res.json())
        ]).then(([edgesGeoJson, nodesGeoJson]) => {

            const edgesLayer = L.geoJSON(edgesGeoJson, {
                style: function (feature) {
                    return {
                        color: `#${feature.properties.color}`,
                        weight: 8,
                        opacity: 0.8
                    };
                }
            });

            const nodesLayer = L.geoJSON(nodesGeoJson, {
                pointToLayer: function (feature, latlng) {
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

                    hitArea.on('mouseover', function () {
                        marker.setRadius(10);
                        hitArea.openPopup();
                    });

                    hitArea.on('mouseout', function () {
                        marker.setRadius(6);
                        hitArea.closePopup();
                    });

                    return L.layerGroup([marker, hitArea]);
                }
            });

            allRoutesLayers = L.layerGroup([edgesLayer, nodesLayer]).addTo(map);

        }).catch(err => {
            e.target.checked = false;
        });

    } else {
        if (allRoutesLayers) {
            map.removeLayer(allRoutesLayers);
            allRoutesLayers = null;
        }
    }
});
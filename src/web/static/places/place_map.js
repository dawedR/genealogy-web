const LEAFLET_ROOT = "/static/vendor/leaflet-1.9.4";
const OSM_TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
let leafletPromise = null;
let activeMap = null;

export function renderPlaceMap({appUrl, point}) {
    destroyPlaceMap();
    const section = document.createElement("section");
    section.className = "places-workbench-map";
    const heading = document.createElement("h4");
    heading.textContent = point.title;
    const details = document.createElement("p");
    details.textContent = `${point.name} — ${coordinates(point)}`;
    const canvas = document.createElement("div");
    canvas.className = "places-workbench-map-canvas";
    canvas.setAttribute("aria-label", `Carte de ${point.name}`);
    const availability = document.createElement("p");
    availability.className = "places-workbench-map-availability";
    availability.hidden = true;
    section.append(heading, details, canvas, availability);

    loadLeaflet(appUrl).then(leaflet => {
        if (!canvas.isConnected) return;
        const map = leaflet.map(canvas, {
            attributionControl: true,
            zoomControl: true,
        }).setView([point.latitude, point.longitude], 12);
        const resizeObserver = window.ResizeObserver
            ? new ResizeObserver(() => map.invalidateSize({pan: false}))
            : null;
        resizeObserver?.observe(canvas);
        activeMap = {map, resizeObserver};
        let tileFailureReported = false;
        leaflet.tileLayer(OSM_TILES, {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors",
        }).on("tileerror", () => {
            if (tileFailureReported) return;
            tileFailureReported = true;
            availability.hidden = false;
            availability.textContent =
                "Le fond cartographique est indisponible ; la position reste indiquée ci-dessus.";
        }).addTo(map);
        const marker = leaflet.marker([point.latitude, point.longitude], {
            draggable: false,
            icon: leaflet.divIcon({
                className: "places-workbench-map-pin-container",
                html: '<span class="places-workbench-map-pin" aria-hidden="true"></span>',
                iconSize: [28, 36],
                iconAnchor: [14, 36],
            }),
        }).addTo(map);
        marker.bindPopup(popupContent(point));
        requestAnimationFrame(() => map.invalidateSize());
    }).catch(() => {
        availability.hidden = false;
        availability.textContent =
            "La carte ne peut pas être chargée ; les coordonnées restent disponibles ci-dessus.";
    });
    return section;
}

export function destroyPlaceMap() {
    if (activeMap) {
        activeMap.resizeObserver?.disconnect();
        activeMap.map.remove();
    }
    activeMap = null;
}

function loadLeaflet(appUrl) {
    if (window.L?.map) return Promise.resolve(window.L);
    if (leafletPromise) return leafletPromise;
    leafletPromise = Promise.all([
        loadStyle(appUrl(`${LEAFLET_ROOT}/leaflet.css`)),
        loadScript(appUrl(`${LEAFLET_ROOT}/leaflet.js`)),
    ]).then(() => {
        if (!window.L?.map) throw new Error("Leaflet unavailable");
        return window.L;
    });
    return leafletPromise;
}

function loadStyle(href) {
    const existing = document.querySelector(`link[data-place-map-style="${href}"]`);
    if (existing) return Promise.resolve();
    return new Promise((resolve, reject) => {
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = href;
        link.dataset.placeMapStyle = href;
        link.addEventListener("load", resolve, {once: true});
        link.addEventListener("error", reject, {once: true});
        document.head.appendChild(link);
    });
}

function loadScript(src) {
    const existing = document.querySelector(`script[data-place-map-script="${src}"]`);
    if (existing) return Promise.resolve();
    return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.async = true;
        script.dataset.placeMapScript = src;
        script.addEventListener("load", resolve, {once: true});
        script.addEventListener("error", reject, {once: true});
        document.head.appendChild(script);
    });
}

function popupContent(point) {
    const content = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = point.name;
    const values = document.createElement("div");
    values.textContent = coordinates(point);
    content.append(name, values);
    return content;
}

function coordinates(point) {
    return `${Number(point.latitude).toFixed(6)}, ${Number(point.longitude).toFixed(6)}`;
}

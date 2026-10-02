const fanViewChart = document.querySelector("#fan-view-chart");
const fanViewContainer = document.querySelector("#fan-view-container");
const fanViewStage = document.querySelector("#fan-view-stage");
const fanViewTitle = document.querySelector("#fan-view-title");
const fanViewStatus = document.querySelector("#fan-view-status");
const fanViewLegend = document.querySelector("#fan-view-legend");
const fanViewLegendList = document.querySelector("#fan-view-legend-list");
const fanViewGenerations = document.querySelector("#fan-view-generations");
const fanViewColorMode = document.querySelector("#fan-view-color-mode");
let fanViewRequestSerial = 0;
let fanViewOptions = parseFanViewOptions(new URLSearchParams(window.location.search));
let fanNaturalSize = {width: 0, height: 0};
const fanNavigation = createViewportNavigation({
    viewport: fanViewContainer, stage: fanViewStage,
    getNaturalSize: () => fanNaturalSize,
    applyContentZoom: zoom => { fanViewChart.style.width = `${fanNaturalSize.width * zoom}px`; fanViewChart.style.height = `${fanNaturalSize.height * zoom}px`; },
    zoomOutput: document.querySelector("#fan-view-zoom"), zoomOutButton: document.querySelector("#fan-view-zoom-out"), zoomInButton: document.querySelector("#fan-view-zoom-in"), fitButton: document.querySelector("#fan-view-fit"), actualSizeButton: document.querySelector("#fan-view-actual-size"),
    isPanTarget: target => !target.closest("button, input, select, label"),
});
if (fanViewOptions === null) fanViewStatus.textContent = "Paramètres d’éventail invalides ou incomplets.";
else { fanViewGenerations.value = fanViewOptions.generations; fanViewColorMode.value = fanViewOptions.colorMode; loadFanView(); }
fanViewGenerations.addEventListener("change", reloadFanView);
fanViewColorMode.addEventListener("change", reloadFanView);

function parseFanViewOptions(params) {
    const personId = params.get("person_id");
    const generations = Number(params.get("generations"));
    const colorMode = params.get("color_mode");
    if (!personId || !Number.isInteger(generations) || generations < 1 || generations > 10 || !["NONE", "BIRTH_PLACE"].includes(colorMode)) return null;
    const bool = (name, fallback) => params.has(name) ? params.get(name) === "true" : fallback;
    return {personId, generations, colorMode, openingAngle: Number(params.get("opening_angle") || 240), showUnknown: bool("show_unknown", true), labelConfig: {showSosa: bool("show_sosa", true), showName: bool("show_name", true), showBirth: bool("show_birth", true), showBirthPlace: bool("show_birth_place", false), showDeath: bool("show_death", true), showDeathPlace: bool("show_death_place", false)}};
}
function replaceFanViewUrl() {
    const o = fanViewOptions;
    const params = new URLSearchParams({person_id: o.personId, generations: String(o.generations), color_mode: o.colorMode, opening_angle: String(o.openingAngle), show_unknown: String(o.showUnknown), show_sosa: String(o.labelConfig.showSosa), show_name: String(o.labelConfig.showName), show_birth: String(o.labelConfig.showBirth), show_birth_place: String(o.labelConfig.showBirthPlace), show_death: String(o.labelConfig.showDeath), show_death_place: String(o.labelConfig.showDeathPlace)});
    window.history.replaceState(null, "", `/fan-view?${params.toString()}`);
}
function reloadFanView() {
    const generations = Number(fanViewGenerations.value);
    if (!Number.isInteger(generations) || generations < 1 || generations > 10) { fanViewStatus.textContent = "Les générations doivent être comprises entre 1 et 10."; return; }
    fanViewOptions.generations = generations; fanViewOptions.colorMode = fanViewColorMode.value; replaceFanViewUrl(); loadFanView();
}
async function loadFanView() {
    const requestSerial = ++fanViewRequestSerial;
    fanViewStatus.textContent = "Calcul de l’éventail…";
    clearFanLegend(fanViewLegend, fanViewLegendList);
    try {
        const response = await fetch(`/people/${encodeURIComponent(fanViewOptions.personId)}/sosa?${new URLSearchParams({generations: String(fanViewOptions.generations), color_mode: fanViewOptions.colorMode}).toString()}`);
        const occurrences = await response.json();
        if (requestSerial !== fanViewRequestSerial) return;
        if (!response.ok) throw new Error(occurrences.detail || "Impossible de calculer l’éventail");
        renderFanChart(fanViewChart, occurrences, fanViewOptions);
        renderFanLegend(fanViewLegend, fanViewLegendList, occurrences, fanViewOptions.showUnknown, fanViewOptions.colorMode);
        const [x, y, width, height] = fanViewChart.getAttribute("viewBox").split(" ").map(Number);
        fanNaturalSize = {width, height};
        fanViewChart.setAttribute("width", width); fanViewChart.setAttribute("height", height);
        fanNavigation.actualSize();
        fanNavigation.center({x: x + width / 2, y: y + height / 2});
        fanViewTitle.textContent = "Éventail d’ascendance";
        fanViewStatus.textContent = `${occurrences.length} positions Sosa`;
    } catch (error) { if (requestSerial === fanViewRequestSerial) fanViewStatus.textContent = error.message; }
}

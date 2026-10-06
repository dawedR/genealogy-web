const treeViewChart = document.querySelector("#tree-view-chart");
const treeViewGenerationScale = document.querySelector("#tree-view-generation-scale");
const treeViewContainer = document.querySelector("#tree-view-container");
const treeViewStage = document.querySelector("#tree-view-stage");
const treeViewTitle = document.querySelector("#tree-view-title");
const treeViewStatus = document.querySelector("#tree-view-status");
const treeViewDiagnostics = document.querySelector("#tree-view-diagnostics");
const treeViewAncestorGenerations = document.querySelector("#tree-view-ancestor-generations");
const treeViewDescendantGenerations = document.querySelector("#tree-view-descendant-generations");
const treeViewShowGenerationScale = document.querySelector("#tree-view-show-generation-scale");
const treeViewZoomOut = document.querySelector("#tree-view-zoom-out");
const treeViewZoomIn = document.querySelector("#tree-view-zoom-in");
const treeViewZoomValue = document.querySelector("#tree-view-zoom");
const treeViewFit = document.querySelector("#tree-view-fit");
const treeViewActualSize = document.querySelector("#tree-view-actual-size");

let treeViewRequestSerial = 0;
let currentTree = null;
let treeViewOptions = parseTreeViewOptions(new URLSearchParams(window.location.search));
const treeNavigation = createViewportNavigation({
    viewport: treeViewContainer,
    stage: treeViewStage,
    getNaturalSize: () => currentTree === null ? {width: 0, height: 0} : {
        width: currentTree.layout.width + (treeViewOptions?.showGenerationScale ? generationScaleWidth : 0),
        height: currentTree.layout.height,
    },
    applyContentZoom: zoom => {
        if (currentTree === null) return;
        treeViewChart.style.width = `${currentTree.layout.width * zoom}px`;
        treeViewChart.style.height = `${currentTree.layout.height * zoom}px`;
        if (!treeViewGenerationScale.hidden) {
            treeViewGenerationScale.style.width = `${generationScaleWidth * zoom}px`;
            treeViewGenerationScale.style.height = `${currentTree.layout.height * zoom}px`;
        }
    },
    zoomOutput: treeViewZoomValue,
    zoomOutButton: treeViewZoomOut,
    zoomInButton: treeViewZoomIn,
    fitButton: treeViewFit,
    actualSizeButton: treeViewActualSize,
    isPanTarget: target => !target.closest(".tree-person-card, .tree-portrait, .tree-person-label, button, input, label"),
});

if (treeViewOptions === null) {
    treeViewStatus.textContent = "Paramètres d’arbre invalides ou incomplets.";
} else {
    synchronizeControls();
    loadDedicatedTree();
}

treeViewAncestorGenerations.addEventListener("change", updateGenerationsAndReload);
treeViewDescendantGenerations.addEventListener("change", updateGenerationsAndReload);
treeViewShowGenerationScale.addEventListener("change", () => {
    if (treeViewOptions === null || currentTree === null) return;
    const rootBefore = rootCenterInTreeStage({
        stage: treeViewStage,
        treeSvg: treeViewChart,
        tree: currentTree,
        zoom: treeNavigation.zoom,
    });
    treeViewOptions.showGenerationScale = treeViewShowGenerationScale.checked;
    replaceTreeViewUrl();
    renderScale();
    treeNavigation.syncSize();
    preserveTreeRootPosition({
        viewport: treeViewContainer,
        stage: treeViewStage,
        treeSvg: treeViewChart,
        tree: currentTree,
        before: rootBefore,
        zoom: treeNavigation.zoom,
    });
});

function parseTreeViewOptions(params) {
    const personId = params.get("person_id");
    const ancestorGenerations = parseGeneration(params.get("ancestor_generations"));
    const descendantGenerations = parseGeneration(params.get("descendant_generations"));
    if (personId === null || personId === "" || ancestorGenerations === null || descendantGenerations === null) return null;
    return {personId, ancestorGenerations, descendantGenerations, showGenerationScale: params.get("show_generation_scale") === "true"};
}

function parseGeneration(value) {
    if (value === null || !/^\d+$/.test(value)) return null;
    const generation = Number(value);
    return generation >= 0 && generation <= 10 ? generation : null;
}

function synchronizeControls() {
    treeViewAncestorGenerations.value = treeViewOptions.ancestorGenerations;
    treeViewDescendantGenerations.value = treeViewOptions.descendantGenerations;
    treeViewShowGenerationScale.checked = treeViewOptions.showGenerationScale;
}

function replaceTreeViewUrl() {
    const params = new URLSearchParams({person_id: treeViewOptions.personId, ancestor_generations: String(treeViewOptions.ancestorGenerations), descendant_generations: String(treeViewOptions.descendantGenerations), show_generation_scale: String(treeViewOptions.showGenerationScale)});
    window.history.replaceState(null, "", appUrl(`/tree-view?${params.toString()}`));
}

function updateGenerationsAndReload() {
    const ancestorGenerations = parseGeneration(treeViewAncestorGenerations.value);
    const descendantGenerations = parseGeneration(treeViewDescendantGenerations.value);
    if (treeViewOptions === null || ancestorGenerations === null || descendantGenerations === null) {
        treeViewStatus.textContent = "Les générations doivent être comprises entre 0 et 10.";
        return;
    }
    treeViewOptions.ancestorGenerations = ancestorGenerations;
    treeViewOptions.descendantGenerations = descendantGenerations;
    replaceTreeViewUrl();
    loadDedicatedTree();
}

async function loadDedicatedTree() {
    const requestSerial = ++treeViewRequestSerial;
    const query = new URLSearchParams({ancestor_generations: String(treeViewOptions.ancestorGenerations), descendant_generations: String(treeViewOptions.descendantGenerations), show_siblings: "false"});
    treeViewStatus.textContent = "Calcul de l’arbre familial…";
    treeViewDiagnostics.hidden = true;
    try {
        const response = await fetch(appUrl(`/people/${encodeURIComponent(treeViewOptions.personId)}/tree?${query.toString()}`));
        const tree = await response.json();
        if (requestSerial !== treeViewRequestSerial) return;
        if (!response.ok) throw new Error(tree.detail || "Impossible de calculer l’arbre familial");
        currentTree = tree;
        renderTree(treeViewChart, tree, {naturalSize: true});
        finalizeStructuralTreeRender();
        const rootCard = tree.person_cards.find(card => card.occurrence_id === tree.root_occurrence_id);
        const rootName = rootCard === undefined ? "?" : [rootCard.display_given_name, rootCard.display_surname].filter(Boolean).join(" ") || "?";
        treeViewTitle.textContent = `Arbre familial — ${rootName}`;
        treeViewStatus.textContent = `${tree.person_occurrences.length} occurrences`;
        if (tree.diagnostics.length > 0) {
            treeViewDiagnostics.textContent = `${tree.diagnostics.length} diagnostic${tree.diagnostics.length > 1 ? "s" : ""} dans les données`;
            treeViewDiagnostics.hidden = false;
        }
    } catch (error) {
        if (requestSerial === treeViewRequestSerial) treeViewStatus.textContent = error.message;
    }
}
function finalizeStructuralTreeRender() {
    treeNavigation.resetToActualSize();
    renderScale();
    treeNavigation.syncSize();
    resetTreeViewportToRoot({
        viewport: treeViewContainer,
        stage: treeViewStage,
        treeSvg: treeViewChart,
        tree: currentTree,
    });
}

function renderScale() {
    if (currentTree === null || !treeViewOptions.showGenerationScale) {
        treeViewGenerationScale.hidden = true;
        treeViewGenerationScale.innerHTML = "";
        return;
    }
    treeViewGenerationScale.hidden = false;
    renderGenerationScale(treeViewGenerationScale, currentTree, {naturalSize: true});
}

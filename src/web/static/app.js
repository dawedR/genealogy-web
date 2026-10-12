const importForm = document.querySelector("#import-form");
const fileInput = document.querySelector("#gedcom-file");
const importStatus = document.querySelector("#import-status");
const importReport = document.querySelector("#import-report");
const gedcomStatus = document.querySelector("#gedcom-status");

const searchForm = document.querySelector("#search-form");
const searchQuery = document.querySelector("#search-query");
const searchResults = document.querySelector("#search-results");

const selectedPerson = document.querySelector("#selected-person");

const importDetails =
    document.querySelector("#import-details");

const warningsSection =
    document.querySelector("#warnings-section");

const warningsList =
    document.querySelector("#warnings-list");

const ignoredTagsSection =
    document.querySelector("#ignored-tags-section");

const ignoredTagsList =
    document.querySelector("#ignored-tags-list");

const fanGenerations =
    document.querySelector("#fan-generations");

const fanOpening =
    document.querySelector("#fan-opening");

const fanOpeningValue =
    document.querySelector("#fan-opening-value");

const fanShowUnknown =
    document.querySelector("#fan-show-unknown");

const fanColorMode =
    document.querySelector("#fan-color-mode");

const fanRenderButton =
    document.querySelector("#fan-render");

const openFanViewButton =
    document.querySelector("#open-fan-view");

const fanStatus =
    document.querySelector("#fan-status");

const fanChart =
    document.querySelector("#fan-chart");

const fanLegend =
    document.querySelector("#fan-legend");

const fanLegendList =
    document.querySelector("#fan-legend-list");

const treeAncestorGenerations =
    document.querySelector("#tree-ancestor-generations");

const treeDescendantGenerations =
    document.querySelector("#tree-descendant-generations");

const treeShowGenerationScale =
    document.querySelector("#tree-show-generation-scale");

const treeGenerationScale =
    document.querySelector("#tree-generation-scale");


const treeContainer =
    document.querySelector("#tree-container");

const treeStage =
    document.querySelector("#tree-stage");
const treeStatus =
    document.querySelector("#tree-status");

const treeChart =
    document.querySelector("#tree-chart");

const treeDiagnostics =
    document.querySelector("#tree-diagnostics");

const openTreeViewButton =
    document.querySelector("#open-tree-view");

const DEFAULT_PERSON_ID = "@I1@";

let treeRequestSerial = 0;
let fanRequestSerial = 0;
let selectionRequestSerial = 0;
let currentTree = null;

const fanLabelSosa =
    document.querySelector("#fan-label-sosa");

const fanLabelName =
    document.querySelector("#fan-label-name");

const fanLabelBirth =
    document.querySelector("#fan-label-birth");

const fanLabelBirthPlace =
    document.querySelector("#fan-label-birth-place");

const fanLabelDeath =
    document.querySelector("#fan-label-death");

const fanLabelDeathPlace =
    document.querySelector("#fan-label-death-place");

const fanLabelControls = [
    fanLabelSosa,
    fanLabelName,
    fanLabelBirth,
    fanLabelBirthPlace,
    fanLabelDeath,
    fanLabelDeathPlace,
];

for (const control of fanLabelControls) {
    control.addEventListener("change", () => {
        if (selectedPersonId !== null) {
            loadFanChart(selectedPersonId);
        }
    });
}

let selectedPersonId = null;
let placesWorkspace = null;
let placesWorkspaceInitialization = null;


importForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const file = fileInput.files[0];

    if (!file) {
        return;
    }

    importStatus.textContent = "Import en cours…";
    importReport.hidden = true;
    importDetails.hidden = true;
    warningsSection.hidden = true;
    ignoredTagsSection.hidden = true;
    warningsList.innerHTML = "";
    ignoredTagsList.innerHTML = "";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(appUrl("/imports"), {
            method: "POST",
            body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Échec de l'import"
            );
        }

        document.querySelector("#persons-count").textContent =
            data.persons_count;

        document.querySelector("#families-count").textContent =
            data.families_count;

        document.querySelector("#events-count").textContent =
            data.events_count;

        document.querySelector("#places-count").textContent =
            data.places_count;

        importReport.hidden = false;
        importStatus.textContent =
            `Import réussi : ${data.filename}`;
        
        renderImportDetails(data);
        await loadGedcomStatus();
        await refreshPlacesWorkspace();

        clearPersonSelection();
        searchResults.innerHTML = "";
        await selectDefaultPerson();

    } catch (error) {
        importStatus.textContent = error.message;
    }
});


searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const query = searchQuery.value.trim();

    if (!query) {
        return;
    }

    searchResults.textContent = "Recherche…";

    try {
        const response = await fetch(
            appUrl(`/people?q=${encodeURIComponent(query)}`)
        );

        const people = await response.json();

        if (!response.ok) {
            throw new Error("Échec de la recherche");
        }

        renderSearchResults(people);

    } catch (error) {
        searchResults.textContent = error.message;
    }
});


fanRenderButton.addEventListener("click", () => {
    if (selectedPersonId !== null) {
        loadFanChart(selectedPersonId);
    }
});

fanGenerations.addEventListener("change", () => {
    if (selectedPersonId !== null) loadFanChart(selectedPersonId);
});
fanShowUnknown.addEventListener("change", () => {
    if (selectedPersonId !== null) loadFanChart(selectedPersonId);
});
fanColorMode.addEventListener("change", () => {
    if (selectedPersonId !== null) loadFanChart(selectedPersonId);
});
fanOpening.addEventListener("input", () => {
    fanOpeningValue.textContent = `${fanOpening.value}°`;
    if (selectedPersonId !== null) loadFanChart(selectedPersonId);
});
openFanViewButton.addEventListener("click", () => {
    if (selectedPersonId === null) return;
    const query = new URLSearchParams({
        person_id: selectedPersonId, generations: fanGenerations.value,
        opening_angle: fanOpening.value, show_unknown: String(fanShowUnknown.checked),
        color_mode: fanColorMode.value, show_sosa: String(fanLabelSosa.checked),
        show_name: String(fanLabelName.checked), show_birth: String(fanLabelBirth.checked),
        show_birth_place: String(fanLabelBirthPlace.checked),
        show_death: String(fanLabelDeath.checked), show_death_place: String(fanLabelDeathPlace.checked),
    });
    window.open(appUrl(`/fan-view?${query.toString()}`), "_blank", "noopener");
});

for (const control of [treeAncestorGenerations, treeDescendantGenerations]) {
    control.addEventListener("change", () => {
        if (selectedPersonId !== null) loadTreeChart(selectedPersonId);
    });
}
treeShowGenerationScale.addEventListener("change", () => {
    if (currentTree === null) return;
    const rootBefore = rootCenterInTreeStage({
        stage: treeStage,
        treeSvg: treeChart,
        tree: currentTree,
    });
    renderEmbeddedGenerationScale();
    updateEmbeddedTreeStage();
    preserveTreeRootPosition({
        viewport: treeContainer,
        stage: treeStage,
        treeSvg: treeChart,
        tree: currentTree,
        before: rootBefore,
    });
});
openTreeViewButton.addEventListener("click", () => {
    if (selectedPersonId === null) return;
    const query = new URLSearchParams({
        person_id: selectedPersonId,
        ancestor_generations: treeAncestorGenerations.value,
        descendant_generations: treeDescendantGenerations.value,
        show_generation_scale: String(treeShowGenerationScale.checked),
    });
    window.open(appUrl(`/tree-view?${query.toString()}`), "_blank", "noopener");
});

function clearPersonSelection() {
    selectionRequestSerial += 1;
    selectedPersonId = null;
    selectedPerson.textContent = "Aucune personne sélectionnée.";
    fanRequestSerial += 1;
    fanChart.innerHTML = "";
    fanStatus.textContent = "Sélectionnez une personne pour afficher l’éventail.";
    clearFanLegend(fanLegend, fanLegendList);
    fanRenderButton.disabled = true;
    openFanViewButton.disabled = true;
    clearTreeChart("Sélectionnez une personne pour afficher l’arbre.");
    openTreeViewButton.disabled = true;
}


function selectPerson(person) {
    selectionRequestSerial += 1;
    selectedPersonId = person.id;
    fanRenderButton.disabled = false;
    openFanViewButton.disabled = false;
    fanChart.innerHTML = "";
    fanStatus.textContent = "";
    clearTreeChart("Chargement de l’arbre familial…");
    openTreeViewButton.disabled = false;

    const birth = person.birth_date
        ? " — naissance : " + person.birth_date
        : "";

    selectedPerson.textContent =
        "Souche : " + person.given_names + " " + person.surname + birth;

    loadFanChart(person.id);
    loadTreeChart(person.id);
}


async function selectDefaultPerson() {
    const requestSerial = ++selectionRequestSerial;

    try {
        const response = await fetch(
            appUrl("/people/" + encodeURIComponent(DEFAULT_PERSON_ID)),
        );

        if (requestSerial !== selectionRequestSerial) {
            return false;
        }

        if (response.status === 404) {
            return false;
        }

        const person = await response.json();

        if (requestSerial !== selectionRequestSerial) {
            return false;
        }

        if (!response.ok) {
            throw new Error(
                person.detail || "Impossible de sélectionner la souche par défaut",
            );
        }

        selectPerson(person);
        return true;
    } catch (error) {
        if (requestSerial === selectionRequestSerial) {
            console.error(error);
        }
        return false;
    }
}


async function initializePage() {
    await loadGedcomStatus();
    await refreshPlacesWorkspace();
    await selectDefaultPerson();
}


async function refreshPlacesWorkspace() {
    if (placesWorkspaceInitialization === null) {
        placesWorkspaceInitialization = import("./places/place_workspace.js")
            .then(({createPlacesWorkspace}) => {
                placesWorkspace = createPlacesWorkspace({appUrl});
                return placesWorkspace;
            })
            .catch(error => {
                console.error("Impossible de charger la gestion des lieux", error);
                return null;
            });
    }
    const workspace = await placesWorkspaceInitialization;
    if (workspace !== null) await workspace.refresh();
}


function renderSearchResults(people) {
    searchResults.innerHTML = "";

    if (people.length === 0) {
        searchResults.textContent = "Aucun résultat.";
        return;
    }

    const list = document.createElement("ul");
    list.className = "people-list";

    for (const person of people) {
        const item = document.createElement("li");
        const button = document.createElement("button");

        button.type = "button";
        button.className = "person-button";
        const birth = person.birth_date
            ? ` — naissance : ${person.birth_date}`
            : " — naissance inconnue";

        button.textContent =
            `${person.given_names} ${person.surname}${birth}`;

        button.addEventListener("click", () => {
            selectPerson(person);
        });

        item.appendChild(button);
        list.appendChild(item);
    }

    searchResults.appendChild(list);
}


async function loadGedcomStatus() {
    try {
        const response = await fetch(appUrl("/health"));
        const health = await response.json();

        if (!response.ok) {
            throw new Error(health.detail || "Impossible de charger l’état du GEDCOM");
        }

        if (health.source !== null && health.filename !== null) {
            gedcomStatus.textContent =
                "GEDCOM : " + health.filename + " · " +
                health.persons_count + " personnes" +
                (health.source === "AUTO" ? " · chargé automatiquement" : "");
            return;
        }

        gedcomStatus.textContent = health.load_error
            ? "GEDCOM : aucun fichier actif · " + health.load_error
            : "GEDCOM : aucun fichier actif";
    } catch (error) {
        gedcomStatus.textContent = error.message;
    }
}


function renderImportDetails(report) {
    warningsList.innerHTML = "";
    ignoredTagsList.innerHTML = "";

    warningsSection.hidden = true;
    ignoredTagsSection.hidden = true;

    if (report.warnings.length > 0) {
        for (const warning of report.warnings) {
            const item = document.createElement("li");
            item.textContent = warning;
            warningsList.appendChild(item);
        }

        warningsSection.hidden = false;
    }

    if (report.ignored_tags.length > 0) {
        for (const ignored of report.ignored_tags) {
            const item = document.createElement("li");

            item.textContent = ignored.record_id
                ? `${ignored.tag} — ${ignored.record_id}`
                : ignored.tag;

            ignoredTagsList.appendChild(item);
        }

        ignoredTagsSection.hidden = false;
    }

    importDetails.hidden =
        report.warnings.length === 0 &&
        report.ignored_tags.length === 0;
}

function clearTreeChart(statusMessage) {
    treeRequestSerial += 1;
    treeChart.innerHTML = "";
    currentTree = null;
    treeStage.style.width = "";
    treeStage.style.height = "";
    treeGenerationScale.innerHTML = "";
    treeGenerationScale.hidden = true;
    treeChart.setAttribute("viewBox", "0 0 1 1");
    treeStatus.textContent = statusMessage;
    treeDiagnostics.hidden = true;
    treeDiagnostics.textContent = "";
}
async function loadTreeChart(personId) {
    const requestSerial = ++treeRequestSerial;
    const ancestors = Number(treeAncestorGenerations.value);
    const descendants = Number(treeDescendantGenerations.value);

    treeStatus.textContent = "Calcul de l’arbre familial…";
    treeDiagnostics.hidden = true;
    treeDiagnostics.textContent = "";

    try {
        const response = await fetch(
            appUrl(`/people/${encodeURIComponent(personId)}` +
            `/tree?ancestor_generations=${encodeURIComponent(ancestors)}` +
            `&descendant_generations=${encodeURIComponent(descendants)}` +
            "&show_siblings=false"),
        );
        const tree = await response.json();

        if (requestSerial !== treeRequestSerial) {
            return;
        }

        if (!response.ok) {
            throw new Error(
                tree.detail || "Impossible de calculer l’arbre familial",
            );
        }

        renderTree(treeChart, tree, {naturalSize: true});
        currentTree = tree;
        finalizeEmbeddedStructuralTreeRender();
        treeStatus.textContent =
            `${tree.person_occurrences.length} occurrences`;

        if (tree.diagnostics.length > 0) {
            treeDiagnostics.textContent =
                `${tree.diagnostics.length} diagnostic${
                    tree.diagnostics.length > 1 ? "s" : ""
                } dans les données`;
            treeDiagnostics.hidden = false;
        }
    } catch (error) {
        if (requestSerial === treeRequestSerial) {
            treeStatus.textContent = error.message;
        }
    }
}

function updateEmbeddedTreeStage() {
    if (currentTree === null) return;
    const scaleWidth = treeShowGenerationScale.checked ? generationScaleWidth : 0;
    treeStage.style.width = `${currentTree.layout.width + scaleWidth}px`;
    treeStage.style.height = `${currentTree.layout.height}px`;
}

function finalizeEmbeddedStructuralTreeRender() {
    if (currentTree === null) return;
    treeChart.style.width = `${currentTree.layout.width}px`;
    treeChart.style.height = `${currentTree.layout.height}px`;
    updateEmbeddedTreeStage();
    renderEmbeddedGenerationScale();
    resetTreeViewportToRoot({
        viewport: treeContainer,
        stage: treeStage,
        treeSvg: treeChart,
        tree: currentTree,
    });
}


function renderEmbeddedGenerationScale() {
    if (currentTree === null || !treeShowGenerationScale.checked) {
        treeGenerationScale.hidden = true;
        treeGenerationScale.innerHTML = "";
        return;
    }
    treeGenerationScale.hidden = false;
    renderGenerationScale(treeGenerationScale, currentTree, {naturalSize: true});
}
async function loadFanChart(personId) {
    const generations = Number(fanGenerations.value);
    const requestSerial = ++fanRequestSerial;

    fanStatus.textContent = "Calcul de l'éventail…";
    clearFanLegend(fanLegend, fanLegendList);

    try {
        const response = await fetch(
            appUrl(`/people/${encodeURIComponent(personId)}` +
            `/sosa?generations=${encodeURIComponent(generations)}` +
            `&color_mode=${encodeURIComponent(fanColorMode.value)}`)
        );

        const occurrences = await response.json();

        if (requestSerial !== fanRequestSerial) {
            return;
        }

        if (!response.ok) {
            throw new Error(
                occurrences.detail ||
                "Impossible de calculer l'éventail"
            );
        }

        renderFanChart(fanChart, occurrences, {
            generations,
            showUnknown: fanShowUnknown.checked,
            openingAngle: Number(fanOpening.value),
            labelConfig: getFanLabelConfig(),
        });
        renderFanLegend(
            fanLegend,
            fanLegendList,
            occurrences,
            fanShowUnknown.checked,
            fanColorMode.value,
        );

        fanStatus.textContent =
            `${occurrences.length} positions Sosa`;

    } catch (error) {
        if (requestSerial === fanRequestSerial) {
            fanStatus.textContent = error.message;
        }
    }
}



function getFanLabelConfig() {
    return {
        showSosa: fanLabelSosa.checked,
        showName: fanLabelName.checked,
        showBirth: fanLabelBirth.checked,
        showBirthPlace: fanLabelBirthPlace.checked,
        showDeath: fanLabelDeath.checked,
        showDeathPlace: fanLabelDeathPlace.checked,
    };
}

void initializePage();

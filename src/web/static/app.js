const importForm = document.querySelector("#import-form");
const fileInput = document.querySelector("#gedcom-file");
const importStatus = document.querySelector("#import-status");
const importReport = document.querySelector("#import-report");
const gedcomStatus = document.querySelector("#gedcom-status");

const placesStatus = document.querySelector("#places-status");
const placesTable = document.querySelector("#places-table");
const placesList = document.querySelector("#places-list");
const placeEnrichmentForm = document.querySelector(
    "#place-enrichment-form",
);
const placeEnrichmentOriginalName = document.querySelector(
    "#place-enrichment-original-name",
);
const placeEnrichmentStatus = document.querySelector(
    "#place-enrichment-status",
);
const placeEnrichmentValidate = document.querySelector(
    "#place-enrichment-validate",
);
const placeEnrichmentNormalizedName = document.querySelector(
    "#place-enrichment-normalized-name",
);
const placeEnrichmentLatitude = document.querySelector(
    "#place-enrichment-latitude",
);
const placeEnrichmentLongitude = document.querySelector(
    "#place-enrichment-longitude",
);
const placeEnrichmentComment = document.querySelector(
    "#place-enrichment-comment",
);
const placeGeocodingQuery = document.querySelector(
    "#place-geocoding-query",
);
const placeGeocodingSearch = document.querySelector(
    "#place-geocoding-search",
);
const placeGeocodingResults = document.querySelector(
    "#place-geocoding-results",
);
const placeGeocodingAttribution = document.querySelector(
    "#place-geocoding-attribution",
);

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
let selectedPlace = null;


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
        const response = await fetch("/imports", {
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
        selectedPlace = null;
        placeEnrichmentForm.hidden = true;
        await loadPlaces();

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
            `/people?q=${encodeURIComponent(query)}`
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


placeEnrichmentForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (selectedPlace === null) {
        return;
    }

    const latitude = optionalCoordinate(placeEnrichmentLatitude);
    const longitude = optionalCoordinate(placeEnrichmentLongitude);

    if (latitude === undefined || longitude === undefined) {
        placesStatus.textContent = "Coordonnée invalide.";
        return;
    }

    try {
        const response = await fetch("/place-enrichments", {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                original_name: selectedPlace.original_name,
                normalized_name: emptyToNull(
                    placeEnrichmentNormalizedName.value,
                ),
                latitude,
                longitude,
                comment: emptyToNull(placeEnrichmentComment.value),
            }),
        });
        const enrichment = await response.json();

        if (!response.ok) {
            throw new Error(
                enrichment.detail ||
                "Impossible d’enregistrer l’enrichissement",
            );
        }

        const places = await loadPlaces();
        const updatedPlace = places.find(
            place => place.original_name === selectedPlace.original_name,
        );

        if (updatedPlace) {
            selectPlace(updatedPlace);
        }

        placesStatus.textContent = "Enrichissement enregistré.";

    } catch (error) {
        placesStatus.textContent = error.message;
    }
});


placeGeocodingSearch.addEventListener("click", async () => {
    if (selectedPlace === null) {
        return;
    }

    const query = emptyToNull(placeGeocodingQuery.value) ||
        selectedPlace.original_name;

    placeGeocodingResults.hidden = false;
    placeGeocodingResults.textContent = "Recherche de candidats…";
    placeGeocodingAttribution.hidden = true;

    try {
        const response = await fetch("/geocoding/candidates", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                original_name: selectedPlace.original_name,
                query,
            }),
        });
        const candidates = await response.json();

        if (!response.ok) {
            throw new Error(
                candidates.detail || "Recherche de géocodage impossible",
            );
        }

        renderGeocodingCandidates(candidates);

    } catch (error) {
        placeGeocodingResults.textContent = error.message;
    }
});


placeEnrichmentValidate.addEventListener("click", async () => {
    if (selectedPlace === null) {
        return;
    }

    try {
        const response = await fetch("/place-enrichments/validate", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                original_name: selectedPlace.original_name,
            }),
        });
        const enrichment = await response.json();

        if (!response.ok) {
            throw new Error(
                enrichment.detail || "Impossible de valider ce lieu",
            );
        }

        const places = await loadPlaces();
        const updatedPlace = places.find(
            place => place.original_name === selectedPlace.original_name,
        );

        if (updatedPlace) {
            selectPlace(updatedPlace);
        }

        placesStatus.textContent = "Lieu validé.";

    } catch (error) {
        placesStatus.textContent = error.message;
    }
});

fanRenderButton.addEventListener("click", () => {
    if (selectedPersonId !== null) {
        loadFanChart(selectedPersonId);
    }
});

fanGenerations.addEventListener("change", () => {
    if (selectedPersonId !== null) {
        loadFanChart(selectedPersonId);
    }
});

fanShowUnknown.addEventListener("change", () => {
    if (selectedPersonId !== null) {
        loadFanChart(selectedPersonId);
    }
});

fanColorMode.addEventListener("change", () => {
    if (selectedPersonId !== null) {
        loadFanChart(selectedPersonId);
    }
});

for (const control of [
    treeAncestorGenerations,
    treeDescendantGenerations,
]) {
    control.addEventListener("change", () => {
        if (selectedPersonId !== null) {
            loadTreeChart(selectedPersonId);
        }
    });
}

openTreeViewButton.addEventListener("click", () => {
    if (selectedPersonId === null) {
        return;
    }
    const query = new URLSearchParams({
        person_id: selectedPersonId,
        ancestor_generations: treeAncestorGenerations.value,
        descendant_generations: treeDescendantGenerations.value,
    });
    window.open(`/tree-view?${query.toString()}`, "_blank", "noopener");
});

fanOpening.addEventListener("input", () => {
    fanOpeningValue.textContent =
        `${fanOpening.value}°`;

    if (selectedPersonId !== null) {
        loadFanChart(selectedPersonId);
    }
});

function clearPersonSelection() {
    selectionRequestSerial += 1;
    selectedPersonId = null;
    selectedPerson.textContent = "Aucune personne sélectionnée.";
    fanRequestSerial += 1;
    fanChart.innerHTML = "";
    fanStatus.textContent = "Sélectionnez une personne pour afficher l’éventail.";
    clearFanLegend();
    fanRenderButton.disabled = true;
    clearTreeChart("Sélectionnez une personne pour afficher l’arbre.");
    openTreeViewButton.disabled = true;
}


function selectPerson(person) {
    selectionRequestSerial += 1;
    selectedPersonId = person.id;
    fanRenderButton.disabled = false;
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
            "/people/" + encodeURIComponent(DEFAULT_PERSON_ID),
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
    await loadPlaces();
    await selectDefaultPerson();
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
        const response = await fetch("/health");
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


async function loadPlaces() {
    placesStatus.textContent = "Chargement des lieux…";
    placesTable.hidden = true;
    placesList.innerHTML = "";

    try {
        const response = await fetch("/places");
        const places = await response.json();

        if (!response.ok) {
            throw new Error(
                places.detail ||
                "Impossible de charger les lieux"
            );
        }

        if (places.length === 0) {
            placesStatus.textContent =
                "Aucun lieu associé à un événement.";
            return [];
        }

        for (const place of places) {
            const row = document.createElement("tr");
            row.className = "place-row";
            row.tabIndex = 0;
            row.addEventListener("click", () => selectPlace(place));
            row.addEventListener("keydown", event => {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    selectPlace(place);
                }
            });

            const cells = [
                place.original_name,
                place.occurrences_count,
                place.persons_count,
                formatPlaceEventCounts(place.event_counts),
                placeStatusLabel(place.enrichment),
            ];

            for (const [index, value] of cells.entries()) {
                const cell = document.createElement("td");

                if (index === cells.length - 1) {
                    const status = document.createElement("span");
                    status.className = placeStatusClass(place.enrichment);
                    status.textContent = value;
                    cell.appendChild(status);
                } else {
                    cell.textContent = value;
                }

                row.appendChild(cell);
            }

            placesList.appendChild(row);
        }

        placesTable.hidden = false;
        placesStatus.textContent =
            `${places.length} lieux utilisés dans les événements.`;

        return places;

    } catch (error) {
        placesStatus.textContent = error.message;
        return [];
    }
}


function selectPlace(place) {
    selectedPlace = place;

    const enrichment = place.enrichment;

    placeEnrichmentOriginalName.value = place.original_name;
    placeEnrichmentStatus.textContent = placeStatusLabel(enrichment);
    placeEnrichmentStatus.className = placeStatusClass(enrichment);
    placeEnrichmentValidate.hidden = !(
        enrichment?.status === "MANUAL" &&
        enrichment.latitude !== null &&
        enrichment.longitude !== null
    );
    placeEnrichmentNormalizedName.value =
        enrichment?.normalized_name || "";
    placeEnrichmentLatitude.value = enrichment?.latitude ?? "";
    placeEnrichmentLongitude.value = enrichment?.longitude ?? "";
    placeEnrichmentComment.value = enrichment?.comment || "";
    placeGeocodingQuery.value = place.original_name;
    placeGeocodingResults.innerHTML = "";
    placeGeocodingResults.hidden = true;
    placeGeocodingAttribution.hidden = true;
    placeEnrichmentForm.hidden = false;
}


function placeStatusLabel(enrichment) {
    return enrichment ? enrichment.status : "Aucun enrichissement";
}


function placeStatusClass(enrichment) {
    if (enrichment?.status === "VALIDATED") {
        return "place-status place-status-validated";
    }

    if (enrichment?.status === "MANUAL") {
        return "place-status place-status-manual";
    }

    return "place-status place-status-unenriched";
}


function renderGeocodingCandidates(candidates) {
    placeGeocodingResults.innerHTML = "";
    placeGeocodingResults.hidden = false;

    if (candidates.length === 0) {
        placeGeocodingResults.textContent = "Aucun candidat trouvé.";
        return;
    }

    const list = document.createElement("ul");
    list.className = "geocoding-candidates";

    for (const candidate of candidates) {
        const item = document.createElement("li");
        const details = document.createElement("div");
        const administration = [
            candidate.city,
            candidate.postcode,
            candidate.region,
            candidate.country,
        ].filter(Boolean).join(", ");

        details.textContent = `${candidate.display_name} — ` +
            `${candidate.latitude}, ${candidate.longitude}` +
            (administration ? ` (${administration})` : "");

        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "Choisir ce candidat";
        button.addEventListener("click", () => {
            selectGeocodingCandidate(candidate.selection_token);
        });

        item.appendChild(details);
        item.appendChild(button);
        list.appendChild(item);
    }

    placeGeocodingResults.appendChild(list);
    placeGeocodingAttribution.hidden = false;
}


async function selectGeocodingCandidate(candidateToken) {
    if (selectedPlace === null) {
        return;
    }

    try {
        const response = await fetch(
            "/place-enrichments/geoapify-selection",
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    original_name: selectedPlace.original_name,
                    candidate_token: candidateToken,
                }),
            },
        );
        const enrichment = await response.json();

        if (!response.ok) {
            throw new Error(
                enrichment.detail || "Impossible de choisir ce candidat",
            );
        }

        const places = await loadPlaces();
        const updatedPlace = places.find(
            place => place.original_name === selectedPlace.original_name,
        );

        if (updatedPlace) {
            selectPlace(updatedPlace);
        }

        placesStatus.textContent = "Candidat Geoapify enregistré.";

    } catch (error) {
        placesStatus.textContent = error.message;
    }
}


function optionalCoordinate(input) {
    if (input.value.trim() === "") {
        return null;
    }

    const value = Number(input.value);

    return Number.isFinite(value) ? value : undefined;
}


function emptyToNull(value) {
    const trimmed = value.trim();

    return trimmed === "" ? null : trimmed;
}

function formatPlaceEventCounts(eventCounts) {
    return Object.entries(eventCounts)
        .map(([type, count]) => `${type}: ${count}`)
        .join(", ");
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
            `/people/${encodeURIComponent(personId)}` +
            `/tree?ancestor_generations=${encodeURIComponent(ancestors)}` +
            `&descendant_generations=${encodeURIComponent(descendants)}` +
            "&show_siblings=false",
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

        renderTree(treeChart, tree);
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




async function loadFanChart(personId) {
    const requestSerial = ++fanRequestSerial;
    const generations = Number(fanGenerations.value);

    fanStatus.textContent = "Calcul de l'éventail…";
    clearFanLegend();

    try {
        const response = await fetch(
            `/people/${encodeURIComponent(personId)}` +
            `/sosa?generations=${encodeURIComponent(generations)}` +
            `&color_mode=${encodeURIComponent(fanColorMode.value)}`
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

        renderFanChart(
            occurrences,
            generations,
            fanShowUnknown.checked,
        );
        renderFanLegend(
            occurrences,
            fanShowUnknown.checked,
        );

        fanStatus.textContent =
            `${occurrences.length} positions Sosa`;

    } catch (error) {
        if (requestSerial === fanRequestSerial) {
            fanStatus.textContent = error.message;
        }
    }
}


function renderFanChart(
    occurrences,
    generations,
    showUnknown,
) {
    fanChart.innerHTML = "";

    const openingAngle = Number(fanOpening.value);

    const geometry = createFanGeometry(
        generations,
        openingAngle,
    );

    const labelConfig =
        getFanLabelConfig();

    setFanViewBox(geometry);

    for (const occurrence of occurrences) {
        if (
            occurrence.person === null &&
            !showUnknown
        ) {
            continue;
        }

        const sector = getSectorGeometry(
            occurrence,
            geometry,
        );

        addFanSector(
            occurrence,
            sector,
        );

        if (occurrence.person !== null) {
            addFanLabel(
                occurrence,
                sector,
                geometry,
                labelConfig,
            );
        }
    }
}


function clearFanLegend() {
    fanLegendList.innerHTML = "";
    fanLegend.hidden = true;
}


function renderFanLegend(occurrences, showUnknown) {
    clearFanLegend();

    if (fanColorMode.value !== "BIRTH_PLACE") {
        return;
    }

    const entries = new Map();

    for (const occurrence of occurrences) {
        if (occurrence.person === null && !showUnknown) {
            continue;
        }

        const entry = legendEntryForOccurrence(occurrence);
        if (entry === null) {
            continue;
        }

        const existing = entries.get(entry.key);
        if (existing !== undefined) {
            existing.occurrencesCount += 1;
        } else {
            entries.set(entry.key, entry);
        }
    }

    const orderedEntries = [...entries.values()].sort(compareLegendEntries);

    for (const entry of orderedEntries) {
        const item = document.createElement("li");
        item.className = "fan-legend-entry";

        const swatch = document.createElement("span");
        swatch.className = "fan-legend-swatch";
        swatch.style.backgroundColor = entry.colorCss;
        swatch.setAttribute("aria-hidden", "true");

        const label = document.createElement("span");
        label.className = "fan-legend-label";
        label.textContent = entry.label;

        const status = document.createElement("span");
        status.className = "fan-legend-status";
        status.textContent = entry.statusLabel || "";

        const count = document.createElement("span");
        count.className = "fan-legend-count";
        count.textContent = entry.occurrencesCount;

        item.append(swatch, label, status, count);
        fanLegendList.appendChild(item);
    }

    fanLegend.hidden = orderedEntries.length === 0;
}


function legendEntryForOccurrence(occurrence) {
    if (
        occurrence.color_kind === "GEOGRAPHIC" ||
        occurrence.color_kind === "UNVERIFIED_PLACE"
    ) {
        if (
            occurrence.birth_place_original_name === null ||
            occurrence.birth_place_display_name === null
        ) {
            return null;
        }

        const isGeographic = occurrence.color_kind === "GEOGRAPHIC";

        return {
            key: `${occurrence.color_kind}:${occurrence.birth_place_original_name}`,
            kind: occurrence.color_kind,
            label: occurrence.birth_place_display_name,
            statusLabel: isGeographic ? null : "Non vérifié",
            colorCss: occurrence.color_css,
            occurrencesCount: 1,
        };
    }

    if (occurrence.color_kind === "UNKNOWN_BIRTH") {
        return {
            key: "UNKNOWN_BIRTH",
            kind: "UNKNOWN_BIRTH",
            label: "Naissance inconnue",
            statusLabel: null,
            colorCss: occurrence.color_css,
            occurrencesCount: 1,
        };
    }

    return null;
}

function compareLegendEntries(first, second) {
    const rank = {
        GEOGRAPHIC: 0,
        UNVERIFIED_PLACE: 1,
        UNKNOWN_BIRTH: 2,
    };
    const rankDifference = rank[first.kind] - rank[second.kind];

    if (rankDifference !== 0) {
        return rankDifference;
    }

    if (first.kind === "UNKNOWN_BIRTH") {
        return 0;
    }

    if (first.occurrencesCount !== second.occurrencesCount) {
        return second.occurrencesCount - first.occurrencesCount;
    }

    return first.label.localeCompare(second.label, "fr");
}


function createFanGeometry(
    generations,
    openingAngle,
) {
    const centerRadius = 52;

    /*
     * Slightly larger inner generations make names easier to read.
     * Outer generations remain compact enough for 8–10 generations.
     */
    const ringWidths = [];

    for (
        let generation = 1;
        generation <= generations;
        generation += 1
    ) {
        let width;

        if (generation <= 2) {
            width = 92;
        } else if (generation <= 4) {
            width = 82;
        } else if (generation <= 6) {
            width = 74;
        } else {
            width = 68;
        }

        ringWidths.push(width);
    }

    const radii = [0, centerRadius];

    let radius = centerRadius;

    for (const width of ringWidths) {
        radius += width;
        radii.push(radius);
    }

    /*
     * The fan is centred on the upper half-plane:
     *
     * 180° -> from -180° to 0°
     * 240° -> from -210° to 30°
     * 360° -> complete circle
     */
    const startAngle =
        -90 - openingAngle / 2;

    const endAngle =
        -90 + openingAngle / 2;

    return {
        generations,
        openingAngle,
        startAngle,
        endAngle,
        radii,
        outerRadius: radii[radii.length - 1],
    };
}


function getSectorGeometry(
    occurrence,
    geometry,
) {
    const generation = occurrence.generation;

    if (generation === 0) {
        return {
            innerRadius: 0,
            outerRadius: geometry.radii[1],
            startAngle: geometry.startAngle,
            endAngle: geometry.endAngle,
        };
    }

    const firstSosa = 2 ** generation;
    const position =
        occurrence.sosa - firstSosa;

    const count = 2 ** generation;

    const sectorAngle =
        geometry.openingAngle / count;

    const startAngle =
        geometry.startAngle +
        position * sectorAngle;

    const endAngle =
        startAngle + sectorAngle;

    return {
        innerRadius:
            geometry.radii[generation],
        outerRadius:
            geometry.radii[generation + 1],
        startAngle,
        endAngle,
    };
}


function addFanSector(
    occurrence,
    sector,
) {
    const svgNS =
        "http://www.w3.org/2000/svg";

    const path =
        document.createElementNS(
            svgNS,
            "path",
        );

    path.setAttribute(
        "d",
        annularSectorPath(
            sector.innerRadius,
            sector.outerRadius,
            sector.startAngle,
            sector.endAngle,
        ),
    );

    path.setAttribute(
        "class",
        occurrence.person
            ? "fan-sector known"
            : "fan-sector unknown",
    );

    path.dataset.sosa = occurrence.sosa;

    if (occurrence.color_css !== null) {
        path.style.fill = occurrence.color_css;
    }

    fanChart.appendChild(path);
}


function annularSectorPath(
    innerRadius,
    outerRadius,
    startAngle,
    endAngle,
) {
    const angleSize =
        endAngle - startAngle;

    const largeArc =
        angleSize > 180 ? 1 : 0;

    if (innerRadius === 0) {
        /*
         * Sosa 1 is represented as a circular sector.
         */
        if (angleSize >= 359.999) {
            return circlePath(outerRadius);
        }

        const start =
            polar(outerRadius, startAngle);

        const end =
            polar(outerRadius, endAngle);

        return [
            "M 0 0",
            `L ${start.x} ${start.y}`,
            `A ${outerRadius} ${outerRadius}`,
            `0 ${largeArc} 1`,
            `${end.x} ${end.y}`,
            "Z",
        ].join(" ");
    }

    if (angleSize >= 359.999) {
        return annulusPath(
            innerRadius,
            outerRadius,
        );
    }

    const outerStart =
        polar(outerRadius, startAngle);

    const outerEnd =
        polar(outerRadius, endAngle);

    const innerEnd =
        polar(innerRadius, endAngle);

    const innerStart =
        polar(innerRadius, startAngle);

    return [
        `M ${outerStart.x} ${outerStart.y}`,
        `A ${outerRadius} ${outerRadius}`,
        `0 ${largeArc} 1`,
        `${outerEnd.x} ${outerEnd.y}`,
        `L ${innerEnd.x} ${innerEnd.y}`,
        `A ${innerRadius} ${innerRadius}`,
        `0 ${largeArc} 0`,
        `${innerStart.x} ${innerStart.y}`,
        "Z",
    ].join(" ");
}


function circlePath(radius) {
    return [
        `M ${-radius} 0`,
        `A ${radius} ${radius} 0 1 0`,
        `${radius} 0`,
        `A ${radius} ${radius} 0 1 0`,
        `${-radius} 0`,
        "Z",
    ].join(" ");
}


function annulusPath(
    innerRadius,
    outerRadius,
) {
    return [
        `M ${-outerRadius} 0`,
        `A ${outerRadius} ${outerRadius} 0 1 0`,
        `${outerRadius} 0`,
        `A ${outerRadius} ${outerRadius} 0 1 0`,
        `${-outerRadius} 0`,
        "Z",
        `M ${-innerRadius} 0`,
        `A ${innerRadius} ${innerRadius} 0 1 1`,
        `${innerRadius} 0`,
        `A ${innerRadius} ${innerRadius} 0 1 1`,
        `${-innerRadius} 0`,
        "Z",
    ].join(" ");
}


function polar(
    radius,
    angleDegrees,
) {
    const angle =
        angleDegrees * Math.PI / 180;

    return {
        x: radius * Math.cos(angle),
        y: radius * Math.sin(angle),
    };
}


function addFanLabel(
    occurrence,
    sector,
    geometry,
    labelConfig,
) {
    const svgNS =
        "http://www.w3.org/2000/svg";

    const generation =
        occurrence.generation;

    const angle =
        (
            sector.startAngle +
            sector.endAngle
        ) / 2;

    const radius =
        sector.innerRadius === 0
            ? sector.outerRadius * 0.55
            : (
                sector.innerRadius +
                sector.outerRadius
            ) / 2;

    const point =
        polar(radius, angle);

    const group =
        document.createElementNS(
            svgNS,
            "g",
        );

    group.setAttribute(
        "class",
        "fan-label",
    );

    group.setAttribute(
        "transform",
        labelTransform(
            point,
            angle,
            generation,
        ),
    );

    const availableWidth =
        getLabelAvailableWidth(
            sector,
            generation,
        );

    const availableHeight =
        getLabelAvailableHeight(
            sector,
            generation,
        );

    const labelVariants =
        buildPersonLabelVariants(
            occurrence,
            generation,
            labelConfig,
        );

    if (labelVariants.length === 0) {
        return;
    }

    const text =
        document.createElementNS(
            svgNS,
            "text",
        );

    text.setAttribute(
        "class",
        "fan-name",
    );

    group.appendChild(text);
    fanChart.appendChild(group);

    fitFanLabel(
        text,
        labelVariants,
        availableWidth,
        availableHeight,
        generation,
    );
}


function labelTransform(
    point,
    angle,
    generation,
) {
    /*
     * Inner generations remain mostly horizontal/tangential.
     * Outer generations become radial.
     */
    if (generation <= 3) {
        return (
            `translate(${point.x} ${point.y})`
        );
    }

    let rotation = angle + 90;

    /*
     * Keep text readable instead of upside-down.
     */
    const normalized =
        ((rotation % 360) + 360) % 360;

    if (
        normalized > 90 &&
        normalized < 270
    ) {
        rotation += 180;
    }

    return (
        `translate(${point.x} ${point.y}) ` +
        `rotate(${rotation})`
    );
}

function buildPersonLabelVariants(
    occurrence,
    generation,
    config,
) {
    const person = occurrence.person;

    const fullSecondary = buildSecondaryLabelLines(
        person,
        config,
        "full",
    );

    const yearSecondary = buildSecondaryLabelLines(
        person,
        config,
        "year",
    );

    const fullPrimary = buildPrimaryLabelLines(
        occurrence,
        person,
        generation,
        config,
    );

    const variants = [];

    /*
     * Prefer every selected datum, then only the year part of dates.
     * Neither step can introduce information disabled by the user.
     */
    addLabelVariant(
        variants,
        [...fullPrimary, ...fullSecondary],
    );

    addLabelVariant(
        variants,
        [...fullPrimary, ...yearSecondary],
    );

    /*
     * From the year-only form, remove optional details one at a time.
     * The primary identity remains; if none was requested, retain the
     * first selected detail rather than rendering an empty label.
     */
    const essentialSecondary =
        fullPrimary.length === 0 &&
        yearSecondary.length > 0
            ? [yearSecondary[0]]
            : [];

    for (
        let count = yearSecondary.length - 1;
        count >= essentialSecondary.length;
        count -= 1
    ) {
        addLabelVariant(
            variants,
            [...fullPrimary, ...yearSecondary.slice(0, count)],
        );
    }

    if (config.showName) {
        const abbreviatedPrimary = buildPrimaryLabelLines(
            occurrence,
            person,
            generation,
            config,
            true,
        );

        addLabelVariant(variants, abbreviatedPrimary);
    }

    return variants;
}


function buildPrimaryLabelLines(
    occurrence,
    person,
    generation,
    config,
    abbreviateName = false,
) {
    const primary = [];

    if (config.showSosa) {
        primary.push(`S${occurrence.sosa}`);
    }

    if (config.showName) {
        const name = abbreviateName
            ? abbreviatePersonName(person)
            : formatPersonName(person);

        if (name) {
            primary.push(name);
        }
    }

    if (generation >= 6 || abbreviateName) {
        return [primary.join(" ")].filter(Boolean);
    }

    return primary;
}


function buildSecondaryLabelLines(
    person,
    config,
    datePrecision,
) {
    const secondary = [];

    if (config.showBirth) {
        const birth = formatEventLabel(
            "°",
            person.birth_date,
            datePrecision,
        );

        if (birth) {
            secondary.push(birth);
        }
    }

    if (config.showBirthPlace && person.birth_place) {
        secondary.push(person.birth_place);
    }

    if (config.showDeath) {
        const death = formatEventLabel(
            "†",
            person.death_date,
            datePrecision,
        );

        if (death) {
            secondary.push(death);
        }
    }

    if (config.showDeathPlace && person.death_place) {
        secondary.push(person.death_place);
    }

    return secondary;
}


function addLabelVariant(variants, lines) {
    if (lines.length === 0) {
        return;
    }

    const key = lines.join("\u0000");

    if (!variants.some(variant => variant.join("\u0000") === key)) {
        variants.push(lines);
    }
}


function formatPersonName(person) {
    return `${person.given_names} ${person.surname}`.trim();
}


function abbreviatePersonName(person) {
    const abbreviatedGivenNames = person.given_names
        .split(/\s+/)
        .filter(Boolean)
        .map(name => `${name[0]}.`)
        .join(" ");

    return [
        abbreviatedGivenNames,
        person.surname,
    ].filter(Boolean).join(" ");
}

function getLabelAvailableWidth(
    sector,
    generation,
) {
    const angleRadians =
        (
            sector.endAngle -
            sector.startAngle
        ) * Math.PI / 180;

    const middleRadius =
        (
            sector.innerRadius +
            sector.outerRadius
        ) / 2;

    const arcLength =
        middleRadius * angleRadians;

    const radialLength =
        sector.outerRadius -
        sector.innerRadius;

    if (generation <= 3) {
        return Math.max(
            20,
            arcLength * 0.82,
        );
    }

    /*
     * Rotated outer labels use the radial dimension.
     */
    return Math.max(
        20,
        radialLength * 0.86,
    );
}


function getLabelAvailableHeight(
    sector,
    generation,
) {
    const radialLength =
        sector.outerRadius -
        sector.innerRadius;

    if (generation <= 3) {
        return radialLength * 0.78;
    }

    const angleRadians =
        (
            sector.endAngle -
            sector.startAngle
        ) * Math.PI / 180;

    const middleRadius =
        (
            sector.innerRadius +
            sector.outerRadius
        ) / 2;

    return Math.max(
        18,
        middleRadius *
        angleRadians *
        0.78,
    );
}


function fitFanLabel(
    text,
    variants,
    maxWidth,
    maxHeight,
    generation,
) {
    const minFontSize = 5.5;

    for (const lines of variants) {
        let fontSize = initialFanFontSize(generation);

        while (fontSize >= minFontSize) {
            populateFanText(text, lines, fontSize);

            const box = text.getBBox();

            if (
                box.width <= maxWidth &&
                box.height <= maxHeight
            ) {
                return;
            }

            fontSize -= 0.5;
        }
    }

    const finalLines = variants[variants.length - 1];

    populateFanText(
        text,
        finalLines,
        minFontSize,
    );

    truncateSvgText(
        text,
        maxWidth,
    );
}

function initialFanFontSize(generation) {
    if (generation === 0) {
        return 13;
    }

    if (generation <= 2) {
        return 12;
    }

    if (generation <= 4) {
        return 10;
    }

    if (generation <= 6) {
        return 8.5;
    }

    return 7.5;
}


function populateFanText(
    text,
    lines,
    fontSize,
) {
    const svgNS =
        "http://www.w3.org/2000/svg";

    text.innerHTML = "";

    text.setAttribute(
        "font-size",
        fontSize,
    );

    const lineHeight =
        fontSize * 1.15;

    const totalHeight =
        (lines.length - 1) *
        lineHeight;

    lines.forEach(
        (line, index) => {
            const tspan =
                document.createElementNS(
                    svgNS,
                    "tspan",
                );

            tspan.setAttribute(
                "x",
                "0",
            );

            if (index === 0) {
                tspan.setAttribute(
                    "dy",
                    -totalHeight / 2,
                );
            } else {
                tspan.setAttribute(
                    "dy",
                    lineHeight,
                );
            }

            tspan.textContent = line;

            text.appendChild(tspan);
        }
    );
}


function truncateSvgText(
    text,
    maxWidth,
) {
    const tspan =
        text.querySelector("tspan");

    if (!tspan) {
        return;
    }

    const original =
        tspan.textContent;

    if (
        tspan.getComputedTextLength()
        <= maxWidth
    ) {
        return;
    }

    let value = original;

    while (value.length > 1) {
        value = value.slice(0, -1);

        tspan.textContent =
            `${value}…`;

        if (
            tspan.getComputedTextLength()
            <= maxWidth
        ) {
            return;
        }
    }

    tspan.textContent = "…";
}

function setFanViewBox(geometry) {
    const radius = geometry.outerRadius;

    const points = [
        {x: 0, y: 0},
    ];

    /*
     * Sampling the angular range makes the viewBox work for every
     * opening from 180° to 360°.
     */
    const samples = 180;

    for (
        let index = 0;
        index <= samples;
        index += 1
    ) {
        const ratio =
            index / samples;

        const angle =
            geometry.startAngle +
            geometry.openingAngle * ratio;

        points.push(
            polar(radius, angle)
        );
    }

    const xs =
        points.map(point => point.x);

    const ys =
        points.map(point => point.y);

    const padding = 30;

    const minX =
        Math.min(...xs) - padding;

    const maxX =
        Math.max(...xs) + padding;

    const minY =
        Math.min(...ys) - padding;

    const maxY =
        Math.max(...ys) + padding;

    fanChart.setAttribute(
        "viewBox",
        [
            minX,
            minY,
            maxX - minX,
            maxY - minY,
        ].join(" "),
    );
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


function formatEventLabel(
    symbol,
    value,
    precision = "full",
) {
    if (!value) {
        return "";
    }

    if (precision === "year") {
        const match = value.match(/\b\d{4}\b/);

        return match ? `${symbol} ${match[0]}` : "";
    }

    return `${symbol} ${value}`;
}

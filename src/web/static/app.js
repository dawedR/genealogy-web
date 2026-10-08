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
const historicalReconciliation = document.querySelector(
    "#historical-reconciliation",
);
const historicalReconciliationSummary = document.querySelector(
    "#historical-reconciliation-summary",
);
const historicalReconciliationList = document.querySelector(
    "#historical-reconciliation-list",
);
const historicalReconciliationShowAll = document.querySelector(
    "#historical-reconciliation-show-all",
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
let selectedPlace = null;
let currentPlacesByOriginalName = new Map();
let historicalReconciliations = [];
let skippedHistoricalProposals = new Set();
let showAllHistoricalProposals = false;


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
        selectedPlace = null;
        placeEnrichmentForm.hidden = true;
        await loadPlaces();
        await loadHistoricalReconciliation({resetSession: true});

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
        const response = await fetch(appUrl("/place-enrichments"), {
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
        const response = await fetch(appUrl("/geocoding/candidates"), {
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
        const response = await fetch(appUrl("/place-enrichments/validate"), {
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
    await loadPlaces();
    await loadHistoricalReconciliation({resetSession: true});
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


async function loadPlaces() {
    placesStatus.textContent = "Chargement des lieux…";
    placesTable.hidden = true;
    placesList.innerHTML = "";

    try {
        const response = await fetch(appUrl("/places"));
        const places = await response.json();

        if (!response.ok) {
            throw new Error(
                places.detail ||
                "Impossible de charger les lieux"
            );
        }

        if (places.length === 0) {
            currentPlacesByOriginalName = new Map();
            placesStatus.textContent =
                "Aucun lieu associé à un événement.";
            return [];
        }

        currentPlacesByOriginalName = new Map(
            places.map(place => [place.original_name, place]),
        );

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


historicalReconciliationShowAll.addEventListener("click", () => {
    showAllHistoricalProposals = true;
    renderHistoricalReconciliation();
});


async function loadHistoricalReconciliation({resetSession = false} = {}) {
    if (resetSession) {
        skippedHistoricalProposals = new Set();
        showAllHistoricalProposals = false;
    }

    try {
        const response = await fetch(
            appUrl("/place-reconciliation/historical"),
        );
        const reconciliations = await response.json();

        if (!response.ok) {
            throw new Error(
                reconciliations.detail ||
                "Impossible de charger les propositions historiques",
            );
        }

        historicalReconciliations = reconciliations;
        renderHistoricalReconciliation();
    } catch (error) {
        historicalReconciliations = [];
        historicalReconciliation.hidden = false;
        historicalReconciliationSummary.textContent = error.message;
        historicalReconciliationList.innerHTML = "";
        historicalReconciliationShowAll.hidden = true;
    }
}


function renderHistoricalReconciliation() {
    const counts = {
        STRONG_MATCH: 0,
        REVIEW: 0,
        AMBIGUOUS: 0,
        NO_MATCH: 0,
    };
    for (const reconciliation of historicalReconciliations) {
        counts[reconciliation.classification] += 1;
    }

    historicalReconciliationSummary.textContent =
        `${counts.STRONG_MATCH} fortes · ${counts.REVIEW} à examiner · ` +
        `${counts.NO_MATCH} sans correspondance` +
        (counts.AMBIGUOUS > 0 ? ` · ${counts.AMBIGUOUS} ambiguës` : "");

    const proposals = historicalReconciliations
        .filter(reconciliation =>
            reconciliation.classification === "STRONG_MATCH" ||
            reconciliation.classification === "REVIEW",
        )
        .flatMap(reconciliation => reconciliation.proposals)
        .filter(proposal =>
            proposal.classification === "STRONG_MATCH" ||
            proposal.classification === "REVIEW",
        )
        .sort((left, right) => {
            if (left.classification !== right.classification) {
                return left.classification === "STRONG_MATCH" ? -1 : 1;
            }
            return right.score - left.score || left.source_original_name.localeCompare(
                right.source_original_name,
            );
        });

    historicalReconciliationList.innerHTML = "";
    historicalReconciliation.hidden = proposals.length === 0;
    if (proposals.length === 0) {
        historicalReconciliationShowAll.hidden = true;
        return;
    }

    const visibleProposals = showAllHistoricalProposals
        ? proposals
        : proposals.filter(proposal => !skippedHistoricalProposals.has(
            historicalProposalKey(proposal),
        ));
    historicalReconciliationShowAll.hidden =
        showAllHistoricalProposals || skippedHistoricalProposals.size === 0;

    if (visibleProposals.length === 0) {
        historicalReconciliationList.textContent =
            "Toutes les propositions ont été passées pour cette session.";
        return;
    }

    for (const proposal of visibleProposals) {
        historicalReconciliationList.appendChild(
            historicalProposalElement(proposal),
        );
    }
}


function historicalProposalElement(proposal) {
    const container = document.createElement("article");
    container.className = "historical-proposal " +
        (proposal.classification === "REVIEW"
            ? "historical-proposal-review"
            : "historical-proposal-strong");

    const sourcePlace = currentPlacesByOriginalName.get(
        proposal.source_original_name,
    );
    const title = document.createElement("strong");
    title.textContent = proposal.source_original_name +
        (sourcePlace ? ` · ${sourcePlace.occurrences_count} occurrence(s)` : "");
    container.appendChild(title);

    const historical = document.createElement("p");
    historical.textContent =
        `Ancien libellé : ${proposal.historical_original_name} ` +
        `(${proposal.historical_status})`;
    container.appendChild(historical);

    if (proposal.historical_normalized_name) {
        const normalized = document.createElement("p");
        normalized.textContent =
            `Nom normalisé : ${proposal.historical_normalized_name}`;
        container.appendChild(normalized);
    }

    const score = document.createElement("p");
    score.textContent =
        `Similarité documentaire : ${proposal.score} · ${proposal.classification}` +
        ` · Réutilisation des coordonnées : ${proposal.coordinate_reuse_reliability}`;
    container.appendChild(score);

    const reasons = document.createElement("p");
    reasons.textContent = `Raisons : ${proposal.reasons.join(" · ")}`;
    container.appendChild(reasons);

    if (proposal.warnings.length > 0) {
        const warnings = document.createElement("p");
        warnings.className = "historical-proposal-warnings";
        warnings.textContent = `À vérifier : ${proposal.warnings.join(" · ")}`;
        container.appendChild(warnings);
    }

    const actions = document.createElement("div");
    actions.className = "historical-proposal-actions";
    const reuse = document.createElement("button");
    reuse.type = "button";
    reuse.textContent = "Réutiliser";
    reuse.addEventListener("click", () => {
        void reuseHistoricalProposal(proposal);
    });
    const skip = document.createElement("button");
    skip.type = "button";
    skip.textContent = "Passer";
    skip.addEventListener("click", () => {
        skippedHistoricalProposals.add(historicalProposalKey(proposal));
        renderHistoricalReconciliation();
    });
    actions.append(reuse, skip);
    container.appendChild(actions);
    return container;
}


async function reuseHistoricalProposal(proposal) {
    try {
        const response = await fetch(
            appUrl("/place-reconciliation/historical/reuse"),
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    source_original_name: proposal.source_original_name,
                    historical_original_name: proposal.historical_original_name,
                }),
            },
        );
        const enrichment = await response.json();
        if (!response.ok) {
            throw new Error(
                enrichment.detail ||
                "Impossible de réutiliser l’enrichissement historique",
            );
        }

        await loadPlaces();
        await loadHistoricalReconciliation();
        placesStatus.textContent = "Enrichissement historique réutilisé.";
    } catch (error) {
        placesStatus.textContent = error.message;
    }
}


function historicalProposalKey(proposal) {
    return `${proposal.source_original_name}\u0000${proposal.historical_original_name}`;
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
            appUrl("/place-enrichments/geoapify-selection"),
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

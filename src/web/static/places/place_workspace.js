import {
    loadPlaceWorkbench, reuseHistoricalProposal, savePlaceEnrichment,
    searchGeocodingCandidates, selectGeoapifyCandidate, validatePlaceEnrichment,
    confirmAdministrativeMatch, submitAdministrativeReview, searchCog,
    selectAdministrativeReference, deleteAdministrativeReference,
} from "./place_api.js";
import {renderPlaceDetail} from "./place_detail.js";
import {createAdministrationUiState} from "./place_administration.js";
import {createGeographyUiState} from "./place_geography.js";
import {historicalProposalKey} from "./historical_reconciliation.js";
import {renderPlaceList, visibleEntries} from "./place_list.js";

export function createPlacesWorkspace({appUrl}) {
    const elements = {
        status: document.querySelector("#places-workbench-status"),
        search: document.querySelector("#places-workbench-search"),
        filter: document.querySelector("#places-workbench-filter"),
        sort: document.querySelector("#places-workbench-sort"),
        list: document.querySelector("#places-workbench-list"),
        detail: document.querySelector("#places-workbench-detail"),
        previous: document.querySelector("#places-workbench-previous"),
        next: document.querySelector("#places-workbench-next"),
    };
    const state = {
        entries: [], selectedOriginalName: null, query: "", filter: "ALL",
        sort: "PRIORITY", requestSerial: 0, operationSerial: 0,
        skippedHistoricalProposals: new Set(), showSkippedHistoricalProposals: false,
        geography: createGeographyUiState(),
        administration: createAdministrationUiState(),
        detail: {advancedOpen: false},
        mapPoint: null,
    };

    function visible() {
        return visibleEntries(state.entries, state);
    }

    function render() {
        const entries = visible();
        ensureVisibleSelection(entries);
        renderPlaceList(elements.list, entries, state.selectedOriginalName, select);
        const selectedEntry = entries.find(
            entry => entry.original_name === state.selectedOriginalName,
        );
        renderPlaceDetail(
            elements.detail, selectedEntry, historicalActions(), geographyActions(),
            administrationActions(), detailActions(selectedEntry),
        );
        const index = entries.findIndex(
            entry => entry.original_name === state.selectedOriginalName,
        );
        elements.previous.disabled = index <= 0;
        elements.next.disabled = index < 0 || index >= entries.length - 1;
        elements.status.textContent = `${entries.length} lieu(x) affiché(s).`;
    }

    function ensureVisibleSelection(entries) {
        let selected = state.selectedOriginalName;
        if (entries.length === 1) {
            selected = entries[0].original_name;
        } else if (!entries.some(entry =>
            entry.original_name === selected,
        )) {
            selected = entries[0]?.original_name || null;
        }
        setSelected(selected);
    }

    function historicalActions() {
        return {
            skipped: state.skippedHistoricalProposals,
            showSkipped: state.showSkippedHistoricalProposals,
            onReuse: proposal => { void reuse(proposal); },
            onSkip: proposal => {
                state.skippedHistoricalProposals.add(historicalProposalKey(proposal));
                render();
            },
            onRestore: proposal => {
                state.skippedHistoricalProposals.delete(historicalProposalKey(proposal));
                render();
            },
            onToggleSkipped: () => {
                state.showSkippedHistoricalProposals =
                    !state.showSkippedHistoricalProposals;
                render();
            },
            onPreview: proposal => {
                state.mapPoint = historicalMapPoint(proposal);
                render();
            },
            onSearchAlternative: () => {
                state.detail.advancedOpen = true;
                state.geography.searchOpen = true;
                render();
            },
        };
    }

    function geographyActions() {
        return {
            state: state.geography,
            onSearch: (originalName, query) => { void search(originalName, query); },
            onSelect: candidateToken => { void selectCandidate(candidateToken); },
            onPreview: candidate => {
                state.mapPoint = candidateMapPoint(candidate);
                render();
            },
            onSave: (payload, validationError) => {
                if (validationError) {
                    state.geography.message = validationError;
                    render();
                } else {
                    void save(payload);
                }
            },
            onValidate: originalName => { void validate(originalName); },
            onEdit: () => {
                state.geography.editOpen = true;
                render();
            },
            onCancelEdit: () => {
                state.geography.editOpen = false;
                state.geography.message = null;
                render();
            },
        };
    }

    function administrationActions() {
        return {
            state: state.administration,
            onConfirm: originalName => {
                void administrativeWrite(
                    () => confirmAdministrativeMatch(appUrl, originalName),
                    "Proposition COG confirmée.",
                );
            },
            onReview: (originalName, note) => {
                void administrativeWrite(
                    () => submitAdministrativeReview(appUrl, originalName, note),
                    "Proposition COG conservée pour revue.",
                );
            },
            onSearch: (originalName, query) => { void administrativeSearch(originalName, query); },
            onSelect: candidate => {
                const originalName = state.selectedOriginalName;
                if (!originalName) return;
                void administrativeWrite(
                    () => selectAdministrativeReference(
                        appUrl, originalName, candidate, state.administration.note.trim() || null,
                    ),
                    "Rattachement COG confirmé manuellement.",
                );
            },
            onDelete: originalName => {
                void administrativeWrite(
                    () => deleteAdministrativeReference(appUrl, originalName),
                    "Rattachement COG retiré.",
                );
            },
        };
    }

    function detailActions(entry) {
        return {
            advancedOpen: state.detail.advancedOpen,
            appUrl,
            mapPoint: selectedMapPoint(entry),
            onAdvancedToggle: open => { state.detail.advancedOpen = open; },
            onOpenTool: target => {
                state.detail.advancedOpen = true;
                if (target === "historical") previewFirstHistoricalProposal();
                if (target === "geography-search") state.geography.searchOpen = true;
                if (target === "geography-edit") state.geography.editOpen = true;
                if (target === "administration") state.administration.open = true;
                render();
            },
        };
    }

    function select(originalName) {
        setSelected(originalName);
        render();
    }

    function setSelected(originalName) {
        if (state.selectedOriginalName === originalName) return;
        state.selectedOriginalName = originalName;
        state.detail.advancedOpen = false;
        state.geography.searchOpen = false;
        state.geography.editOpen = false;
        state.administration.open = false;
        state.mapPoint = null;
    }

    function selectedMapPoint(entry) {
        if (state.mapPoint?.originalName === state.selectedOriginalName) return state.mapPoint;
        const enrichment = entry?.geography.enrichment;
        if (enrichment?.latitude !== null && enrichment?.longitude !== null && enrichment) {
            return {
                originalName: entry.original_name,
                title: "Position enregistrée",
                name: enrichment.normalized_name || entry.original_name,
                latitude: enrichment.latitude,
                longitude: enrichment.longitude,
            };
        }
        const proposal = entry?.historical_reconciliation?.proposals.find(item =>
            item.latitude !== null && item.longitude !== null,
        );
        return proposal ? historicalMapPoint(proposal) : null;
    }

    function previewFirstHistoricalProposal() {
        const entry = visible().find(item => item.original_name === state.selectedOriginalName);
        const proposal = entry?.historical_reconciliation?.proposals.find(item =>
            item.latitude !== null && item.longitude !== null,
        );
        if (proposal) state.mapPoint = historicalMapPoint(proposal);
    }

    function historicalMapPoint(proposal) {
        return {
            originalName: proposal.source_original_name,
            title: `Position proposée pour ${placeName(proposal.source_original_name)}`,
            name: proposal.historical_normalized_name || proposal.historical_original_name,
            latitude: proposal.latitude,
            longitude: proposal.longitude,
        };
    }

    function candidateMapPoint(candidate) {
        return {
            originalName: state.selectedOriginalName,
            title: "Position Geoapify examinée",
            name: candidate.display_name,
            latitude: candidate.latitude,
            longitude: candidate.longitude,
        };
    }

    function placeName(originalName) {
        return originalName.split(",", 1)[0].replace(/^\?\s*/, "").trim();
    }

    function navigate(offset) {
        const entries = visible();
        const index = entries.findIndex(
            entry => entry.original_name === state.selectedOriginalName,
        );
        const target = entries[index + offset];
        if (target) select(target.original_name);
    }

    async function refresh() {
        const serial = ++state.requestSerial;
        elements.status.textContent = "Chargement des lieux…";
        try {
            const entries = await loadPlaceWorkbench(appUrl);
            if (serial !== state.requestSerial) return;
            state.entries = entries;
            render();
        } catch (error) {
            if (serial === state.requestSerial) {
                elements.status.textContent = error.message;
                elements.list.innerHTML = "";
                renderPlaceDetail(elements.detail, null);
            }
        }
    }

    async function reuse(proposal) {
        const serial = ++state.operationSerial;
        elements.status.textContent = "Réutilisation de l’enrichissement historique…";
        try {
            await reuseHistoricalProposal(appUrl, proposal);
            if (serial !== state.operationSerial) return;
            state.mapPoint = null;
            await refresh();
            if (serial === state.operationSerial) {
                elements.status.textContent = "Enrichissement historique réutilisé : à valider.";
            }
        } catch (error) {
            if (serial === state.operationSerial) elements.status.textContent = error.message;
        }
    }

    async function search(originalName, query) {
        const serial = ++state.operationSerial;
        state.geography.message = "Recherche de candidats…";
        state.geography.candidates = null;
        state.geography.query = query;
        state.geography.searchOpen = true;
        render();
        try {
            const candidates = await searchGeocodingCandidates(appUrl, originalName, query);
            if (serial !== state.operationSerial ||
                state.selectedOriginalName !== originalName) return;
            state.geography.candidates = candidates;
            state.geography.message = null;
            render();
        } catch (error) {
            if (serial === state.operationSerial &&
                state.selectedOriginalName === originalName) {
                state.geography.message = error.message;
                render();
            }
        }
    }

    async function selectCandidate(candidateToken) {
        const originalName = state.selectedOriginalName;
        if (!originalName) return;
        await write(
            () => selectGeoapifyCandidate(appUrl, originalName, candidateToken),
            "Candidat Geoapify enregistré : à valider.",
        );
    }

    async function save(payload) {
        if (!payload) return;
        await write(
            () => savePlaceEnrichment(appUrl, payload),
            enrichment => enrichment.status === "MANUAL"
                ? "Modifications enregistrées — position à confirmer."
                : "Modifications enregistrées.",
        );
    }

    async function validate(originalName) {
        await write(
            () => validatePlaceEnrichment(appUrl, originalName),
            "Lieu validé.",
        );
    }

    async function write(action, successMessage) {
        const serial = ++state.operationSerial;
        elements.status.textContent = "Enregistrement…";
        try {
            const result = await action();
            if (serial !== state.operationSerial) return;
            state.mapPoint = null;
            state.geography.candidates = null;
            state.geography.message = null;
            state.geography.editOpen = false;
            await refresh();
            if (serial === state.operationSerial) {
                elements.status.textContent = typeof successMessage === "function"
                    ? successMessage(result)
                    : successMessage;
            }
        } catch (error) {
            if (serial === state.operationSerial) {
                state.geography.message = error.message;
                elements.status.textContent = error.message;
                render();
            }
        }
    }

    async function administrativeSearch(originalName, query) {
        if (!query) {
            state.administration.message = "Saisissez une recherche COG.";
            render();
            return;
        }
        const serial = ++state.operationSerial;
        state.administration.message = "Recherche COG…";
        state.administration.candidates = null;
        state.administration.query = query;
        state.administration.open = true;
        render();
        try {
            const candidates = await searchCog(appUrl, query);
            if (serial !== state.operationSerial ||
                state.selectedOriginalName !== originalName) return;
            state.administration.candidates = candidates;
            state.administration.message = null;
            render();
        } catch (error) {
            if (serial === state.operationSerial &&
                state.selectedOriginalName === originalName) {
                state.administration.message = error.message;
                render();
            }
        }
    }

    async function administrativeWrite(action, successMessage) {
        const serial = ++state.operationSerial;
        elements.status.textContent = "Enregistrement du rattachement COG…";
        try {
            await action();
            if (serial !== state.operationSerial) return;
            state.administration.candidates = null;
            state.administration.message = null;
            await refresh();
            if (serial === state.operationSerial) elements.status.textContent = successMessage;
        } catch (error) {
            if (serial === state.operationSerial) {
                state.administration.message = error.message;
                elements.status.textContent = error.message;
                render();
            }
        }
    }

    elements.search.addEventListener("input", () => {
        state.query = elements.search.value;
        render();
    });
    elements.filter.addEventListener("change", () => {
        state.filter = elements.filter.value;
        render();
    });
    elements.sort.addEventListener("change", () => {
        state.sort = elements.sort.value;
        render();
    });
    elements.previous.addEventListener("click", () => navigate(-1));
    elements.next.addEventListener("click", () => navigate(1));

    return {refresh};
}

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
    };

    function visible() {
        return visibleEntries(state.entries, state);
    }

    function render() {
        const entries = visible();
        ensureVisibleSelection(entries);
        renderPlaceList(elements.list, entries, state.selectedOriginalName, select);
        renderPlaceDetail(elements.detail, entries.find(
            entry => entry.original_name === state.selectedOriginalName,
        ), historicalActions(), geographyActions(), administrationActions());
        const index = entries.findIndex(
            entry => entry.original_name === state.selectedOriginalName,
        );
        elements.previous.disabled = index <= 0;
        elements.next.disabled = index < 0 || index >= entries.length - 1;
        elements.status.textContent = `${entries.length} lieu(x) affiché(s).`;
    }

    function ensureVisibleSelection(entries) {
        if (entries.length === 1) {
            state.selectedOriginalName = entries[0].original_name;
        } else if (!entries.some(entry =>
            entry.original_name === state.selectedOriginalName,
        )) {
            state.selectedOriginalName = entries[0]?.original_name || null;
        }
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
        };
    }

    function geographyActions() {
        return {
            state: state.geography,
            onSearch: (originalName, query) => { void search(originalName, query); },
            onSelect: candidateToken => { void selectCandidate(candidateToken); },
            onSave: (payload, validationError) => {
                if (validationError) {
                    state.geography.message = validationError;
                    render();
                } else {
                    void save(payload);
                }
            },
            onValidate: originalName => { void validate(originalName); },
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

    function select(originalName) {
        state.selectedOriginalName = originalName;
        render();
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
            "Enrichissement enregistré.",
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
            await action();
            if (serial !== state.operationSerial) return;
            state.geography.candidates = null;
            state.geography.message = null;
            await refresh();
            if (serial === state.operationSerial) {
                elements.status.textContent = successMessage;
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

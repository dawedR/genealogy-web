export async function loadPlaceWorkbench(appUrl) {
    const response = await fetch(appUrl("/places/workbench"));
    const entries = await response.json();
    if (!response.ok) {
        throw new Error(entries.detail || "Impossible de charger les lieux.");
    }
    return entries;
}

export async function reuseHistoricalProposal(appUrl, proposal) {
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
            "Impossible de réutiliser l’enrichissement historique.",
        );
    }
    return enrichment;
}

export async function searchGeocodingCandidates(appUrl, originalName, query) {
    return requestJson(appUrl("/geocoding/candidates"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({original_name: originalName, query}),
    }, "Recherche de géocodage impossible.");
}

export async function selectGeoapifyCandidate(appUrl, originalName, candidateToken) {
    return requestJson(appUrl("/place-enrichments/geoapify-selection"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            original_name: originalName,
            candidate_token: candidateToken,
        }),
    }, "Impossible de choisir ce candidat.");
}

export async function savePlaceEnrichment(appUrl, payload) {
    return requestJson(appUrl("/place-enrichments"), {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
    }, "Impossible d’enregistrer l’enrichissement.");
}

export async function validatePlaceEnrichment(appUrl, originalName) {
    return requestJson(appUrl("/place-enrichments/validate"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({original_name: originalName}),
    }, "Impossible de valider ce lieu.");
}

export async function confirmAdministrativeMatch(appUrl, originalName) {
    return requestJson(appUrl("/places/administrative-references/confirm-match"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({original_name: originalName}),
    }, "Impossible de confirmer la proposition COG.");
}

export async function submitAdministrativeReview(appUrl, originalName, humanNote) {
    return requestJson(appUrl("/places/administrative-references/submit-review"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({original_name: originalName, human_note: humanNote}),
    }, "Impossible de conserver la proposition COG pour revue.");
}

export async function searchCog(appUrl, query) {
    return requestJson(
        appUrl(`/cog/search?query=${encodeURIComponent(query)}`),
        {},
        "Recherche COG impossible.",
    );
}

export async function selectAdministrativeReference(appUrl, originalName, candidate, humanNote) {
    return requestJson(appUrl("/places/administrative-references/manual-selection"), {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            original_name: originalName,
            cog_code: candidate.code,
            cog_type: candidate.type,
            human_note: humanNote,
        }),
    }, "Impossible de sélectionner cette référence COG.");
}

export async function deleteAdministrativeReference(appUrl, originalName) {
    const response = await fetch(appUrl("/places/administrative-references"), {
        method: "DELETE",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({original_name: originalName}),
    });
    if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "Impossible de retirer le rattachement COG.");
    }
}

async function requestJson(url, options, fallbackMessage) {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || fallbackMessage);
    return payload;
}

const labels = {
    UNENRICHED: "Géographie manquante",
    UNRESOLVED: "Géographie non résolue",
    AUTOMATIC: "Géographie automatique",
    AMBIGUOUS: "Géographie ambiguë",
    MANUAL: "Géographie à valider",
    VALIDATED: "Géographie validée",
    MATCHED: "COG à confirmer",
    REVIEW: "COG à examiner",
    AMBIGUOUS_COG: "COG ambigu",
    NO_MATCH: "COG sans correspondance",
    NOT_APPLICABLE: "COG non applicable",
    STRONG_MATCH: "Proposition historique forte",
    NO_MATCH_HISTORY: "Aucune proposition historique",
    ADMINISTRATIVE_REFERENCE: "Présentation calculée",
    GEDCOM_FALLBACK: "Présentation GEDCOM",
};

const warnings = {
    NO_CONFIRMED_ADMINISTRATIVE_REFERENCE: "Référence administrative à confirmer",
    NO_STRUCTURED_GEOGRAPHIC_REFERENCE: "Aucune référence géographique structurée fiable",
    ADMINISTRATIVE_REFERENCE_NOT_CONFIRMED: "Référence administrative non confirmée",
    ADMINISTRATIVE_REFERENCE_OBSOLETE: "Référence administrative à revoir",
};

const historicalReasons = {
    NORMALIZED_FULL_LABEL_MATCH: "Libellés complets rapprochés",
    LOCALITY_MATCH: "Localité identique",
    COUNTRY_MATCH: "Pays identique",
    CODE_MATCH: "Code commun",
    DISTRICT_NUMBER_MATCHES_CODE_SUFFIX: "Numéro de district cohérent avec le code",
    ADMINISTRATIVE_COMPONENTS_MATCH: "Composants administratifs concordants",
    HISTORICAL_ENRICHMENT_VALIDATED: "Ancien enrichissement validé",
    HISTORICAL_COORDINATES_AVAILABLE: "Coordonnées historiques disponibles",
};

const historicalWarnings = {
    LEADING_UNCERTAINTY_MARKER: "Le libellé GEDCOM commence par un marqueur d’incertitude",
    LOCALITY_ONLY_MATCH: "La correspondance repose seulement sur la localité",
    CODE_MISMATCH: "Les codes présents diffèrent",
    ADMINISTRATIVE_VARIANT: "Les composants administratifs diffèrent",
    HISTORICAL_ENRICHMENT_NOT_VALIDATED: "L’ancien enrichissement n’est pas validé",
    HISTORICAL_COORDINATES_MISSING: "Les coordonnées historiques sont absentes",
    COMPETING_HISTORICAL_MATCHES: "Plusieurs anciennes correspondances sont concurrentes",
    SECONDARY_TOPONYMS_DIFFER: "Des toponymes secondaires diffèrent",
    SECONDARY_TOPONYMS_NOT_DOCUMENTED: "Des toponymes secondaires ne sont pas documentés des deux côtés",
    NORMALIZED_SECONDARY_TOPONYMS_DIFFER: "Le nom normalisé mentionne des toponymes secondaires différents",
};

const cogReasons = {
    SOURCE_COUNTRY_FRANCE: "Le pays France est indiqué dans le libellé",
    CURRENT_CODE_NAME_MATCH: "Le code et le nom correspondent à la commune actuelle",
    HISTORICAL_CODE_NAME_MATCH: "Le code et le nom correspondent à une commune historique",
    MUNICIPAL_ARRONDISSEMENT_MATCH: "Arrondissement municipal identifié",
    EMBEDDED_COMMUNE_MATCH: "Commune identifiée dans un libellé plus précis",
};

const cogWarnings = {
    HISTORICAL_DETAIL_PRESERVED: "La précision historique du libellé est conservée",
    LEADING_UNCERTAINTY_MARKER: "Le libellé GEDCOM commence par un marqueur d’incertitude",
    CODE_DOES_NOT_MATCH_SOURCE_NAME: "Le code et le nom source ne correspondent pas",
    CODE_NOT_IN_COG: "Le code n’existe pas dans le COG 2026",
    POSTCODE_NOT_INFERRED: "Le nombre à cinq chiffres n’est pas assimilé à un code INSEE",
};

export function geographyLabel(entry) {
    return labels[entry.geography.state] || entry.geography.state;
}

export function administrationLabel(entry) {
    if (!entry.administration.applicable) return labels.NOT_APPLICABLE;
    if (entry.administration.reference?.status === "CONFIRMED" &&
        entry.administration.reference_is_current) {
        return "COG confirmé";
    }
    if (entry.administration.reference?.status === "REVIEW") return "COG à revoir";
    if (entry.administration.diagnostic_classification === "AMBIGUOUS") {
        return labels.AMBIGUOUS_COG;
    }
    return labels[entry.administration.diagnostic_classification] ||
        entry.administration.diagnostic_classification;
}

export function historicalLabel(entry) {
    const reconciliation = entry.historical_reconciliation;
    if (!reconciliation || reconciliation.proposals.length === 0) {
        return labels.NO_MATCH_HISTORY;
    }
    if (reconciliation.classification === "STRONG_MATCH") {
        return labels.STRONG_MATCH;
    }
    return "Proposition historique à examiner";
}

export function historicalProposalLabel(classification) {
    if (classification === "STRONG_MATCH") return "Correspondance forte";
    if (classification === "REVIEW") return "À examiner";
    if (classification === "AMBIGUOUS") return "Ambiguë";
    return "Sans correspondance";
}

export function reconciliationWarningLabel() {
    return "Des éléments de cette proposition demandent une vérification.";
}

export function historicalReliabilityLabel(reliability) {
    if (reliability === "HIGH_CONFIDENCE") return "Fiabilité élevée";
    if (reliability === "REVIEW") return "À vérifier";
    return "Non disponible";
}

export function historicalReasonLabel(reason) {
    return historicalReasons[reason] || "Élément de rapprochement à vérifier";
}

export function historicalWarningLabel(warning) {
    return historicalWarnings[warning] || "Élément de fiabilité à vérifier";
}

export function presentationLabel(entry) {
    return labels[entry.presentation.generated_from] ||
        entry.presentation.generated_from;
}

export function warningLabel(warning) {
    return warnings[warning] || "Information à vérifier";
}

export function cogReasonLabel(reason) {
    return cogReasons[reason] || "Élément de diagnostic COG à vérifier";
}

export function cogWarningLabel(warning) {
    return cogWarnings[warning] || "Avertissement COG à vérifier";
}

export function cogLocationLabel(reference) {
    const identity = [
        reference.commune,
        reference.type && reference.code && `code INSEE ${reference.code} (${reference.type})`,
    ].filter(Boolean).join(" — ");
    const administration = [reference.department, reference.region]
        .filter(Boolean).join(" · ");
    const historical = reference.historical_name
        ? ` · Nom historique : ${reference.historical_name}` +
            (reference.valid_from || reference.valid_to
                ? ` (${reference.valid_from || "?"} – ${reference.valid_to || "?"})`
                : "")
        : "";
    return identity + (administration ? ` — ${administration}` : "") + historical;
}

export function eventCountsLabel(eventCounts) {
    return Object.entries(eventCounts)
        .map(([type, count]) => `${type} : ${count}`)
        .join(" · ");
}

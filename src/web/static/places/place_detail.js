import {
    administrationLabel,
    cogLocationLabel,
    cogReasonLabel,
    cogWarningLabel,
    eventCountsLabel,
    geographyLabel,
    historicalLabel,
    presentationLabel,
    warningLabel,
} from "./place_formatters.js";
import {renderHistoricalProposals} from "./historical_reconciliation.js";
import {renderGeographyEditor} from "./place_geography.js";
import {renderAdministrationEditor} from "./place_administration.js";

export function renderPlaceDetail(
    container, entry, historicalActions = null, geographyActions = null,
    administrationActions = null,
) {
    container.innerHTML = "";
    if (!entry) {
        container.textContent = "Sélectionnez un lieu.";
        return;
    }
    container.append(
        section("Identité GEDCOM", [
            field("Libellé original", entry.original_name),
            field("Occurrences", String(entry.occurrences_count)),
            field("Personnes", String(entry.persons_count)),
            field("Événements", eventCountsLabel(entry.event_counts)),
        ]),
        geographySection(entry, historicalActions, geographyActions),
        administrationSection(entry, administrationActions),
        presentationSection(entry),
    );
}

function geographySection(entry, historicalActions, geographyActions) {
    const enrichment = entry.geography.enrichment;
    const fields = [field("État", geographyLabel(entry))];
    if (enrichment) {
        fields.push(
            field("Coordonnées", coordinates(enrichment)),
            field("Provenance", enrichment.source || "Saisie locale"),
        );
    }
    const reconciliation = entry.historical_reconciliation;
    fields.push(field("Historique", historicalLabel(entry)));
    if (reconciliation?.proposals.length && historicalActions) {
        const proposals = renderHistoricalProposals({entry, ...historicalActions});
        fields.push(fieldNode("Propositions", proposals));
    }
    if (geographyActions) {
        fields.push(fieldNode(
            "Actions géographiques",
            renderGeographyEditor({entry, ...geographyActions}),
        ));
    }
    return section("Géographie", fields);
}

function administrationSection(entry, administrationActions) {
    if (!entry.administration.applicable) {
        return section("Administration", [field("COG", "Non applicable à ce lieu")]);
    }
    const fields = [field("État", administrationLabel(entry))];
    const reference = entry.administration.reference;
    if (reference) {
        fields.push(field(
            "Référence confirmée",
            cogLocationLabel({...reference, type: reference.cog_type, code: reference.cog_code}),
        ));
        if (!entry.administration.reference_is_current) {
            fields.push(field(
                "Avertissement",
                "Référence à revoir : elle ne correspond plus au référentiel COG actif.",
            ));
        }
    } else if (entry.administration.diagnostic?.candidate) {
        const candidate = entry.administration.diagnostic.candidate;
        fields.push(field(
            "Proposition COG",
            cogLocationLabel(candidate),
        ));
    }
    const diagnostic = entry.administration.diagnostic;
    if (diagnostic?.reasons.length) {
        fields.push(field("Raisons", diagnostic.reasons.map(cogReasonLabel).join(" · ")));
    }
    if (diagnostic?.warnings.length) {
        fields.push(field("Avertissements", diagnostic.warnings.map(cogWarningLabel).join(" · ")));
    }
    if (administrationActions) {
        fields.push(fieldNode(
            "Actions administratives",
            renderAdministrationEditor({entry, ...administrationActions}),
        ));
    }
    return section("Administration", fields);
}

function presentationSection(entry) {
    const fields = [
        field("Libellé complet", entry.presentation.full_label),
        field("Libellé court", entry.presentation.short_label),
        field("Origine", presentationLabel(entry)),
    ];
    if (entry.presentation.warnings.length) {
        fields.push(field(
            "Avertissements",
            entry.presentation.warnings.map(warningLabel).join(" · "),
        ));
    }
    return section("Présentation", fields);
}

function section(title, fields) {
    const element = document.createElement("section");
    element.className = "places-workbench-detail-section";
    const heading = document.createElement("h3");
    heading.textContent = title;
    const list = document.createElement("dl");
    for (const item of fields) list.appendChild(item);
    element.append(heading, list);
    return element;
}

function field(label, value) {
    const text = document.createElement("span");
    text.textContent = value;
    return fieldNode(label, text);
}

function fieldNode(label, value) {
    const wrapper = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = label;
    const definition = document.createElement("dd");
    definition.appendChild(value);
    wrapper.append(term, definition);
    return wrapper;
}

function coordinates(enrichment) {
    return enrichment.latitude === null || enrichment.longitude === null
        ? "Non renseignées"
        : `${enrichment.latitude}, ${enrichment.longitude}`;
}

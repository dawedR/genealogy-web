import {
    cogLocationLabel,
    coordinatesLabel,
    eventCountsLabel,
    geographyLabel,
    locationSourceLabel,
    placeProgress,
    presentationOriginLabel,
    warningLabel,
} from "./place_formatters.js";
import {renderHistoricalProposals} from "./historical_reconciliation.js";
import {renderGeographyEditor} from "./place_geography.js";
import {renderAdministrationEditor} from "./place_administration.js";
import {renderPlaceMap} from "./place_map.js";

export function renderPlaceDetail(
    container, entry, historicalActions = null, geographyActions = null,
    administrationActions = null, detailActions = null,
) {
    container.innerHTML = "";
    if (!entry) {
        container.textContent = "Sélectionnez un lieu.";
        return;
    }
    const progress = placeProgress(entry);
    container.append(
        progressSection(progress, detailActions),
        originSection(entry),
        locationSection(entry, detailActions),
        presentationSection(entry),
        advancedSection(
            entry, historicalActions, geographyActions, administrationActions, detailActions,
        ),
    );
}

function progressSection(progress, detailActions) {
    const element = document.createElement("section");
    element.className = "places-workbench-progress";
    const heading = document.createElement("h3");
    heading.textContent = "Avancement";
    const status = document.createElement("p");
    status.className = progress.treated
        ? "places-workbench-progress-treated"
        : "places-workbench-progress-pending";
    status.textContent = progress.label;
    const detail = document.createElement("p");
    detail.textContent = progress.detail;
    element.append(heading, status, detail);
    if (progress.actions.length) {
        const actions = document.createElement("div");
        actions.className = "places-workbench-primary-actions";
        for (const action of progress.actions) {
            actions.appendChild(button(
                action.label, () => detailActions?.onOpenTool(action.target),
            ));
        }
        element.appendChild(actions);
    }
    return element;
}

function originSection(entry) {
    return section("Lieu d’origine", [
        field("Libellé GEDCOM", entry.original_name),
        field("Utilisation", `${entry.occurrences_count} occurrence(s) · ` +
            `${entry.persons_count} personne(s)`),
        field("Événements", eventCountsLabel(entry.event_counts)),
    ]);
}

function locationSection(entry, detailActions) {
    const enrichment = entry.geography.enrichment;
    const fields = [field("État", entry.geography.state === "VALIDATED"
        ? "Localisation validée"
        : geographyLabel(entry))];
    if (enrichment) {
        fields.push(
            field("Coordonnées", coordinatesLabel(enrichment.latitude, enrichment.longitude)),
            field("Provenance", locationSourceLabel(enrichment)),
        );
        if (enrichment.coordinates_overridden) {
            fields.push(field("Information", "Coordonnées ajustées manuellement."));
        }
    } else {
        fields.push(field("Coordonnées", "Aucune localisation enregistrée."));
    }
    const element = section("Localisation", fields);
    const point = detailActions?.mapPoint;
    if (point) element.appendChild(renderPlaceMap({appUrl: detailActions.appUrl, point}));
    return element;
}

function presentationSection(entry) {
    const fields = [
        field("Libellé complet", entry.presentation.full_label),
        field("Libellé court", entry.presentation.short_label),
        field("Origine", presentationOriginLabel(entry)),
    ];
    const reference = entry.administration.reference;
    if (entry.administration.applicable && reference?.status === "CONFIRMED" &&
        entry.administration.reference_is_current) {
        fields.push(field("Rattachement administratif", cogLocationLabel({
            ...reference, type: reference.cog_type, code: reference.cog_code,
        })));
    }
    return section("Nom affiché dans la généalogie", fields);
}

function advancedSection(entry, historicalActions, geographyActions, administrationActions, detailActions) {
    const details = document.createElement("details");
    details.className = "places-workbench-advanced";
    details.open = Boolean(detailActions?.advancedOpen);
    details.addEventListener("toggle", () => {
        if (detailActions) detailActions.onAdvancedToggle(details.open);
    });
    const summary = document.createElement("summary");
    summary.textContent = "Détails et outils avancés";
    const content = document.createElement("div");
    content.className = "places-workbench-advanced-content";
    const reconciliation = entry.historical_reconciliation;
    if (reconciliation?.proposals.length && historicalActions) {
        content.appendChild(toolSection("Ancienne localisation", renderHistoricalProposals({
            entry, ...historicalActions,
        })));
    }
    if (geographyActions) {
        content.appendChild(toolSection("Outils de localisation", renderGeographyEditor({
            entry, ...geographyActions,
        })));
    }
    if (entry.administration.applicable && administrationActions) {
        content.appendChild(toolSection("Rattachement administratif", renderAdministrationEditor({
            entry, ...administrationActions,
        })));
    }
    const displayWarnings = entry.presentation.warnings.filter(warning => !(
        entry.geography.state === "VALIDATED" &&
        warning === "NO_STRUCTURED_GEOGRAPHIC_REFERENCE"
    ));
    if (displayWarnings.length) {
        content.appendChild(toolSection("Informations à vérifier", text(
            displayWarnings.map(warningLabel).join(" · "),
        )));
    }
    details.append(summary, content);
    return details;
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
    return fieldNode(label, text(value));
}

function text(value) {
    const element = document.createElement("span");
    element.textContent = value;
    return element;
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

function toolSection(title, content) {
    const section = document.createElement("section");
    section.className = "places-workbench-tool-section";
    const heading = document.createElement("h4");
    heading.textContent = title;
    section.append(heading, content);
    return section;
}

function button(label, handler) {
    const element = document.createElement("button");
    element.type = "button";
    element.textContent = label;
    element.addEventListener("click", handler);
    return element;
}

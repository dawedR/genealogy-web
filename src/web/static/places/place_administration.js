import {cogLocationLabel, cogReasonLabel, cogWarningLabel} from "./place_formatters.js";

export function createAdministrationUiState() {
    return {
        originalName: null, query: "", note: "", candidates: null, message: null,
        open: false,
    };
}

export function renderAdministrationEditor({
    entry, state, onConfirm, onReview, onSearch, onSelect, onDelete,
}) {
    if (!entry.administration.applicable) return null;
    if (state.originalName !== entry.original_name) {
        state.originalName = entry.original_name;
        state.query = defaultQuery(entry);
        state.note = entry.administration.reference?.human_note || "";
        state.candidates = null;
        state.message = null;
        state.open = false;
    }
    const details = document.createElement("details");
    details.className = "places-workbench-administration-editor";
    details.open = state.open;
    const summary = document.createElement("summary");
    summary.textContent = "Gérer le rattachement administratif COG";
    details.appendChild(summary);
    const content = document.createElement("div");
    content.className = "places-workbench-administration-content";
    if (state.message) content.appendChild(message(state.message));
    content.appendChild(diagnostic(entry));
    const reference = entry.administration.reference;
    if (reference) {
        content.append(referenceDetails(reference, entry.administration.reference_is_current),
            manualSearch(entry, state, onSearch, onSelect),
            button("Retirer le rattachement", () => onDelete(entry.original_name)));
    } else if (entry.administration.diagnostic_classification === "MATCHED") {
        content.appendChild(button(
            "Confirmer cette proposition COG",
            () => onConfirm(entry.original_name),
        ));
    } else if (entry.administration.diagnostic_classification === "REVIEW") {
        const note = noteField(state);
        content.append(note.label, button(
            "Conserver pour revue",
            () => onReview(entry.original_name, note.input.value.trim() || null),
        ), manualSearch(entry, state, onSearch, onSelect));
    } else {
        content.appendChild(manualSearch(entry, state, onSearch, onSelect));
    }
    details.appendChild(content);
    return details;
}

function diagnostic(entry) {
    const diagnostic = entry.administration.diagnostic;
    const section = document.createElement("section");
    section.className = "places-workbench-administration-diagnostic";
    const title = document.createElement("strong");
    title.textContent = "Diagnostic automatique";
    section.appendChild(title);
    if (diagnostic?.candidate) {
        if (entry.administration.diagnostic_classification === "REVIEW" &&
            diagnostic.source_code) {
            section.appendChild(paragraph(
                "Conflit à examiner",
                `Le code ${diagnostic.source_code} correspond à ` +
                `${diagnostic.candidate.commune} dans le COG 2026, et non à ` +
                `${sourceLocality(entry.original_name)}. Sélection manuelle nécessaire.`,
            ));
        } else {
            section.appendChild(paragraph(
                "Proposition", cogLocationLabel(diagnostic.candidate),
            ));
        }
    }
    if (diagnostic?.reasons.length) section.appendChild(paragraph(
        "Raisons", diagnostic.reasons.map(cogReasonLabel).join(" · "),
    ));
    if (diagnostic?.warnings.length) {
        const warning = paragraph(
            "Avertissements", diagnostic.warnings.map(cogWarningLabel).join(" · "),
        );
        warning.classList.add("places-workbench-administration-warnings");
        section.appendChild(warning);
    }
    return section;
}

function referenceDetails(reference, isCurrent) {
    const section = document.createElement("section");
    section.className = "places-workbench-administration-reference";
    section.appendChild(paragraph(
        "Décision humaine", `${reference.status} — ${cogLocationLabel({
            ...reference, type: reference.cog_type, code: reference.cog_code,
        })}`,
    ));
    if (reference.human_note) section.appendChild(paragraph("Note", reference.human_note));
    if (!isCurrent) {
        const stale = paragraph(
            "À revoir", "Cette référence ne correspond plus au référentiel COG actif.",
        );
        stale.classList.add("places-workbench-administration-warnings");
        section.appendChild(stale);
    }
    return section;
}

function manualSearch(entry, state, onSearch, onSelect) {
    const section = document.createElement("section");
    section.className = "places-workbench-administration-search";
    const label = document.createElement("label");
    label.textContent = "Rechercher une référence COG";
    const input = document.createElement("input");
    input.type = "search";
    input.value = state.query;
    input.autocomplete = "off";
    input.addEventListener("input", () => { state.query = input.value; });
    label.appendChild(input);
    section.append(label, button("Rechercher dans le COG", () => {
        onSearch(entry.original_name, input.value.trim());
    }));
    if (state.candidates !== null) section.appendChild(searchResults(state.candidates, onSelect));
    return section;
}

function searchResults(candidates, onSelect) {
    const container = document.createElement("div");
    container.className = "places-workbench-cog-results";
    if (candidates.length === 0) {
        container.textContent = "Aucune référence COG trouvée.";
        return container;
    }
    const list = document.createElement("ul");
    for (const candidate of candidates) {
        const item = document.createElement("li");
        item.append(
            document.createTextNode(cogLocationLabel(candidate)),
            button("Choisir cette référence", () => onSelect(candidate)),
        );
        list.appendChild(item);
    }
    container.appendChild(list);
    return container;
}

function noteField(state) {
    const label = document.createElement("label");
    label.textContent = "Note de revue facultative";
    const input = document.createElement("textarea");
    input.value = state.note;
    input.addEventListener("input", () => { state.note = input.value; });
    label.appendChild(input);
    return {label, input};
}

function defaultQuery(entry) {
    return entry.administration.reference?.commune ||
        entry.administration.diagnostic?.candidate?.commune ||
        entry.original_name.split(",", 1)[0];
}

function sourceLocality(originalName) {
    return originalName.split(",", 1)[0].replace(/^\?\s*/, "").trim();
}

function paragraph(label, value) {
    const element = document.createElement("p");
    const strong = document.createElement("strong");
    strong.textContent = `${label} : `;
    element.append(strong, document.createTextNode(value));
    return element;
}

function message(value) {
    const element = document.createElement("p");
    element.className = "places-workbench-administration-message";
    element.textContent = value;
    return element;
}

function button(label, handler) {
    const element = document.createElement("button");
    element.type = "button";
    element.textContent = label;
    element.addEventListener("click", handler);
    return element;
}

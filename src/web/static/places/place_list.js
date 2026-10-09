import {
    administrationLabel,
    geographyLabel,
    historicalLabel,
    presentationLabel,
} from "./place_formatters.js";

export function visibleEntries(entries, {query, filter, sort}) {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    const filtered = entries.filter(entry =>
        (!normalizedQuery || entry.original_name.toLocaleLowerCase().includes(normalizedQuery)) &&
        matchesFilter(entry, filter),
    );
    return [...filtered].sort(comparator(sort));
}

export function renderPlaceList(container, entries, selectedOriginalName, onSelect) {
    container.innerHTML = "";
    if (entries.length === 0) {
        container.textContent = "Aucun lieu ne correspond aux critères.";
        return;
    }
    for (const entry of entries) {
        const item = document.createElement("li");
        const button = document.createElement("button");
        button.type = "button";
        button.className = "places-workbench-entry";
        button.setAttribute("aria-pressed", String(entry.original_name === selectedOriginalName));
        if (entry.original_name === selectedOriginalName) {
            button.classList.add("is-selected");
        }
        const title = document.createElement("strong");
        title.textContent = entry.original_name;
        const occurrence = document.createElement("span");
        occurrence.textContent = `${entry.occurrences_count} occurrence(s)`;
        const states = document.createElement("span");
        states.className = "places-workbench-entry-states";
        states.textContent = [
            geographyLabel(entry), administrationLabel(entry),
            historicalLabel(entry), presentationLabel(entry),
        ].join(" · ");
        button.append(title, occurrence, states);
        button.addEventListener("click", () => onSelect(entry.original_name));
        item.appendChild(button);
        container.appendChild(item);
    }
}

function matchesFilter(entry, filter) {
    const completed = entry.geography.state === "VALIDATED" &&
        (!entry.administration.applicable ||
            (entry.administration.reference?.status === "CONFIRMED" &&
                entry.administration.reference_is_current)) &&
        entry.presentation.warnings.length === 0;
    const toVerify = entry.geography.state === "MANUAL" ||
        ["REVIEW", "AMBIGUOUS"].includes(
            entry.administration.diagnostic_classification,
        ) ||
        ["REVIEW", "AMBIGUOUS"].includes(
            entry.historical_reconciliation?.classification,
        ) || entry.presentation.warnings.length > 0;
    switch (filter) {
    case "TO_PROCESS": return !completed;
    case "TO_VERIFY": return toVerify;
    case "COMPLETED": return completed;
    case "GEOGRAPHY_MISSING":
        return entry.geography.enrichment === null ||
            entry.geography.enrichment.latitude === null ||
            entry.geography.enrichment.longitude === null;
    case "COG_TO_CONFIRM":
        return entry.administration.applicable &&
            !entry.administration.reference_is_current &&
            ["MATCHED", "REVIEW"].includes(
                entry.administration.diagnostic_classification,
            );
    default: return true;
    }
}

function comparator(sort) {
    if (sort === "OCCURRENCES") {
        return (left, right) => right.occurrences_count - left.occurrences_count ||
            alphabetical(left, right);
    }
    if (sort === "ALPHABETICAL") return alphabetical;
    return (left, right) => priority(left) - priority(right) ||
        right.occurrences_count - left.occurrences_count || alphabetical(left, right);
}

function priority(entry) {
    if (["STRONG_MATCH", "REVIEW"].includes(
        entry.historical_reconciliation?.classification,
    )) return 0;
    if (entry.administration.applicable && !entry.administration.reference_is_current &&
        ["MATCHED", "REVIEW"].includes(entry.administration.diagnostic_classification)) return 1;
    if (entry.geography.enrichment === null) return 2;
    if (entry.geography.state === "MANUAL") return 3;
    return 4;
}

function alphabetical(left, right) {
    return left.original_name.localeCompare(right.original_name, "fr");
}

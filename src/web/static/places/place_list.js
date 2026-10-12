import {
    hasActionablePresentationWarning,
    hasConfirmedCurrentAdministration,
    placeProgress,
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
        states.textContent = placeProgress(entry).label;
        button.append(title, occurrence, states);
        button.addEventListener("click", () => onSelect(entry.original_name));
        item.appendChild(button);
        container.appendChild(item);
    }
}

function matchesFilter(entry, filter) {
    const completed = placeProgress(entry).treated;
    const toVerify = entry.geography.state === "MANUAL" ||
        ["REVIEW", "AMBIGUOUS"].includes(
            entry.administration.diagnostic_classification,
        ) ||
        ["REVIEW", "AMBIGUOUS"].includes(
            entry.historical_reconciliation?.classification,
        ) || hasActionablePresentationWarning(entry);
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
            !hasConfirmedCurrentAdministration(entry) &&
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
    const target = placeProgress(entry).actions[0]?.target;
    return {
        historical: 0,
        "geography-search": 1,
        "geography-edit": 2,
        administration: 3,
    }[target] ?? 4;
}

function alphabetical(left, right) {
    return left.original_name.localeCompare(right.original_name, "fr");
}

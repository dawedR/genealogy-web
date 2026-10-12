export function createGeographyUiState() {
    return {
        originalName: null, query: "", candidates: null, message: null,
        searchOpen: false, editOpen: false,
    };
}

export function renderGeographyEditor({
    entry, state, onSearch, onSelect, onPreview, onSave, onValidate, onEdit, onCancelEdit,
}) {
    if (state.originalName !== entry.original_name) {
        state.originalName = entry.original_name;
        state.query = entry.original_name;
        state.candidates = null;
        state.message = null;
        state.searchOpen = false;
        state.editOpen = false;
    }
    const container = document.createElement("div");
    container.className = "places-workbench-geography-editor";
    const enrichment = entry.geography.enrichment;
    if (state.message) {
        const message = document.createElement("p");
        message.className = "places-workbench-geography-message";
        message.textContent = state.message;
        container.appendChild(message);
    }
    container.append(
        searchSection(entry, state, onSearch, onSelect, onPreview),
        editSection(entry, enrichment, state, onSave, onValidate, onEdit, onCancelEdit),
    );
    return container;
}

function searchSection(entry, state, onSearch, onSelect, onPreview) {
    const details = document.createElement("details");
    details.className = "places-workbench-geography-subsection";
    details.open = state.searchOpen;
    const summary = document.createElement("summary");
    summary.textContent = "Rechercher avec Geoapify";
    details.appendChild(summary);
    const content = document.createElement("div");
    content.className = "places-workbench-geography-content";
    const label = document.createElement("label");
    label.textContent = "Requête Geoapify";
    const input = document.createElement("input");
    input.type = "search";
    input.value = state.query;
    input.autocomplete = "off";
    input.addEventListener("input", () => { state.query = input.value; });
    label.appendChild(input);
    const search = button("Rechercher des candidats", () => {
        onSearch(entry.original_name, input.value.trim() || entry.original_name);
    });
    content.append(label, search);
    if (state.candidates !== null) {
        content.appendChild(candidateResults(state.candidates, onSelect, onPreview));
    }
    details.appendChild(content);
    return details;
}

function candidateResults(candidates, onSelect, onPreview) {
    const container = document.createElement("div");
    container.className = "places-workbench-geocoding-candidates";
    if (candidates.length === 0) {
        container.textContent = "Aucun candidat trouvé.";
        return container;
    }
    const list = document.createElement("ul");
    for (const candidate of candidates) {
        const item = document.createElement("li");
        const title = document.createElement("strong");
        title.textContent = candidate.display_name;
        const coordinates = document.createElement("p");
        coordinates.textContent = `Coordonnées : ${formatCoordinate(candidate.latitude)}, ` +
            formatCoordinate(candidate.longitude);
        const components = document.createElement("p");
        components.textContent = `Composants : ${componentLabel(candidate) || "Non renseignés"}`;
        const provenance = document.createElement("p");
        provenance.textContent = `Provenance : ${provenanceLabel(candidate)}`;
        item.append(title, coordinates, components, provenance,
            button("Voir sur la carte", () => onPreview(candidate)),
            button("Choisir ce candidat", () => onSelect(candidate.selection_token)));
        list.appendChild(item);
    }
    container.appendChild(list);
    return container;
}

function editSection(entry, enrichment, state, onSave, onValidate, onEdit, onCancelEdit) {
    const section = document.createElement("section");
    section.className = "places-workbench-geography-subsection";
    if (!state.editOpen) {
        section.appendChild(button(
            enrichment ? "Modifier la position" : "Saisir une position manuellement",
            onEdit,
        ));
        if (enrichment?.status !== "VALIDATED") {
            section.appendChild(button(
                "Valider cette position", () => onValidate(entry.original_name),
            ));
        }
        return section;
    }
    const form = document.createElement("form");
    form.className = "places-workbench-geography-content";
    const normalizedName = textInput("Nom normalisé", enrichment?.normalized_name || "");
    const latitude = coordinateInput("Latitude", enrichment?.latitude);
    const longitude = coordinateInput("Longitude", enrichment?.longitude);
    const comment = textInput("Commentaire", enrichment?.comment || "");
    form.append(normalizedName.label, latitude.label, longitude.label, comment.label);
    if (enrichment?.geographic_reference) {
        form.appendChild(geographicReference(enrichment));
    }
    const actions = document.createElement("div");
    actions.className = "places-workbench-geography-actions";
    const save = button("Enregistrer les modifications", () => form.requestSubmit());
    save.disabled = true;
    const cancel = button("Annuler", onCancelEdit);
    actions.append(save, cancel);
    form.appendChild(actions);
    const initial = formPayload(entry.original_name, enrichment);
    const updateSaveState = () => {
        save.disabled = samePayload(initial, formPayload(
            entry.original_name, {
                normalized_name: normalizedName.input.value,
                latitude: coordinateValue(latitude.input),
                longitude: coordinateValue(longitude.input),
                comment: comment.input.value,
            },
        ));
    };
    for (const input of (normalizedName.input, latitude.input, longitude.input, comment.input)) {
        input.addEventListener("input", updateSaveState);
    }
    form.addEventListener("submit", event => {
        event.preventDefault();
        const latitudeValue = optionalCoordinate(latitude.input);
        const longitudeValue = optionalCoordinate(longitude.input);
        if (latitudeValue === undefined || longitudeValue === undefined) {
            onSave(null, "Coordonnée invalide.");
            return;
        }
        onSave(formPayload(entry.original_name, {
            normalized_name: normalizedName.input.value,
            latitude: latitudeValue,
            longitude: longitudeValue,
            comment: comment.input.value,
        }));
    });
    section.appendChild(form);
    return section;
}

function geographicReference(enrichment) {
    const reference = enrichment.geographic_reference;
    const section = document.createElement("section");
    section.className = "places-workbench-geographic-reference";
    const title = document.createElement("strong");
    title.textContent = "Référence Geoapify conservée";
    const details = document.createElement("p");
    details.textContent = `${reference.formatted} — ${componentLabel(reference) || "composants non renseignés"}`;
    section.append(title, details);
    if (enrichment.coordinates_overridden) {
        const override = document.createElement("p");
        override.className = "places-workbench-historical-warnings";
        override.textContent = "Les coordonnées actives ont été modifiées manuellement.";
        section.appendChild(override);
    }
    return section;
}

function textInput(labelText, value) {
    const label = document.createElement("label");
    label.textContent = labelText;
    const input = document.createElement("input");
    input.type = "text";
    input.value = value;
    label.appendChild(input);
    return {label, input};
}

function coordinateInput(labelText, value) {
    const field = textInput(labelText, value ?? "");
    field.input.type = "number";
    field.input.step = "any";
    return field;
}

function optionalCoordinate(input) {
    if (input.value.trim() === "") return null;
    const value = Number(input.value);
    return Number.isFinite(value) ? value : undefined;
}

function coordinateValue(input) {
    return input.value.trim() === "" ? null : input.value;
}

function formPayload(originalName, values) {
    return {
        original_name: originalName,
        normalized_name: emptyToNull(values.normalized_name ?? ""),
        latitude: values.latitude === null || values.latitude === "" ? null : Number(values.latitude),
        longitude: values.longitude === null || values.longitude === "" ? null : Number(values.longitude),
        comment: emptyToNull(values.comment ?? ""),
    };
}

function samePayload(left, right) {
    return left.original_name === right.original_name &&
        left.normalized_name === right.normalized_name &&
        left.latitude === right.latitude &&
        left.longitude === right.longitude &&
        left.comment === right.comment;
}

function emptyToNull(value) {
    const trimmed = value.trim();
    return trimmed || null;
}

function componentLabel(candidate) {
    return [
        candidate.city && `ville : ${candidate.city}`,
        candidate.suburb && `quartier : ${candidate.suburb}`,
        candidate.district && `district : ${candidate.district}`,
        candidate.county && `département/comté : ${candidate.county}`,
        candidate.state && `région : ${candidate.state}`,
        candidate.state_code && `code région : ${candidate.state_code}`,
        candidate.postcode && `code postal : ${candidate.postcode}`,
        candidate.country && `pays : ${candidate.country}`,
        candidate.result_type && `type : ${candidate.result_type}`,
    ].filter(Boolean).join(" · ");
}

function provenanceLabel(candidate) {
    return [
        candidate.provider && `fournisseur : ${candidate.provider}`,
        candidate.datasource_name && `données : ${candidate.datasource_name}`,
        candidate.datasource_attribution,
        candidate.rank_confidence !== null && candidate.rank_confidence !== undefined &&
            `confiance fournisseur : ${candidate.rank_confidence}`,
    ].filter(Boolean).join(" · ") || "Geoapify";
}

function formatCoordinate(value) {
    return Number(value).toFixed(6);
}

function button(label, handler) {
    const element = document.createElement("button");
    element.type = "button";
    element.textContent = label;
    element.addEventListener("click", handler);
    return element;
}

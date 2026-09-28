const importForm = document.querySelector("#import-form");
const fileInput = document.querySelector("#gedcom-file");
const importStatus = document.querySelector("#import-status");
const importReport = document.querySelector("#import-report");

const searchForm = document.querySelector("#search-form");
const searchQuery = document.querySelector("#search-query");
const searchResults = document.querySelector("#search-results");

const generationsInput = document.querySelector("#generations");
const selectedPerson = document.querySelector("#selected-person");
const ancestryContainer = document.querySelector("#ancestry");

let selectedPersonId = null;


importForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const file = fileInput.files[0];

    if (!file) {
        return;
    }

    importStatus.textContent = "Import en cours…";
    importReport.hidden = true;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("/imports", {
            method: "POST",
            body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Échec de l'import"
            );
        }

        document.querySelector("#persons-count").textContent =
            data.persons_count;

        document.querySelector("#families-count").textContent =
            data.families_count;

        document.querySelector("#events-count").textContent =
            data.events_count;

        document.querySelector("#places-count").textContent =
            data.places_count;

        importReport.hidden = false;
        importStatus.textContent =
            `Import réussi : ${data.filename}`;

        selectedPersonId = null;
        selectedPerson.textContent =
            "Aucune personne sélectionnée.";
        searchResults.innerHTML = "";
        ancestryContainer.innerHTML = "";

    } catch (error) {
        importStatus.textContent = error.message;
    }
});


searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const query = searchQuery.value.trim();

    if (!query) {
        return;
    }

    searchResults.textContent = "Recherche…";

    try {
        const response = await fetch(
            `/people?q=${encodeURIComponent(query)}`
        );

        const people = await response.json();

        if (!response.ok) {
            throw new Error("Échec de la recherche");
        }

        renderSearchResults(people);

    } catch (error) {
        searchResults.textContent = error.message;
    }
});


generationsInput.addEventListener("change", () => {
    if (selectedPersonId !== null) {
        loadAncestry(selectedPersonId);
    }
});


function renderSearchResults(people) {
    searchResults.innerHTML = "";

    if (people.length === 0) {
        searchResults.textContent = "Aucun résultat.";
        return;
    }

    const list = document.createElement("ul");
    list.className = "people-list";

    for (const person of people) {
        const item = document.createElement("li");
        const button = document.createElement("button");

        button.type = "button";
        button.className = "person-button";
        const birth = person.birth_date
            ? ` — naissance : ${person.birth_date}`
            : " — naissance inconnue";

        button.textContent =
            `${person.given_names} ${person.surname}${birth}`;

        button.addEventListener("click", () => {
            selectedPersonId = person.id;

            const birth = person.birth_date
                ? ` — naissance : ${person.birth_date}`
                : "";

            selectedPerson.textContent =
                `Souche : ${person.given_names} ${person.surname}${birth}`;

            loadAncestry(person.id);
        });

        item.appendChild(button);
        list.appendChild(item);
    }

    searchResults.appendChild(list);
}


async function loadAncestry(personId) {
    const generations = generationsInput.value;

    ancestryContainer.textContent =
        "Calcul de l'ascendance…";

    try {
        const response = await fetch(
            `/people/${encodeURIComponent(personId)}` +
            `/ancestors?generations=${encodeURIComponent(generations)}`
        );

        const ancestors = await response.json();

        if (!response.ok) {
            throw new Error(
                ancestors.detail ||
                "Impossible de calculer l'ascendance"
            );
        }

        renderAncestry(ancestors);

    } catch (error) {
        ancestryContainer.textContent = error.message;
    }
}


function renderAncestry(ancestors) {
    ancestryContainer.innerHTML = "";

    if (ancestors.length === 0) {
        ancestryContainer.textContent =
            "Aucune ascendance connue.";
        return;
    }

    const list = document.createElement("div");
    list.className = "ancestry-list";

    for (const ancestor of ancestors) {
        const row = document.createElement("div");

        row.className = "ancestor";
        row.style.setProperty(
            "--generation",
            ancestor.generation
        );

        const person = ancestor.person;

        row.textContent =
            `G${ancestor.generation} — ` +
            `${person.given_names} ${person.surname}`;

        list.appendChild(row);
    }

    ancestryContainer.appendChild(list);
}
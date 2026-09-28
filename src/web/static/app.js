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

const importDetails =
    document.querySelector("#import-details");

const warningsSection =
    document.querySelector("#warnings-section");

const warningsList =
    document.querySelector("#warnings-list");

const ignoredTagsSection =
    document.querySelector("#ignored-tags-section");

const ignoredTagsList =
    document.querySelector("#ignored-tags-list");

const fanGenerations =
    document.querySelector("#fan-generations");

const fanOpening =
    document.querySelector("#fan-opening");

const fanOpeningValue =
    document.querySelector("#fan-opening-value");

const fanShowUnknown =
    document.querySelector("#fan-show-unknown");

const fanRenderButton =
    document.querySelector("#fan-render");

const fanStatus =
    document.querySelector("#fan-status");

const fanChart =
    document.querySelector("#fan-chart");

let selectedPersonId = null;


importForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const file = fileInput.files[0];

    if (!file) {
        return;
    }

    importStatus.textContent = "Import en cours…";
    importReport.hidden = true;
    importDetails.hidden = true;
    warningsSection.hidden = true;
    ignoredTagsSection.hidden = true;
    warningsList.innerHTML = "";
    ignoredTagsList.innerHTML = "";

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
        
        renderImportDetails(data);

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
            fanRenderButton.disabled = false;
            fanChart.innerHTML = "";
            fanStatus.textContent = "";

            fanRenderButton.addEventListener("click", () => {
                if (selectedPersonId !== null) {
                    loadFanChart(selectedPersonId);
                }
            });

            fanGenerations.addEventListener("change", () => {
                if (selectedPersonId !== null) {
                    loadFanChart(selectedPersonId);
                }
            });

            fanShowUnknown.addEventListener("change", () => {
                if (selectedPersonId !== null) {
                    loadFanChart(selectedPersonId);
                }
            });

            fanOpening.addEventListener("input", () => {
                fanOpeningValue.textContent =
                    `${fanOpening.value}°`;

                if (selectedPersonId !== null) {
                    loadFanChart(selectedPersonId);
                }
            });

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

function renderImportDetails(report) {
    warningsList.innerHTML = "";
    ignoredTagsList.innerHTML = "";

    warningsSection.hidden = true;
    ignoredTagsSection.hidden = true;

    if (report.warnings.length > 0) {
        for (const warning of report.warnings) {
            const item = document.createElement("li");
            item.textContent = warning;
            warningsList.appendChild(item);
        }

        warningsSection.hidden = false;
    }

    if (report.ignored_tags.length > 0) {
        for (const ignored of report.ignored_tags) {
            const item = document.createElement("li");

            item.textContent = ignored.record_id
                ? `${ignored.tag} — ${ignored.record_id}`
                : ignored.tag;

            ignoredTagsList.appendChild(item);
        }

        ignoredTagsSection.hidden = false;
    }

    importDetails.hidden =
        report.warnings.length === 0 &&
        report.ignored_tags.length === 0;
}

async function loadFanChart(personId) {
    const generations = Number(fanGenerations.value);

    fanStatus.textContent = "Calcul de l'éventail…";

    try {
        const response = await fetch(
            `/people/${encodeURIComponent(personId)}` +
            `/sosa?generations=${encodeURIComponent(generations)}`
        );

        const occurrences = await response.json();

        if (!response.ok) {
            throw new Error(
                occurrences.detail ||
                "Impossible de calculer l'éventail"
            );
        }

        renderFanChart(
            occurrences,
            generations,
            fanShowUnknown.checked,
        );

        fanStatus.textContent =
            `${occurrences.length} positions Sosa`;

    } catch (error) {
        fanStatus.textContent = error.message;
    }
}


function renderFanChart(
    occurrences,
    generations,
    showUnknown,
) {
    fanChart.innerHTML = "";

    const openingAngle = Number(fanOpening.value);

    const geometry = createFanGeometry(
        generations,
        openingAngle,
    );

    setFanViewBox(geometry);

    for (const occurrence of occurrences) {
        if (
            occurrence.person === null &&
            !showUnknown
        ) {
            continue;
        }

        const sector = getSectorGeometry(
            occurrence,
            geometry,
        );

        addFanSector(
            occurrence,
            sector,
        );

        if (occurrence.person !== null) {
            addFanLabel(
                occurrence,
                sector,
                geometry,
            );
        }
    }
}


function createFanGeometry(
    generations,
    openingAngle,
) {
    const centerRadius = 52;

    /*
     * Slightly larger inner generations make names easier to read.
     * Outer generations remain compact enough for 8–10 generations.
     */
    const ringWidths = [];

    for (
        let generation = 1;
        generation <= generations;
        generation += 1
    ) {
        let width;

        if (generation <= 2) {
            width = 92;
        } else if (generation <= 4) {
            width = 82;
        } else if (generation <= 6) {
            width = 74;
        } else {
            width = 68;
        }

        ringWidths.push(width);
    }

    const radii = [0, centerRadius];

    let radius = centerRadius;

    for (const width of ringWidths) {
        radius += width;
        radii.push(radius);
    }

    /*
     * The fan is centred on the upper half-plane:
     *
     * 180° -> from -180° to 0°
     * 240° -> from -210° to 30°
     * 360° -> complete circle
     */
    const startAngle =
        -90 - openingAngle / 2;

    const endAngle =
        -90 + openingAngle / 2;

    return {
        generations,
        openingAngle,
        startAngle,
        endAngle,
        radii,
        outerRadius: radii[radii.length - 1],
    };
}


function getSectorGeometry(
    occurrence,
    geometry,
) {
    const generation = occurrence.generation;

    if (generation === 0) {
        return {
            innerRadius: 0,
            outerRadius: geometry.radii[1],
            startAngle: geometry.startAngle,
            endAngle: geometry.endAngle,
        };
    }

    const firstSosa = 2 ** generation;
    const position =
        occurrence.sosa - firstSosa;

    const count = 2 ** generation;

    const sectorAngle =
        geometry.openingAngle / count;

    const startAngle =
        geometry.startAngle +
        position * sectorAngle;

    const endAngle =
        startAngle + sectorAngle;

    return {
        innerRadius:
            geometry.radii[generation],
        outerRadius:
            geometry.radii[generation + 1],
        startAngle,
        endAngle,
    };
}


function addFanSector(
    occurrence,
    sector,
) {
    const svgNS =
        "http://www.w3.org/2000/svg";

    const path =
        document.createElementNS(
            svgNS,
            "path",
        );

    path.setAttribute(
        "d",
        annularSectorPath(
            sector.innerRadius,
            sector.outerRadius,
            sector.startAngle,
            sector.endAngle,
        ),
    );

    path.setAttribute(
        "class",
        occurrence.person
            ? "fan-sector known"
            : "fan-sector unknown",
    );

    path.dataset.sosa = occurrence.sosa;

    fanChart.appendChild(path);
}


function annularSectorPath(
    innerRadius,
    outerRadius,
    startAngle,
    endAngle,
) {
    const angleSize =
        endAngle - startAngle;

    const largeArc =
        angleSize > 180 ? 1 : 0;

    if (innerRadius === 0) {
        /*
         * Sosa 1 is represented as a circular sector.
         */
        if (angleSize >= 359.999) {
            return circlePath(outerRadius);
        }

        const start =
            polar(outerRadius, startAngle);

        const end =
            polar(outerRadius, endAngle);

        return [
            "M 0 0",
            `L ${start.x} ${start.y}`,
            `A ${outerRadius} ${outerRadius}`,
            `0 ${largeArc} 1`,
            `${end.x} ${end.y}`,
            "Z",
        ].join(" ");
    }

    if (angleSize >= 359.999) {
        return annulusPath(
            innerRadius,
            outerRadius,
        );
    }

    const outerStart =
        polar(outerRadius, startAngle);

    const outerEnd =
        polar(outerRadius, endAngle);

    const innerEnd =
        polar(innerRadius, endAngle);

    const innerStart =
        polar(innerRadius, startAngle);

    return [
        `M ${outerStart.x} ${outerStart.y}`,
        `A ${outerRadius} ${outerRadius}`,
        `0 ${largeArc} 1`,
        `${outerEnd.x} ${outerEnd.y}`,
        `L ${innerEnd.x} ${innerEnd.y}`,
        `A ${innerRadius} ${innerRadius}`,
        `0 ${largeArc} 0`,
        `${innerStart.x} ${innerStart.y}`,
        "Z",
    ].join(" ");
}


function circlePath(radius) {
    return [
        `M ${-radius} 0`,
        `A ${radius} ${radius} 0 1 0`,
        `${radius} 0`,
        `A ${radius} ${radius} 0 1 0`,
        `${-radius} 0`,
        "Z",
    ].join(" ");
}


function annulusPath(
    innerRadius,
    outerRadius,
) {
    return [
        `M ${-outerRadius} 0`,
        `A ${outerRadius} ${outerRadius} 0 1 0`,
        `${outerRadius} 0`,
        `A ${outerRadius} ${outerRadius} 0 1 0`,
        `${-outerRadius} 0`,
        "Z",
        `M ${-innerRadius} 0`,
        `A ${innerRadius} ${innerRadius} 0 1 1`,
        `${innerRadius} 0`,
        `A ${innerRadius} ${innerRadius} 0 1 1`,
        `${-innerRadius} 0`,
        "Z",
    ].join(" ");
}


function polar(
    radius,
    angleDegrees,
) {
    const angle =
        angleDegrees * Math.PI / 180;

    return {
        x: radius * Math.cos(angle),
        y: radius * Math.sin(angle),
    };
}


function addFanLabel(
    occurrence,
    sector,
    geometry,
) {
    const svgNS =
        "http://www.w3.org/2000/svg";

    const generation =
        occurrence.generation;

    const angle =
        (
            sector.startAngle +
            sector.endAngle
        ) / 2;

    const radius =
        sector.innerRadius === 0
            ? sector.outerRadius * 0.55
            : (
                sector.innerRadius +
                sector.outerRadius
            ) / 2;

    const point =
        polar(radius, angle);

    const group =
        document.createElementNS(
            svgNS,
            "g",
        );

    group.setAttribute(
        "class",
        "fan-label",
    );

    group.setAttribute(
        "transform",
        labelTransform(
            point,
            angle,
            generation,
        ),
    );

    const availableWidth =
        getLabelAvailableWidth(
            sector,
            generation,
        );

    const availableHeight =
        getLabelAvailableHeight(
            sector,
            generation,
        );

    const lines =
        buildPersonLabelLines(
            occurrence,
            generation,
        );

    const text =
        document.createElementNS(
            svgNS,
            "text",
        );

    text.setAttribute(
        "class",
        "fan-name",
    );

    group.appendChild(text);
    fanChart.appendChild(group);

    fitFanLabel(
        text,
        lines,
        availableWidth,
        availableHeight,
        generation,
    );
}


function labelTransform(
    point,
    angle,
    generation,
) {
    /*
     * Inner generations remain mostly horizontal/tangential.
     * Outer generations become radial.
     */
    if (generation <= 3) {
        return (
            `translate(${point.x} ${point.y})`
        );
    }

    let rotation = angle + 90;

    /*
     * Keep text readable instead of upside-down.
     */
    const normalized =
        ((rotation % 360) + 360) % 360;

    if (
        normalized > 90 &&
        normalized < 270
    ) {
        rotation += 180;
    }

    return (
        `translate(${point.x} ${point.y}) ` +
        `rotate(${rotation})`
    );
}

function buildPersonLabelLines(
    occurrence,
    generation,
) {
    const person = occurrence.person;

    const name =
        `${person.given_names} ${person.surname}`
            .trim();

    const life =
        formatLifeYears(person);

    if (generation <= 2) {
        const lines = [
            `S${occurrence.sosa}`,
            name,
        ];

        if (life) {
            lines.push(life);
        }

        return lines;
    }

    if (generation <= 5) {
        return [
            `S${occurrence.sosa}`,
            name,
            ...(life ? [life] : []),
        ];
    }

    /*
     * Outer generations deliberately start compact.
     * More detailed configurable labels will come later.
     */
    return [
        `S${occurrence.sosa} ${name}`,
    ];
}


function formatLifeYears(person) {
    const birth =
        person.birth_year || "?";

    const death =
        person.death_year || "?";

    if (
        birth === "?" &&
        death === "?"
    ) {
        return "";
    }

    return `${birth}–${death}`;
}


function getLabelAvailableWidth(
    sector,
    generation,
) {
    const angleRadians =
        (
            sector.endAngle -
            sector.startAngle
        ) * Math.PI / 180;

    const middleRadius =
        (
            sector.innerRadius +
            sector.outerRadius
        ) / 2;

    const arcLength =
        middleRadius * angleRadians;

    const radialLength =
        sector.outerRadius -
        sector.innerRadius;

    if (generation <= 3) {
        return Math.max(
            20,
            arcLength * 0.82,
        );
    }

    /*
     * Rotated outer labels use the radial dimension.
     */
    return Math.max(
        20,
        radialLength * 0.86,
    );
}


function getLabelAvailableHeight(
    sector,
    generation,
) {
    const radialLength =
        sector.outerRadius -
        sector.innerRadius;

    if (generation <= 3) {
        return radialLength * 0.78;
    }

    const angleRadians =
        (
            sector.endAngle -
            sector.startAngle
        ) * Math.PI / 180;

    const middleRadius =
        (
            sector.innerRadius +
            sector.outerRadius
        ) / 2;

    return Math.max(
        18,
        middleRadius *
        angleRadians *
        0.78,
    );
}


function fitFanLabel(
    text,
    lines,
    maxWidth,
    maxHeight,
    generation,
) {
    let fontSize =
        initialFanFontSize(generation);

    const minFontSize = 5.5;

    while (fontSize >= minFontSize) {
        populateFanText(
            text,
            lines,
            fontSize,
        );

        const box =
            text.getBBox();

        if (
            box.width <= maxWidth &&
            box.height <= maxHeight
        ) {
            return;
        }

        fontSize -= 0.5;
    }

    /*
     * If the full content still does not fit,
     * progressively remove secondary information.
     */
    if (lines.length > 2) {
        fitFanLabel(
            text,
            lines.slice(0, 2),
            maxWidth,
            maxHeight,
            generation,
        );

        return;
    }

    if (lines.length === 2) {
        fitFanLabel(
            text,
            [lines[1]],
            maxWidth,
            maxHeight,
            generation,
        );

        return;
    }

    populateFanText(
        text,
        lines,
        minFontSize,
    );

    truncateSvgText(
        text,
        maxWidth,
    );
}


function initialFanFontSize(generation) {
    if (generation === 0) {
        return 13;
    }

    if (generation <= 2) {
        return 12;
    }

    if (generation <= 4) {
        return 10;
    }

    if (generation <= 6) {
        return 8.5;
    }

    return 7.5;
}


function populateFanText(
    text,
    lines,
    fontSize,
) {
    const svgNS =
        "http://www.w3.org/2000/svg";

    text.innerHTML = "";

    text.setAttribute(
        "font-size",
        fontSize,
    );

    const lineHeight =
        fontSize * 1.15;

    const totalHeight =
        (lines.length - 1) *
        lineHeight;

    lines.forEach(
        (line, index) => {
            const tspan =
                document.createElementNS(
                    svgNS,
                    "tspan",
                );

            tspan.setAttribute(
                "x",
                "0",
            );

            if (index === 0) {
                tspan.setAttribute(
                    "dy",
                    -totalHeight / 2,
                );
            } else {
                tspan.setAttribute(
                    "dy",
                    lineHeight,
                );
            }

            tspan.textContent = line;

            text.appendChild(tspan);
        }
    );
}


function truncateSvgText(
    text,
    maxWidth,
) {
    const tspan =
        text.querySelector("tspan");

    if (!tspan) {
        return;
    }

    const original =
        tspan.textContent;

    if (
        tspan.getComputedTextLength()
        <= maxWidth
    ) {
        return;
    }

    let value = original;

    while (value.length > 1) {
        value = value.slice(0, -1);

        tspan.textContent =
            `${value}…`;

        if (
            tspan.getComputedTextLength()
            <= maxWidth
        ) {
            return;
        }
    }

    tspan.textContent = "…";
}

function setFanViewBox(geometry) {
    const radius = geometry.outerRadius;

    const points = [
        {x: 0, y: 0},
    ];

    /*
     * Sampling the angular range makes the viewBox work for every
     * opening from 180° to 360°.
     */
    const samples = 180;

    for (
        let index = 0;
        index <= samples;
        index += 1
    ) {
        const ratio =
            index / samples;

        const angle =
            geometry.startAngle +
            geometry.openingAngle * ratio;

        points.push(
            polar(radius, angle)
        );
    }

    const xs =
        points.map(point => point.x);

    const ys =
        points.map(point => point.y);

    const padding = 30;

    const minX =
        Math.min(...xs) - padding;

    const maxX =
        Math.max(...xs) + padding;

    const minY =
        Math.min(...ys) - padding;

    const maxY =
        Math.max(...ys) + padding;

    fanChart.setAttribute(
        "viewBox",
        [
            minX,
            minY,
            maxX - minX,
            maxY - minY,
        ].join(" "),
    );
}
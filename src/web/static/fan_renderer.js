/* Passive SVG fan renderer shared by the embedded and dedicated fan views. */

(function () {
    let activeFanChart = null;
function renderFanChart(svgElement, occurrences, options) {
    activeFanChart = svgElement;
    activeFanChart.innerHTML = "";

    const {generations, showUnknown, openingAngle, labelConfig} = options;

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
                labelConfig,
            );
        }
    }
}


function clearFanLegend(legendElement, legendList) {
    legendList.innerHTML = "";
    legendElement.hidden = true;
}


function renderFanLegend(legendElement, legendList, occurrences, showUnknown, colorMode) {
    clearFanLegend(legendElement, legendList);

    if (colorMode !== "BIRTH_PLACE") {
        return;
    }

    const entries = new Map();

    for (const occurrence of occurrences) {
        if (occurrence.person === null && !showUnknown) {
            continue;
        }

        const entry = legendEntryForOccurrence(occurrence);
        if (entry === null) {
            continue;
        }

        const existing = entries.get(entry.key);
        if (existing !== undefined) {
            existing.occurrencesCount += 1;
        } else {
            entries.set(entry.key, entry);
        }
    }

    const orderedEntries = [...entries.values()].sort(compareLegendEntries);

    for (const entry of orderedEntries) {
        const item = document.createElement("li");
        item.className = "fan-legend-entry";

        const swatch = document.createElement("span");
        swatch.className = "fan-legend-swatch";
        swatch.style.backgroundColor = entry.colorCss;
        swatch.setAttribute("aria-hidden", "true");

        const label = document.createElement("span");
        label.className = "fan-legend-label";
        label.textContent = entry.label;

        const status = document.createElement("span");
        status.className = "fan-legend-status";
        status.textContent = entry.statusLabel || "";

        const count = document.createElement("span");
        count.className = "fan-legend-count";
        count.textContent = entry.occurrencesCount;

        item.append(swatch, label, status, count);
        legendList.appendChild(item);
    }

    legendElement.hidden = orderedEntries.length === 0;
}


function legendEntryForOccurrence(occurrence) {
    if (
        occurrence.color_kind === "GEOGRAPHIC" ||
        occurrence.color_kind === "UNVERIFIED_PLACE"
    ) {
        if (
            occurrence.birth_place_original_name === null ||
            occurrence.birth_place_display_name === null
        ) {
            return null;
        }

        const isGeographic = occurrence.color_kind === "GEOGRAPHIC";

        return {
            key: `${occurrence.color_kind}:${occurrence.birth_place_original_name}`,
            kind: occurrence.color_kind,
            label: occurrence.birth_place_display_name,
            statusLabel: isGeographic ? null : "Non vérifié",
            colorCss: occurrence.color_css,
            occurrencesCount: 1,
        };
    }

    if (occurrence.color_kind === "UNKNOWN_BIRTH") {
        return {
            key: "UNKNOWN_BIRTH",
            kind: "UNKNOWN_BIRTH",
            label: "Naissance inconnue",
            statusLabel: null,
            colorCss: occurrence.color_css,
            occurrencesCount: 1,
        };
    }

    return null;
}

function compareLegendEntries(first, second) {
    const rank = {
        GEOGRAPHIC: 0,
        UNVERIFIED_PLACE: 1,
        UNKNOWN_BIRTH: 2,
    };
    const rankDifference = rank[first.kind] - rank[second.kind];

    if (rankDifference !== 0) {
        return rankDifference;
    }

    if (first.kind === "UNKNOWN_BIRTH") {
        return 0;
    }

    if (first.occurrencesCount !== second.occurrencesCount) {
        return second.occurrencesCount - first.occurrencesCount;
    }

    return first.label.localeCompare(second.label, "fr");
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

    if (occurrence.color_css !== null) {
        path.style.fill = occurrence.color_css;
    }

    activeFanChart.appendChild(path);
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
    labelConfig,
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

    const labelVariants =
        buildPersonLabelVariants(
            occurrence,
            generation,
            labelConfig,
        );

    if (labelVariants.length === 0) {
        return;
    }

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
    activeFanChart.appendChild(group);

    fitFanLabel(
        text,
        labelVariants,
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

function buildPersonLabelVariants(
    occurrence,
    generation,
    config,
) {
    const person = occurrence.person;

    const fullSecondary = buildSecondaryLabelLines(
        person,
        config,
        "full",
    );

    const yearSecondary = buildSecondaryLabelLines(
        person,
        config,
        "year",
    );

    const fullPrimary = buildPrimaryLabelLines(
        occurrence,
        person,
        generation,
        config,
    );

    const variants = [];

    /*
     * Prefer every selected datum, then only the year part of dates.
     * Neither step can introduce information disabled by the user.
     */
    addLabelVariant(
        variants,
        [...fullPrimary, ...fullSecondary],
    );

    addLabelVariant(
        variants,
        [...fullPrimary, ...yearSecondary],
    );

    /*
     * From the year-only form, remove optional details one at a time.
     * The primary identity remains; if none was requested, retain the
     * first selected detail rather than rendering an empty label.
     */
    const essentialSecondary =
        fullPrimary.length === 0 &&
        yearSecondary.length > 0
            ? [yearSecondary[0]]
            : [];

    for (
        let count = yearSecondary.length - 1;
        count >= essentialSecondary.length;
        count -= 1
    ) {
        addLabelVariant(
            variants,
            [...fullPrimary, ...yearSecondary.slice(0, count)],
        );
    }

    if (config.showName) {
        const abbreviatedPrimary = buildPrimaryLabelLines(
            occurrence,
            person,
            generation,
            config,
            true,
        );

        addLabelVariant(variants, abbreviatedPrimary);
    }

    return variants;
}


function buildPrimaryLabelLines(
    occurrence,
    person,
    generation,
    config,
    abbreviateName = false,
) {
    const primary = [];

    if (config.showSosa) {
        primary.push(`S${occurrence.sosa}`);
    }

    if (config.showName) {
        const name = abbreviateName
            ? abbreviatePersonName(person)
            : formatPersonName(person);

        if (name) {
            primary.push(name);
        }
    }

    if (generation >= 6 || abbreviateName) {
        return [primary.join(" ")].filter(Boolean);
    }

    return primary;
}


function buildSecondaryLabelLines(
    person,
    config,
    datePrecision,
) {
    const secondary = [];

    if (config.showBirth) {
        const birth = formatEventLabel(
            "°",
            person.birth_date,
            datePrecision,
        );

        if (birth) {
            secondary.push(birth);
        }
    }

    if (config.showBirthPlace && person.birth_place) {
        secondary.push(person.birth_place);
    }

    if (config.showDeath) {
        const death = formatEventLabel(
            "†",
            person.death_date,
            datePrecision,
        );

        if (death) {
            secondary.push(death);
        }
    }

    if (config.showDeathPlace && person.death_place) {
        secondary.push(person.death_place);
    }

    return secondary;
}


function addLabelVariant(variants, lines) {
    if (lines.length === 0) {
        return;
    }

    const key = lines.join("\u0000");

    if (!variants.some(variant => variant.join("\u0000") === key)) {
        variants.push(lines);
    }
}


function formatPersonName(person) {
    return `${person.given_names} ${person.surname}`.trim();
}


function abbreviatePersonName(person) {
    const abbreviatedGivenNames = person.given_names
        .split(/\s+/)
        .filter(Boolean)
        .map(name => `${name[0]}.`)
        .join(" ");

    return [
        abbreviatedGivenNames,
        person.surname,
    ].filter(Boolean).join(" ");
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
    variants,
    maxWidth,
    maxHeight,
    generation,
) {
    const minFontSize = 5.5;

    for (const lines of variants) {
        let fontSize = initialFanFontSize(generation);

        while (fontSize >= minFontSize) {
            populateFanText(text, lines, fontSize);

            const box = text.getBBox();

            if (
                box.width <= maxWidth &&
                box.height <= maxHeight
            ) {
                return;
            }

            fontSize -= 0.5;
        }
    }

    const finalLines = variants[variants.length - 1];

    populateFanText(
        text,
        finalLines,
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

    activeFanChart.setAttribute(
        "viewBox",
        [
            minX,
            minY,
            maxX - minX,
            maxY - minY,
        ].join(" "),
    );
}

    function formatEventLabel(symbol, value, precision = "full") {
        if (!value) { return ""; }
        if (precision === "year") {
            const match = value.match(/\b\d{4}\b/);
            return match ? `${symbol} ${match[0]}` : "";
        }
        return `${symbol} ${value}`;
    }

    window.renderFanChart = renderFanChart;
    window.renderFanLegend = renderFanLegend;
    window.clearFanLegend = clearFanLegend;
})();

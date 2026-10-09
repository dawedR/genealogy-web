/* Passive SVG renderer shared by the embedded and dedicated tree views. */

(function () {
    const generationScaleWidth = 176;
    function renderTree(svgElement, tree, options = {}) {
        const svgNS = "http://www.w3.org/2000/svg";
        const {bounds} = tree.layout;
        const cardsByOccurrenceId = new Map(
            tree.person_cards.map(card => [card.occurrence_id, card]),
        );
        const portraitMargin = 12;

        svgElement.innerHTML = "";
        svgElement.setAttribute(
            "viewBox",
            `${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}`,
        );
        if (options.naturalSize) {
            svgElement.setAttribute("width", tree.layout.width);
            svgElement.setAttribute("height", tree.layout.height);
        } else {
            svgElement.removeAttribute("width");
            svgElement.removeAttribute("height");
        }

        // Preserve this z-order: edges, card backgrounds, portraits, then text.
        for (const edge of tree.layout.edges) {
            const polyline = document.createElementNS(svgNS, "polyline");
            polyline.setAttribute(
                "points",
                edge.points.map(point => `${point.x},${point.y}`).join(" "),
            );
            polyline.setAttribute("class", "tree-edge");
            svgElement.appendChild(polyline);
        }

        for (const node of tree.layout.person_nodes) {
            const rectangle = document.createElementNS(svgNS, "rect");
            rectangle.setAttribute("x", node.x);
            rectangle.setAttribute("y", node.y);
            rectangle.setAttribute("width", node.width);
            rectangle.setAttribute("height", node.height);
            rectangle.setAttribute("rx", "8");
            rectangle.setAttribute("class", "tree-person-card");
            svgElement.appendChild(rectangle);
        }

        for (const node of tree.layout.person_nodes) {
            const card = cardsByOccurrenceId.get(node.occurrence_id);
            if (card === undefined) {
                continue;
            }
            const portraitSize = Math.max(0, node.width - 2 * portraitMargin);
            const image = document.createElementNS(svgNS, "image");
            image.setAttribute("href", card.portrait.url);
            image.setAttribute("x", node.x + portraitMargin);
            image.setAttribute("y", node.y + portraitMargin);
            image.setAttribute("width", portraitSize);
            image.setAttribute("height", portraitSize);
            image.setAttribute("preserveAspectRatio", "xMidYMid slice");
            image.setAttribute("class", "tree-portrait");
            svgElement.appendChild(image);
        }

        for (const node of tree.layout.person_nodes) {
            const card = cardsByOccurrenceId.get(node.occurrence_id);
            const portraitSize = Math.max(0, node.width - 2 * portraitMargin);
            const firstLineY = node.y + portraitMargin + portraitSize + 16;
            for (const [index, line] of treePersonCardLines(card).entries()) {
                const text = document.createElementNS(svgNS, "text");
                text.setAttribute("x", node.x + node.width / 2);
                text.setAttribute("y", firstLineY + index * 15);
                text.setAttribute(
                    "class",
                    line.kind === "name"
                        ? "tree-person-label tree-person-name"
                        : "tree-person-label tree-person-date",
                );
                text.setAttribute("text-anchor", "middle");
                text.textContent = line.value;
                svgElement.appendChild(text);
                if (line.kind === "name") fitNameText(text, node.width - 2 * portraitMargin);
            }
        }
    }

    function treePersonCardLines(card) {
        if (card === undefined || card.is_unknown) {
            return [{kind: "name", value: "?"}];
        }

        const lines = [
            ["name", card.display_given_name],
            ["name", card.display_surname],
            ["date", card.display_birth_date],
            ["date", card.display_death_date],
        ].filter(([, value]) => value !== null && value.trim() !== "")
            .map(([kind, value]) => ({kind, value}));
        return lines.length > 0 ? lines : [{kind: "name", value: "?"}];
    }

    function fitNameText(text, availableWidth) {
        const textWidth = text.getComputedTextLength();
        if (textWidth > availableWidth) {
            text.setAttribute("textLength", availableWidth);
            text.setAttribute("lengthAdjust", "spacingAndGlyphs");
        }
    }


    function generationScaleRows(tree) {
        const occurrencesById = new Map(
            tree.person_occurrences.map(occurrence => [occurrence.id, occurrence]),
        );
        const rowsByGeneration = new Map();

        for (const node of tree.layout.person_nodes) {
            const occurrence = occurrencesById.get(node.occurrence_id);
            if (occurrence === undefined) {
                continue;
            }
            const nodes = rowsByGeneration.get(occurrence.generation) || [];
            nodes.push(node);
            rowsByGeneration.set(occurrence.generation, nodes);
        }

        const rows = [];
        for (const generation of [...rowsByGeneration.keys()].sort((left, right) => left - right)) {
            const yRows = new Map();
            for (const node of rowsByGeneration.get(generation)) {
                const nodes = yRows.get(node.y) || [];
                nodes.push(node);
                yRows.set(node.y, nodes);
            }
            const positions = [...yRows.entries()].sort(([left], [right]) => left - right);
            const [mainY, mainNodes] = positions[0];
            rows.push({
                generation,
                kind: "main",
                label: generation < 0
                    ? `G${generation} · Ascendance`
                    : generation === 0
                        ? "G0 · Noyau familial"
                        : `G${generation} · Descendance`,
                y: mainY + mainNodes[0].height / 2,
            });
            if (generation > 0) {
                for (const [y, nodes] of positions.slice(1)) {
                    rows.push({
                        generation,
                        kind: "spouses",
                        label: `Conjoints G${generation}`,
                        y: y + nodes[0].height / 2,
                    });
                }
            }
        }
        return rows;
    }

    function renderGenerationScale(svgElement, tree, options = {}) {
        const svgNS = "http://www.w3.org/2000/svg";
        const {bounds} = tree.layout;
        const rows = generationScaleRows(tree);
        const axisX = 18;
        const tickEndX = 34;

        svgElement.innerHTML = "";
        svgElement.setAttribute(
            "viewBox",
            `0 ${bounds.y} ${generationScaleWidth} ${bounds.height}`,
        );
        if (options.naturalSize) {
            svgElement.setAttribute("width", generationScaleWidth);
            svgElement.setAttribute("height", tree.layout.height);
        } else {
            svgElement.removeAttribute("width");
            svgElement.removeAttribute("height");
        }

        const axis = document.createElementNS(svgNS, "line");
        axis.setAttribute("x1", axisX);
        axis.setAttribute("x2", axisX);
        axis.setAttribute("y1", bounds.y);
        axis.setAttribute("y2", bounds.y + bounds.height);
        axis.setAttribute("class", "tree-generation-scale-axis");
        svgElement.appendChild(axis);

        for (const row of rows) {
            const tick = document.createElementNS(svgNS, "line");
            tick.setAttribute("x1", axisX);
            tick.setAttribute("x2", tickEndX);
            tick.setAttribute("y1", row.y);
            tick.setAttribute("y2", row.y);
            tick.setAttribute("class", "tree-generation-scale-tick");
            svgElement.appendChild(tick);

            const label = document.createElementNS(svgNS, "text");
            label.setAttribute("x", tickEndX + 8);
            label.setAttribute("y", row.y + 4);
            label.setAttribute(
                "class",
                row.kind === "spouses"
                    ? "tree-generation-scale-label tree-generation-scale-spouses"
                    : "tree-generation-scale-label",
            );
            label.textContent = row.label;
            svgElement.appendChild(label);
        }
        return rows;
    }
    window.renderTree = renderTree;
    window.renderGenerationScale = renderGenerationScale;
    window.generationScaleWidth = generationScaleWidth;
})();

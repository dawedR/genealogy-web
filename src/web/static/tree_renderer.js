/* Passive SVG renderer shared by the embedded and dedicated tree views. */

(function () {
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
                    index < 2
                        ? "tree-person-label tree-person-name"
                        : "tree-person-label tree-person-date",
                );
                text.setAttribute("text-anchor", "middle");
                text.textContent = line;
                svgElement.appendChild(text);
            }
        }
    }

    function treePersonCardLines(card) {
        if (card === undefined || card.is_unknown) {
            return ["?"];
        }

        const lines = [
            card.display_given_name,
            card.display_surname,
            card.display_birth_date,
            card.display_death_date,
        ].filter(value => value !== null && value.trim() !== "");
        return lines.length > 0 ? lines : ["?"];
    }

    window.renderTree = renderTree;
})();

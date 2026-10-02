const treeViewChart = document.querySelector("#tree-view-chart");
const treeViewTitle = document.querySelector("#tree-view-title");
const treeViewStatus = document.querySelector("#tree-view-status");
const treeViewDiagnostics = document.querySelector("#tree-view-diagnostics");

const treeViewOptions = parseTreeViewOptions(new URLSearchParams(window.location.search));
if (treeViewOptions === null) {
    treeViewStatus.textContent = "Paramètres d’arbre invalides ou incomplets.";
} else {
    loadDedicatedTree(treeViewOptions);
}


function parseTreeViewOptions(params) {
    const personId = params.get("person_id");
    const ancestorGenerations = parseGeneration(params.get("ancestor_generations"));
    const descendantGenerations = parseGeneration(params.get("descendant_generations"));

    if (
        personId === null || personId === "" ||
        ancestorGenerations === null || descendantGenerations === null
    ) {
        return null;
    }

    return {
        personId,
        ancestorGenerations,
        descendantGenerations,
    };
}


function parseGeneration(value) {
    if (value === null || !/^\d+$/.test(value)) {
        return null;
    }
    const generation = Number(value);
    return generation >= 0 && generation <= 10 ? generation : null;
}


async function loadDedicatedTree(options) {
    const query = new URLSearchParams({
        ancestor_generations: String(options.ancestorGenerations),
        descendant_generations: String(options.descendantGenerations),
        show_siblings: "false",
    });
    try {
        const response = await fetch(
            `/people/${encodeURIComponent(options.personId)}/tree?${query.toString()}`,
        );
        const tree = await response.json();
        if (!response.ok) {
            throw new Error(tree.detail || "Impossible de calculer l’arbre familial");
        }

        renderTree(treeViewChart, tree, {naturalSize: true});
        const rootCard = tree.person_cards.find(
            card => card.occurrence_id === tree.root_occurrence_id,
        );
        const rootName = rootCard === undefined
            ? "?"
            : [rootCard.display_given_name, rootCard.display_surname]
                .filter(value => value !== null && value !== "")
                .join(" ") || "?";
        treeViewTitle.textContent = `Arbre familial — ${rootName}`;
        treeViewStatus.textContent = `${tree.person_occurrences.length} occurrences`;
        if (tree.diagnostics.length > 0) {
            treeViewDiagnostics.textContent =
                `${tree.diagnostics.length} diagnostic${
                    tree.diagnostics.length > 1 ? "s" : ""
                } dans les données`;
            treeViewDiagnostics.hidden = false;
        }
    } catch (error) {
        treeViewStatus.textContent = error.message;
    }
}

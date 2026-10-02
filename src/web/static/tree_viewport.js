/* Tree-specific viewport positioning, shared by embedded and dedicated views. */

(function () {
    const ROOT_VERTICAL_FRACTION = 0.57;

    function afterLayout(callback) {
        requestAnimationFrame(() => requestAnimationFrame(callback));
    }

    function rootCenterInStage({stage, treeSvg, tree, zoom = 1}) {
        if (tree === null) return null;
        const rootNode = tree.layout.person_nodes.find(
            node => node.occurrence_id === tree.root_occurrence_id,
        );
        if (rootNode === undefined) return null;

        const {bounds} = tree.layout;
        return {
            x: treeSvg.offsetLeft + (rootNode.x - bounds.x + rootNode.width / 2) * zoom,
            y: treeSvg.offsetTop + (rootNode.y - bounds.y + rootNode.height / 2) * zoom,
        };
    }

    function resetTreeViewportToRoot({viewport, stage, treeSvg, tree, zoom = 1}) {
        afterLayout(() => {
            const rootCenter = rootCenterInStage({stage, treeSvg, tree, zoom});
            if (rootCenter === null) return;
            viewport.scrollLeft = Math.max(0, Math.min(
                rootCenter.x - viewport.clientWidth / 2,
                viewport.scrollWidth - viewport.clientWidth,
            ));
            viewport.scrollTop = Math.max(0, Math.min(
                rootCenter.y - viewport.clientHeight * ROOT_VERTICAL_FRACTION,
                viewport.scrollHeight - viewport.clientHeight,
            ));
        });
    }

    function preserveTreeRootPosition({viewport, stage, treeSvg, tree, before, zoom = 1}) {
        afterLayout(() => {
            const after = rootCenterInStage({stage, treeSvg, tree, zoom});
            if (before === null || after === null) return;
            viewport.scrollLeft += after.x - before.x;
            viewport.scrollTop += after.y - before.y;
        });
    }

    window.rootCenterInTreeStage = rootCenterInStage;
    window.resetTreeViewportToRoot = resetTreeViewportToRoot;
    window.preserveTreeRootPosition = preserveTreeRootPosition;
})();

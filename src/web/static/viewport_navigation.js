/* Shared viewport-only navigation: uniform zoom, scroll pan and fitting. */

(function () {
    const MIN_ZOOM = 0.1;
    const MAX_ZOOM = 3;
    const ZOOM_STEP = 0.1;
    const FIT_MARGIN = 0.95;

    function createViewportNavigation(options) {
        const {
            viewport,
            stage,
            getNaturalSize,
            applyContentZoom,
            zoomOutput,
            zoomOutButton,
            zoomInButton,
            fitButton,
            actualSizeButton,
            isPanTarget = () => true,
        } = options;
        let zoom = 1;
        let panState = null;

        function applyZoom(nextZoom, focalPoint = null) {
            const size = getNaturalSize();
            if (size.width <= 0 || size.height <= 0) {
                return;
            }
            const clampedZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, nextZoom));
            const focal = focalPoint || {
                x: viewport.clientWidth / 2,
                y: viewport.clientHeight / 2,
            };
            const contentX = (viewport.scrollLeft + focal.x) / zoom;
            const contentY = (viewport.scrollTop + focal.y) / zoom;
            zoom = clampedZoom;
            stage.style.width = `${size.width * zoom}px`;
            stage.style.height = `${size.height * zoom}px`;
            applyContentZoom(zoom);
            zoomOutput.textContent = `${Math.round(zoom * 100)} %`;
            requestAnimationFrame(() => {
                viewport.scrollLeft = contentX * zoom - focal.x;
                viewport.scrollTop = contentY * zoom - focal.y;
            });
        }

        function syncSize() {
            const size = getNaturalSize();
            if (size.width <= 0 || size.height <= 0) return false;
            stage.style.width = `${size.width * zoom}px`;
            stage.style.height = `${size.height * zoom}px`;
            applyContentZoom(zoom);
            zoomOutput.textContent = `${Math.round(zoom * 100)} %`;
            return true;
        }

        function resetToActualSize() {
            zoom = 1;
            syncSize();
        }

        function fit() {
            const size = getNaturalSize();
            if (size.width <= 0 || size.height <= 0) {
                return;
            }
            applyZoom(FIT_MARGIN * Math.min(
                viewport.clientWidth / size.width,
                viewport.clientHeight / size.height,
            ));
        }

        function center(point, verticalFraction = 0.5) {
            requestAnimationFrame(() => {
                viewport.scrollLeft = Math.max(0,
                    point.x * zoom - viewport.clientWidth / 2,
                );
                viewport.scrollTop = Math.max(0,
                    point.y * zoom - viewport.clientHeight * verticalFraction,
                );
            });
        }

        zoomOutButton.addEventListener("click", () => applyZoom(zoom - ZOOM_STEP));
        zoomInButton.addEventListener("click", () => applyZoom(zoom + ZOOM_STEP));
        actualSizeButton.addEventListener("click", () => applyZoom(1));
        fitButton.addEventListener("click", fit);
        viewport.addEventListener("wheel", event => {
            if (!event.ctrlKey) {
                return;
            }
            event.preventDefault();
            const rectangle = viewport.getBoundingClientRect();
            applyZoom(zoom + (event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP), {
                x: event.clientX - rectangle.left,
                y: event.clientY - rectangle.top,
            });
        }, {passive: false});
        viewport.addEventListener("pointerdown", event => {
            if (event.button !== 0 || !isPanTarget(event.target)) {
                return;
            }
            panState = {
                pointerId: event.pointerId,
                clientX: event.clientX,
                clientY: event.clientY,
                scrollLeft: viewport.scrollLeft,
                scrollTop: viewport.scrollTop,
            };
            viewport.setPointerCapture(event.pointerId);
            viewport.classList.add("is-panning");
        });
        viewport.addEventListener("pointermove", event => {
            if (panState === null || panState.pointerId !== event.pointerId) {
                return;
            }
            viewport.scrollLeft = panState.scrollLeft - (event.clientX - panState.clientX);
            viewport.scrollTop = panState.scrollTop - (event.clientY - panState.clientY);
        });
        for (const eventName of ["pointerup", "pointercancel"]) {
            viewport.addEventListener(eventName, event => {
                if (panState === null || panState.pointerId !== event.pointerId) {
                    return;
                }
                viewport.releasePointerCapture(event.pointerId);
                panState = null;
                viewport.classList.remove("is-panning");
            });
        }

        return {
            actualSize: () => applyZoom(1),
            resetToActualSize,
            syncSize,
            applyZoom,
            center,
            fit,
            get zoom() { return zoom; },
        };
    }

    window.createViewportNavigation = createViewportNavigation;
    window.VIEWPORT_FIT_MARGIN = FIT_MARGIN;
})();

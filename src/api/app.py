from __future__ import annotations

import os
import tempfile
import time
import uuid
from dataclasses import dataclass, replace
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)

from src.api.schemas import (
    AncestorPlaceOccurrenceResponse,
    AncestorResponse,
    CombinedTreeOptionsResponse,
    CombinedTreeResponse,
    CycleTruncatedDiagnosticResponse,
    GeocodingCandidateResponse,
    GeocodingCandidatesRequest,
    GeocodingCandidateSelectionRequest,
    HealthResponse,
    IgnoredTagResponse,
    ImportReportResponse,
    MissingPersonReferenceDiagnosticResponse,
    MultipleParentFamiliesDiagnosticResponse,
    PersonResponse,
    PlaceEnrichmentResponse,
    PlaceEnrichmentValidationRequest,
    PlaceEnrichmentUpdateRequest,
    PlaceInventoryResponse,
    SosaOccurrenceResponse,
    TreeDiagnosticResponse,
    TreeCentralFamilyCoreResponse,
    LayoutBoundsResponse,
    LayoutEdgeResponse,
    LayoutPointResponse,
    PersonLayoutNodeResponse,
    PortraitReferenceResponse,
    TreePersonCardResponse,
    TreeParentChildLinkResponse,
    TreeLayoutResponse,
    TreePersonOccurrenceResponse,
    TreeUnionOccurrenceResponse,
    TreeUnionPartnerResponse,
    UnionLayoutNodeResponse,
)
from src.domain.models import (
    Genealogy,
    ImportReport,
    Person,
    PlaceEnrichment,
    PlaceEnrichmentStatus,
)
from src.gedcom.importer import import_gedcom
from src.services.ancestry import get_ancestors
from src.services.ancestry_geography import build_ancestry_geography
from src.services.colors import ColorConfiguration, ColorResult, ColorService, GeoPoint
from src.services.combined_tree import (
    CombinedTreeOptions,
    CycleTruncatedDiagnostic,
    MissingPersonReferenceDiagnostic,
    MultipleParentFamiliesDiagnostic,
    TreeDiagnostic,
    build_combined_tree,
)
from src.services.search import (
    get_birth_date,
    get_birth_year,
    search_people,
    get_birth_place,
    get_death_date,
    get_death_year,
    get_death_place,
)

from src.services.geocoding import (
    Geocoder,
    GeocodingCandidate,
    GeocodingNetworkError,
    GeocodingProviderError,
    GeocodingRequestRejectedError,
    GeocodingResponseError,
    GeocodingTimeoutError,
    GeocodingUnavailableError,
    UnavailableGeocoder,
)
from src.services.geoapify import GeoapifyGeocoder
from src.services.places import inventory_places
from src.services.sosa import build_sosa_ancestry
from src.services.portraits import PortraitResolver
from src.services.tree_cards import build_tree_person_card
from src.services.tree_layout import TreeLayout, layout_combined_tree
from src.services.tree_view import PORTRAIT_TREE_LAYOUT_CONFIGURATION
from src.storage.place_enrichments import (
    InMemoryPlaceEnrichmentStore,
    JsonPlaceEnrichmentStore,
    PlaceEnrichmentStore,
)


@dataclass(frozen=True)
class _PendingGeocodingCandidate:
    original_name: str
    candidate: GeocodingCandidate
    expires_at: float


class _PendingGeocodingCandidates:
    """Small in-memory registry for explicit candidate selection."""

    def __init__(self, ttl_seconds: float = 600) -> None:
        self._ttl_seconds = ttl_seconds
        self._candidates: dict[str, _PendingGeocodingCandidate] = {}

    def add(self, original_name: str, candidate: GeocodingCandidate) -> str:
        self._discard_expired()
        token = uuid.uuid4().hex
        self._candidates[token] = _PendingGeocodingCandidate(
            original_name=original_name,
            candidate=candidate,
            expires_at=time.monotonic() + self._ttl_seconds,
        )
        return token

    def take(self, original_name: str, token: str) -> GeocodingCandidate | None:
        self._discard_expired()
        pending = self._candidates.pop(token, None)
        if pending is None or pending.original_name != original_name:
            return None
        return pending.candidate

    def _discard_expired(self) -> None:
        now = time.monotonic()
        self._candidates = {
            token: pending
            for token, pending in self._candidates.items()
            if pending.expires_at > now
        }


def create_app(
    genealogy: Genealogy | None = None,
    place_enrichment_store: PlaceEnrichmentStore | None = None,
    geocoder: Geocoder | None = None,
    portrait_resolver: PortraitResolver | None = None,
) -> FastAPI:
    initial_genealogy = genealogy or Genealogy()
    initial_place_enrichment_store = (
        place_enrichment_store or InMemoryPlaceEnrichmentStore()
    )
    initial_geocoder = geocoder or UnavailableGeocoder()
    initial_portrait_resolver = portrait_resolver or PortraitResolver(
        registry_path=Path("data/portraits.json"),
        portraits_root=Path("data/portraits"),
    )
    pending_geocoding_candidates = _PendingGeocodingCandidates()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.genealogy = initial_genealogy
        app.state.place_enrichment_store = initial_place_enrichment_store
        app.state.geocoder = initial_geocoder
        app.state.pending_geocoding_candidates = pending_geocoding_candidates
        app.state.portrait_resolver = initial_portrait_resolver
        yield

    app = FastAPI(
        title="Genealogy Web",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    web_root = (
        Path(__file__).resolve().parent.parent
        / "web"
        / "static"
    )

    app.mount(
        "/static",
        StaticFiles(directory=web_root),
        name="static",
    )
    app.mount(
        "/portraits",
        StaticFiles(
            directory=initial_portrait_resolver.portraits_root,
            check_dir=False,
        ),
        name="portraits",
    )

    @app.get(
        "/",
        include_in_schema=False,
    )
    
    def index() -> FileResponse:
        return FileResponse(web_root / "index.html")

    @app.get(
        "/tree-view",
        include_in_schema=False,
    )
    def tree_view() -> FileResponse:
        return FileResponse(web_root / "tree_view.html")

    @app.get(
        "/health",
        response_model=HealthResponse,
    )
    def health(request: Request) -> HealthResponse:
        current = _genealogy(request)

        return HealthResponse(
            status="ok",
            persons_count=len(current.persons),
            families_count=len(current.families),
        )

    @app.post(
        "/imports",
        response_model=ImportReportResponse,
    )
    async def upload_gedcom(
        request: Request,
        file: UploadFile = File(...),
    ) -> ImportReportResponse:
        filename = file.filename or "upload.ged"

        suffix = Path(filename).suffix or ".ged"

        temp_path: str | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=suffix,
                delete=False,
            ) as temp_file:
                temp_path = temp_file.name

                while chunk := await file.read(1024 * 1024):
                    temp_file.write(chunk)

            genealogy, report = import_gedcom(temp_path)

        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"GEDCOM import failed: {exc}",
            ) from exc

        finally:
            await file.close()

            if temp_path is not None:
                try:
                    os.unlink(temp_path)
                except FileNotFoundError:
                    pass

        # Atomic from the application's point of view:
        # only replace the current genealogy after a successful import.
        request.app.state.genealogy = genealogy

        return _import_report_response(
            filename=filename,
            report=report,
        )

    @app.get(
        "/places",
        response_model=list[PlaceInventoryResponse],
    )
    def places_inventory(
        request: Request,
    ) -> list[PlaceInventoryResponse]:
        enrichments = _place_enrichment_store(request).get_all()

        return [
            PlaceInventoryResponse(
                original_name=entry.original_name,
                occurrences_count=entry.occurrences_count,
                persons_count=entry.persons_count,
                event_counts=entry.event_counts,
                enrichment=_enrichment_response(
                    enrichments.get(entry.original_name)
                ),
            )
            for entry in inventory_places(_genealogy(request))
        ]

    @app.post(
        "/geocoding/candidates",
        response_model=list[GeocodingCandidateResponse],
    )
    def geocoding_candidates(payload: GeocodingCandidatesRequest, request: Request) -> list[GeocodingCandidateResponse]:
        _ensure_known_place(request, payload.original_name)
        query = payload.query.strip() if payload.query else payload.original_name
        try:
            candidates = _geocoder(request).search(query, limit=5)
        except GeocodingUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except GeocodingRequestRejectedError as exc:
            detail = f"La requête a été refusée par Geoapify (HTTP {exc.http_status})."
            raise HTTPException(status_code=422, detail=detail) from exc
        except GeocodingTimeoutError as exc:
            raise HTTPException(status_code=504, detail=str(exc)) from exc
        except GeocodingNetworkError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except GeocodingResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except GeocodingProviderError as exc:
            raise HTTPException(status_code=502, detail="La recherche Geoapify a échoué.") from exc
        pending = _pending_geocoding_candidates(request)
        return [_candidate_response(candidate, pending.add(payload.original_name, candidate)) for candidate in candidates[:5]]

    @app.post(
        "/place-enrichments/geoapify-selection",
        response_model=PlaceEnrichmentResponse,
    )
    def select_geoapify_candidate(payload: GeocodingCandidateSelectionRequest, request: Request) -> PlaceEnrichmentResponse:
        _ensure_known_place(request, payload.original_name)
        candidate = _pending_geocoding_candidates(request).take(payload.original_name, payload.candidate_token)
        if candidate is None or candidate.provider != "geoapify":
            raise HTTPException(status_code=404, detail="Geocoding candidate not found")
        try:
            enrichment = PlaceEnrichment(
                original_name=payload.original_name,
                normalized_name=candidate.display_name,
                latitude=candidate.latitude,
                longitude=candidate.longitude,
                status=PlaceEnrichmentStatus.MANUAL,
                source="geoapify",
                confidence=None,
                comment=None,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        _place_enrichment_store(request).save(enrichment)
        return _enrichment_response(enrichment)

    @app.post(
        "/place-enrichments/validate",
        response_model=PlaceEnrichmentResponse,
    )
    def validate_place_enrichment(
        payload: PlaceEnrichmentValidationRequest,
        request: Request,
    ) -> PlaceEnrichmentResponse:
        _ensure_known_place(request, payload.original_name)
        existing = _place_enrichment_store(request).get(payload.original_name)

        if existing is None:
            raise HTTPException(status_code=404, detail="Place enrichment not found")

        try:
            enrichment = replace(
                existing,
                status=PlaceEnrichmentStatus.VALIDATED,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        _place_enrichment_store(request).save(enrichment)
        return _enrichment_response(enrichment)

    @app.put(
        "/place-enrichments",
        response_model=PlaceEnrichmentResponse,
    )
    def save_place_enrichment(
        payload: PlaceEnrichmentUpdateRequest,
        request: Request,
    ) -> PlaceEnrichmentResponse:
        _ensure_known_place(request, payload.original_name)
        existing = _place_enrichment_store(request).get(payload.original_name)

        if existing is None:
            status = PlaceEnrichmentStatus.MANUAL
            source = None
            confidence = None
        else:
            coordinates_changed = (
                payload.latitude != existing.latitude
                or payload.longitude != existing.longitude
            )
            normalized_name_changed = (
                payload.normalized_name != existing.normalized_name
            )

            if coordinates_changed:
                status = PlaceEnrichmentStatus.MANUAL
                source = None
                confidence = None
            elif normalized_name_changed:
                status = PlaceEnrichmentStatus.MANUAL
                source = existing.source
                confidence = None
            else:
                status = existing.status
                source = existing.source
                confidence = existing.confidence

        try:
            enrichment = PlaceEnrichment(
                original_name=payload.original_name,
                normalized_name=payload.normalized_name,
                latitude=payload.latitude,
                longitude=payload.longitude,
                status=status,
                source=source,
                confidence=confidence,
                comment=payload.comment,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc

        _place_enrichment_store(request).save(enrichment)

        return _enrichment_response(enrichment)

    @app.get(
        "/people",
        response_model=list[PersonResponse],
    )
    def people_search(
        request: Request,
        q: str = Query(min_length=1),
        limit: int = Query(default=20, ge=1, le=100),
    ) -> list[PersonResponse]:
        current = _genealogy(request)

        return [
            _person_response(person)
            for person in search_people(
                current,
                q,
                limit=limit,
            )
        ]

    @app.get(
        "/people/{person_id}",
        response_model=PersonResponse,
    )
    def person_detail(
        person_id: str,
        request: Request,
    ) -> PersonResponse:
        current = _genealogy(request)

        person = current.persons.get(person_id)

        if person is None:
            raise HTTPException(
                status_code=404,
                detail="Person not found",
            )

        return _person_response(person)

    @app.get(
        "/people/{person_id}/ancestors",
        response_model=list[AncestorResponse],
    )
    def ancestors(
        person_id: str,
        request: Request,
        generations: int = Query(
            default=3,
            ge=0,
            le=20,
        ),
    ) -> list[AncestorResponse]:
        current = _genealogy(request)

        if person_id not in current.persons:
            raise HTTPException(
                status_code=404,
                detail="Person not found",
            )

        return [
            AncestorResponse(
                person=_person_response(ancestor.person),
                generation=ancestor.generation,
            )
            for ancestor in get_ancestors(
                current,
                person_id,
                generations=generations,
            )
        ]

    @app.get(
        "/people/{person_id}/tree",
        response_model=CombinedTreeResponse,
    )
    def combined_tree(
        person_id: str,
        request: Request,
        ancestor_generations: int = Query(default=4, ge=0, le=10),
        descendant_generations: int = Query(default=3, ge=0, le=10),
        show_siblings: bool = Query(default=True),
    ) -> CombinedTreeResponse:
        current = _genealogy(request)
        if person_id not in current.persons:
            raise HTTPException(status_code=404, detail="Person not found")

        projection = build_combined_tree(
            current,
            CombinedTreeOptions(
                root_person_id=person_id,
                ancestor_generations=ancestor_generations,
                descendant_generations=descendant_generations,
                show_siblings=show_siblings,
            ),
        )
        return _combined_tree_response(
            projection,
            current,
            layout_combined_tree(projection, PORTRAIT_TREE_LAYOUT_CONFIGURATION),
            initial_portrait_resolver,
        )

    @app.get(
        "/people/{person_id}/sosa",
        response_model=list[SosaOccurrenceResponse],
    )
    def sosa_ancestry(
        person_id: str,
        request: Request,
        generations: int = Query(
            default=5,
            ge=1,
            le=10,
        ),
        color_mode: Literal["NONE", "BIRTH_PLACE"] = Query(default="NONE"),
    ) -> list[SosaOccurrenceResponse]:
        current = _genealogy(request)

        if person_id not in current.persons:
            raise HTTPException(
                status_code=404,
                detail="Person not found",
            )

        enrichments = _place_enrichment_store(request).get_all()
        color_service = (
            _birth_place_color_service(
                current,
                person_id,
                enrichments,
            )
            if color_mode == "BIRTH_PLACE"
            else None
        )

        occurrences = build_sosa_ancestry(
            current,
            person_id,
            generations=generations,
        )

        result: list[SosaOccurrenceResponse] = []

        for occurrence in occurrences:
            person = (
                current.persons.get(occurrence.person_id)
                if occurrence.person_id is not None
                else None
            )

            color = (
                _color_for_birth_place(
                    color_service,
                    person,
                    enrichments,
                )
                if color_service is not None
                else None
            )
            (
                birth_place_original_name,
                birth_place_display_name,
            ) = (
                _birth_place_display_fields(person, enrichments)
                if color_service is not None
                else (None, None)
            )

            result.append(
                SosaOccurrenceResponse(
                    sosa=occurrence.sosa,
                    generation=occurrence.generation,
                    person=(
                        _person_response(person)
                        if person is not None
                        else None
                    ),
                    birth_place_original_name=birth_place_original_name,
                    birth_place_display_name=birth_place_display_name,
                    color_kind=color.kind if color is not None else None,
                    color_css=color.css if color is not None else None,
                    color_reliable=color.reliable if color is not None else None,
                )
            )

        return result

    @app.get(
        "/people/{person_id}/sosa/places",
        response_model=list[AncestorPlaceOccurrenceResponse],
    )
    def sosa_places(
        person_id: str,
        request: Request,
        generations: int = Query(
            default=5,
            ge=0,
            le=10,
        ),
    ) -> list[AncestorPlaceOccurrenceResponse]:
        current = _genealogy(request)

        if person_id not in current.persons:
            raise HTTPException(status_code=404, detail="Person not found")

        enrichments = _place_enrichment_store(request).get_all()
        return [
            AncestorPlaceOccurrenceResponse(
                sosa=occurrence.sosa,
                generation=occurrence.generation,
                person_id=occurrence.person_id,
                birth_place_original_name=occurrence.birth_place_original_name,
                enrichment=_enrichment_response(occurrence.enrichment),
            )
            for occurrence in build_ancestry_geography(
                current,
                person_id,
                generations,
                enrichments,
            )
        ]

    return app


def _combined_tree_response(
    projection,
    genealogy: Genealogy,
    layout: TreeLayout,
    portraits: PortraitResolver,
) -> CombinedTreeResponse:
    return CombinedTreeResponse(
        root_occurrence_id=projection.root_occurrence_id,
        central_family_core=TreeCentralFamilyCoreResponse(
            root_occurrence_id=projection.central_family_core.root_occurrence_id,
            member_occurrence_ids=list(projection.central_family_core.member_occurrence_ids),
            union_occurrence_ids=list(projection.central_family_core.union_occurrence_ids),
        ),
        options=CombinedTreeOptionsResponse(
            root_person_id=projection.options.root_person_id,
            ancestor_generations=projection.options.ancestor_generations,
            descendant_generations=projection.options.descendant_generations,
            show_siblings=projection.options.show_siblings,
        ),
        person_occurrences=[
            _tree_person_occurrence_response(occurrence, genealogy)
            for occurrence in projection.person_occurrences
        ],
        person_cards=[
            _tree_person_card_response(
                build_tree_person_card(occurrence, genealogy, portraits)
            )
            for occurrence in projection.person_occurrences
        ],
        union_occurrences=[
            TreeUnionOccurrenceResponse(
                id=union.id,
                family_id=union.family_id,
                generation=union.generation,
                partners=[
                    TreeUnionPartnerResponse(
                        occurrence_id=partner.occurrence_id,
                        role=partner.role.value,
                    )
                    for partner in union.partners
                ],
            )
            for union in projection.union_occurrences
        ],
        parent_child_links=[
            TreeParentChildLinkResponse(
                union_occurrence_id=link.union_occurrence_id,
                child_occurrence_id=link.child_occurrence_id,
            )
            for link in projection.parent_child_links
        ],
        diagnostics=[
            _tree_diagnostic_response(diagnostic)
            for diagnostic in projection.diagnostics
        ],
        layout=_tree_layout_response(layout),
    )


def _tree_layout_response(layout: TreeLayout) -> TreeLayoutResponse:
    return TreeLayoutResponse(
        person_nodes=[
            PersonLayoutNodeResponse(
                occurrence_id=node.occurrence_id,
                x=node.x,
                y=node.y,
                width=node.width,
                height=node.height,
            )
            for node in layout.person_nodes
        ],
        union_nodes=[
            UnionLayoutNodeResponse(
                union_occurrence_id=node.union_occurrence_id,
                x=node.x,
                y=node.y,
            )
            for node in layout.union_nodes
        ],
        edges=[
            LayoutEdgeResponse(
                kind=edge.kind.value,
                union_occurrence_id=edge.union_occurrence_id,
                person_occurrence_id=edge.person_occurrence_id,
                points=[
                    LayoutPointResponse(x=point.x, y=point.y)
                    for point in edge.points
                ],
            )
            for edge in layout.edges
        ],
        width=layout.width,
        height=layout.height,
        bounds=LayoutBoundsResponse(
            x=layout.bounds.x,
            y=layout.bounds.y,
            width=layout.bounds.width,
            height=layout.bounds.height,
        ),
    )


def _tree_person_occurrence_response(
    occurrence,
    genealogy: Genealogy,
) -> TreePersonOccurrenceResponse:
    person = (
        genealogy.persons.get(occurrence.person_id)
        if occurrence.person_id is not None
        else None
    )
    return TreePersonOccurrenceResponse(
        id=occurrence.id,
        person_id=occurrence.person_id,
        generation=occurrence.generation,
        missing_person_id=occurrence.missing_person_id,
        cycle_truncated=occurrence.cycle_truncated,
        given_names=person.given_names if person is not None else None,
        surname=person.surname if person is not None else None,
        sex=person.sex.value if person is not None else None,
    )


def _tree_person_card_response(card) -> TreePersonCardResponse:
    return TreePersonCardResponse(
        occurrence_id=card.occurrence_id,
        person_id=card.person_id,
        is_unknown=card.is_unknown,
        sex=card.sex.value if card.sex is not None else None,
        given_names=card.given_names,
        display_given_name=card.display_given_name,
        surname=card.surname,
        display_surname=card.display_surname,
        birth_date=card.birth_date,
        display_birth_date=card.display_birth_date,
        death_date=card.death_date,
        display_death_date=card.display_death_date,
        portrait=PortraitReferenceResponse(
            url=card.portrait.url,
            kind=card.portrait.kind.value,
        ),
    )


def _tree_diagnostic_response(
    diagnostic: TreeDiagnostic,
) -> TreeDiagnosticResponse:
    if isinstance(diagnostic, MultipleParentFamiliesDiagnostic):
        return MultipleParentFamiliesDiagnosticResponse(
            code=diagnostic.code.value,
            person_id=diagnostic.person_id,
            family_ids=list(diagnostic.family_ids),
            selected_family_id=diagnostic.selected_family_id,
        )
    if isinstance(diagnostic, CycleTruncatedDiagnostic):
        return CycleTruncatedDiagnosticResponse(
            code=diagnostic.code.value,
            person_id=diagnostic.person_id,
            occurrence_id=diagnostic.occurrence_id,
            traversal=diagnostic.traversal.value,
            path_person_ids=list(diagnostic.path_person_ids),
        )
    if isinstance(diagnostic, MissingPersonReferenceDiagnostic):
        return MissingPersonReferenceDiagnosticResponse(
            code=diagnostic.code.value,
            family_id=diagnostic.family_id,
            missing_person_id=diagnostic.missing_person_id,
            role=diagnostic.role.value,
            occurrence_id=diagnostic.occurrence_id,
        )
    raise TypeError(f"Unsupported tree diagnostic: {diagnostic!r}")


def _ensure_known_place(request: Request, original_name: str) -> None:
    known_original_names = {entry.original_name for entry in inventory_places(_genealogy(request))}
    if original_name not in known_original_names:
        raise HTTPException(status_code=404, detail="Place not found")


def _candidate_response(candidate: GeocodingCandidate, selection_token: str) -> GeocodingCandidateResponse:
    return GeocodingCandidateResponse(
        selection_token=selection_token, provider=candidate.provider,
        provider_id=candidate.provider_id, display_name=candidate.display_name,
        latitude=candidate.latitude, longitude=candidate.longitude,
        city=candidate.city, postcode=candidate.postcode, region=candidate.region,
        country=candidate.country, result_type=candidate.result_type,
    )


def _geocoder(request: Request) -> Geocoder:
    return request.app.state.geocoder


def _pending_geocoding_candidates(request: Request) -> _PendingGeocodingCandidates:
    return request.app.state.pending_geocoding_candidates


def _genealogy(request: Request) -> Genealogy:
    return request.app.state.genealogy


def _place_enrichment_store(request: Request) -> PlaceEnrichmentStore:
    return request.app.state.place_enrichment_store


def _birth_place_color_service(
    genealogy: Genealogy,
    root_person_id: str,
    enrichments: dict[str, PlaceEnrichment],
) -> ColorService:
    root_person = genealogy.persons[root_person_id]
    birth_place = get_birth_place(root_person)
    enrichment = (
        enrichments.get(birth_place)
        if birth_place is not None
        else None
    )

    if (
        enrichment is None
        or enrichment.status is not PlaceEnrichmentStatus.VALIDATED
        or enrichment.latitude is None
        or enrichment.longitude is None
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "BIRTH_PLACE color mode requires a VALIDATED birth place "
                "for the root person"
            ),
        )

    return ColorService(
        ColorConfiguration(
            reference=GeoPoint(
                enrichment.latitude,
                enrichment.longitude,
            )
        )
    )


def _birth_place_display_fields(
    person: Person | None,
    enrichments: dict[str, PlaceEnrichment],
) -> tuple[str | None, str | None]:
    if person is None:
        return None, None

    original_name = get_birth_place(person)
    if original_name is None:
        return None, None

    enrichment = enrichments.get(original_name)
    display_name = (
        enrichment.normalized_name.strip()
        if enrichment is not None
        and enrichment.normalized_name is not None
        and enrichment.normalized_name.strip()
        else original_name
    )
    return original_name, display_name


def _color_for_birth_place(
    color_service: ColorService,
    person: Person | None,
    enrichments: dict[str, PlaceEnrichment],
) -> ColorResult:
    if person is None:
        return color_service.unknown_birth_color()

    birth_place = get_birth_place(person)
    if birth_place is None:
        return color_service.unknown_birth_color()

    return color_service.color_for_enrichment(enrichments.get(birth_place))


def _enrichment_response(
    enrichment: PlaceEnrichment | None,
) -> PlaceEnrichmentResponse | None:
    if enrichment is None:
        return None

    return PlaceEnrichmentResponse(
        original_name=enrichment.original_name,
        normalized_name=enrichment.normalized_name,
        latitude=enrichment.latitude,
        longitude=enrichment.longitude,
        status=enrichment.status.value,
        source=enrichment.source,
        confidence=enrichment.confidence,
        comment=enrichment.comment,
    )


def _person_response(person: Person) -> PersonResponse:
    return PersonResponse(
        id=person.id,
        given_names=person.given_names,
        surname=person.surname,
        sex=person.sex.value,
        occupations=person.occupations,

        birth_date=get_birth_date(person),
        birth_year=get_birth_year(person),
        birth_place=get_birth_place(person),

        death_date=get_death_date(person),
        death_year=get_death_year(person),
        death_place=get_death_place(person),
    )

def _import_report_response(
    filename: str,
    report: ImportReport,
) -> ImportReportResponse:
    return ImportReportResponse(
        filename=filename,
        persons_count=report.persons_count,
        families_count=report.families_count,
        events_count=report.events_count,
        places_count=report.places_count,
        warnings=report.warnings,
        ignored_tags=[
            IgnoredTagResponse(
                tag=item.tag,
                record_id=item.record_id,
            )
            for item in report.ignored_tags
        ],
    )


def _configured_geocoder() -> Geocoder:
    api_key = os.environ.get("GEOAPIFY_API_KEY")
    return GeoapifyGeocoder(api_key) if api_key else UnavailableGeocoder()


app = create_app(
    place_enrichment_store=JsonPlaceEnrichmentStore(Path("data/place_enrichments.json")),
    geocoder=_configured_geocoder(),
)

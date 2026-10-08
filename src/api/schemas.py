from typing import Literal

from pydantic import BaseModel, ConfigDict


class PersonResponse(BaseModel):
    id: str
    given_names: str
    surname: str
    sex: str
    occupations: list[str]

    birth_date: str | None
    birth_year: str | None
    birth_place: str | None

    death_date: str | None
    death_year: str | None
    death_place: str | None
    
class AncestorResponse(BaseModel):
    person: PersonResponse
    generation: int


class HealthResponse(BaseModel):
    status: str
    persons_count: int
    families_count: int
    source: Literal["AUTO", "MANUAL"] | None
    filename: str | None
    load_error: str | None


class IgnoredTagResponse(BaseModel):
    tag: str
    record_id: str | None


class ImportReportResponse(BaseModel):
    filename: str
    persons_count: int
    families_count: int
    events_count: int
    places_count: int
    warnings: list[str]
    ignored_tags: list[IgnoredTagResponse]

class SosaOccurrenceResponse(BaseModel):
    sosa: int
    generation: int
    person: PersonResponse | None
    birth_place_original_name: str | None = None
    birth_place_display_name: str | None = None
    color_kind: str | None = None
    color_css: str | None = None
    color_reliable: bool | None = None

class PlaceEnrichmentResponse(BaseModel):
    original_name: str
    normalized_name: str | None
    latitude: float | None
    longitude: float | None
    status: str
    source: str | None
    confidence: float | None
    comment: str | None


class PlaceEnrichmentUpdateRequest(BaseModel):
    original_name: str
    normalized_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    comment: str | None = None


class PlaceEnrichmentValidationRequest(BaseModel):
    original_name: str


class PlaceInventoryResponse(BaseModel):
    original_name: str
    occurrences_count: int
    persons_count: int
    event_counts: dict[str, int]
    enrichment: PlaceEnrichmentResponse | None


class HistoricalPlaceProposalResponse(BaseModel):
    source_original_name: str
    historical_original_name: str
    historical_status: str
    historical_normalized_name: str | None
    latitude: float | None
    longitude: float | None
    score: int
    classification: str
    coordinate_reuse_reliability: str
    reasons: list[str]
    warnings: list[str]


class HistoricalPlaceReconciliationResponse(BaseModel):
    source_original_name: str
    classification: str
    proposals: list[HistoricalPlaceProposalResponse]


class HistoricalPlaceReuseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_original_name: str
    historical_original_name: str


class GeocodingCandidatesRequest(BaseModel):
    original_name: str
    query: str | None = None


class GeocodingCandidateResponse(BaseModel):
    selection_token: str
    provider: str
    provider_id: str
    display_name: str
    latitude: float
    longitude: float
    city: str | None
    postcode: str | None
    region: str | None
    country: str | None
    result_type: str | None


class GeocodingCandidateSelectionRequest(BaseModel):
    original_name: str
    candidate_token: str


class AncestorPlaceOccurrenceResponse(BaseModel):
    sosa: int
    generation: int
    person_id: str | None
    birth_place_original_name: str | None
    enrichment: PlaceEnrichmentResponse | None


class CombinedTreeOptionsResponse(BaseModel):
    root_person_id: str
    ancestor_generations: int
    descendant_generations: int
    show_siblings: bool


class TreePersonOccurrenceResponse(BaseModel):
    id: str
    person_id: str | None
    generation: int
    missing_person_id: str | None
    cycle_truncated: bool
    given_names: str | None
    surname: str | None
    sex: str | None


class PortraitReferenceResponse(BaseModel):
    url: str
    kind: str


class TreePersonCardResponse(BaseModel):
    occurrence_id: str
    person_id: str | None
    is_unknown: bool
    sex: str | None
    given_names: str | None
    display_given_name: str | None
    surname: str | None
    display_surname: str | None
    birth_date: str | None
    display_birth_date: str | None
    death_date: str | None
    display_death_date: str | None
    portrait: PortraitReferenceResponse


class TreeUnionPartnerResponse(BaseModel):
    occurrence_id: str
    role: str


class TreeUnionOccurrenceResponse(BaseModel):
    id: str
    family_id: str
    generation: int
    partners: list[TreeUnionPartnerResponse]


class TreeParentChildLinkResponse(BaseModel):
    union_occurrence_id: str
    child_occurrence_id: str


class TreeCentralFamilyCoreResponse(BaseModel):
    root_occurrence_id: str
    member_occurrence_ids: list[str]
    union_occurrence_ids: list[str]


class LayoutPointResponse(BaseModel):
    x: float
    y: float


class LayoutBoundsResponse(BaseModel):
    x: float
    y: float
    width: float
    height: float


class PersonLayoutNodeResponse(BaseModel):
    occurrence_id: str
    x: float
    y: float
    width: float
    height: float


class UnionLayoutNodeResponse(BaseModel):
    union_occurrence_id: str
    x: float
    y: float


class LayoutEdgeResponse(BaseModel):
    kind: str
    union_occurrence_id: str
    person_occurrence_id: str
    points: list[LayoutPointResponse]


class TreeLayoutResponse(BaseModel):
    person_nodes: list[PersonLayoutNodeResponse]
    union_nodes: list[UnionLayoutNodeResponse]
    edges: list[LayoutEdgeResponse]
    width: float
    height: float
    bounds: LayoutBoundsResponse


class MultipleParentFamiliesDiagnosticResponse(BaseModel):
    code: Literal["MULTIPLE_PARENT_FAMILIES"]
    person_id: str
    family_ids: list[str]
    selected_family_id: str


class CycleTruncatedDiagnosticResponse(BaseModel):
    code: Literal["CYCLE_TRUNCATED"]
    person_id: str
    occurrence_id: str
    traversal: str
    path_person_ids: list[str]


class MissingPersonReferenceDiagnosticResponse(BaseModel):
    code: Literal["MISSING_PERSON_REFERENCE"]
    family_id: str
    missing_person_id: str
    role: str
    occurrence_id: str


TreeDiagnosticResponse = (
    MultipleParentFamiliesDiagnosticResponse
    | CycleTruncatedDiagnosticResponse
    | MissingPersonReferenceDiagnosticResponse
)


class CombinedTreeResponse(BaseModel):
    root_occurrence_id: str
    options: CombinedTreeOptionsResponse
    central_family_core: TreeCentralFamilyCoreResponse
    person_occurrences: list[TreePersonOccurrenceResponse]
    person_cards: list[TreePersonCardResponse]
    union_occurrences: list[TreeUnionOccurrenceResponse]
    parent_child_links: list[TreeParentChildLinkResponse]
    diagnostics: list[TreeDiagnosticResponse]
    layout: TreeLayoutResponse

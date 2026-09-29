from pydantic import BaseModel


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


class PlaceInventoryResponse(BaseModel):
    original_name: str
    occurrences_count: int
    persons_count: int
    event_counts: dict[str, int]
    enrichment: PlaceEnrichmentResponse | None

from pydantic import BaseModel


class PersonResponse(BaseModel):
    id: str
    given_names: str
    surname: str
    sex: str
    occupations: list[str]


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
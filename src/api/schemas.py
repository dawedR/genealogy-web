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
from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Query, Request

from src.api.schemas import (
    AncestorResponse,
    HealthResponse,
    PersonResponse,
)
from src.domain.models import Genealogy, Person
from src.services.ancestry import get_ancestors
from src.services.search import search_people


def create_app(genealogy: Genealogy | None = None) -> FastAPI:
    initial_genealogy = genealogy or Genealogy()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.genealogy = initial_genealogy
        yield

    app = FastAPI(
        title="Genealogy Web",
        version="0.1.0",
        lifespan=lifespan,
    )

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

    return app


def _genealogy(request: Request) -> Genealogy:
    return request.app.state.genealogy


def _person_response(person: Person) -> PersonResponse:
    return PersonResponse(
        id=person.id,
        given_names=person.given_names,
        surname=person.surname,
        sex=person.sex.value,
        occupations=person.occupations,
    )


app = create_app()
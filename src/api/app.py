from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)

from src.api.schemas import (
    AncestorResponse,
    HealthResponse,
    IgnoredTagResponse,
    ImportReportResponse,
    PersonResponse,
)
from src.domain.models import Genealogy, ImportReport, Person
from src.gedcom.importer import import_gedcom
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


app = create_app()
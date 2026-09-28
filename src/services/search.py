from __future__ import annotations

import re
import unicodedata

from src.domain.models import Genealogy, Person


def search_people(
    genealogy: Genealogy,
    query: str,
    limit: int = 20,
) -> list[Person]:
    """Search people by name and optional birth year."""

    if limit <= 0:
        return []

    normalized_query = _normalize(query)

    if not normalized_query:
        return []

    query_year = _extract_year(normalized_query)

    name_query = normalized_query

    if query_year is not None:
        name_query = re.sub(
            rf"\b{query_year}\b",
            "",
            normalized_query,
        ).strip()

    matches: list[Person] = []

    for person in genealogy.persons.values():
        full_name = f"{person.given_names} {person.surname}"
        normalized_name = _normalize(full_name)

        if name_query and name_query not in normalized_name:
            continue

        if query_year is not None:
            birth_year = get_birth_year(person)

            if birth_year != query_year:
                continue

        matches.append(person)

    matches.sort(
        key=lambda person: (
            _normalize(person.surname),
            _normalize(person.given_names),
            get_birth_year(person) or "",
            person.id,
        )
    )

    return matches[:limit]


def get_birth_date(person: Person) -> str | None:
    event = get_event(person, "BIRT")

    if event is None or event.date is None:
        return None

    return event.date.value

def get_event(person: Person, event_type: str):
    for event in person.events:
        if event.type == event_type:
            return event

    return None


def get_birth_place(person: Person) -> str | None:
    event = get_event(person, "BIRT")

    if event is None or event.place is None:
        return None

    return event.place.original_name


def get_death_date(person: Person) -> str | None:
    event = get_event(person, "DEAT")

    if event is None or event.date is None:
        return None

    return event.date.value


def get_death_year(person: Person) -> str | None:
    death_date = get_death_date(person)

    if death_date is None:
        return None

    match = re.search(
        r"\b(\d{4})\b",
        death_date,
    )

    return match.group(1) if match else None


def get_death_place(person: Person) -> str | None:
    event = get_event(person, "DEAT")

    if event is None or event.place is None:
        return None

    return event.place.original_name


def get_birth_year(person: Person) -> str | None:
    """Extract a four-digit year from the birth date."""

    birth_date = get_birth_date(person)

    if birth_date is None:
        return None

    match = re.search(
        r"\b(\d{4})\b",
        birth_date,
    )

    if match is None:
        return None

    return match.group(1)


def _extract_year(value: str) -> str | None:
    match = re.search(
        r"\b(\d{4})\b",
        value,
    )

    if match is None:
        return None

    return match.group(1)


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)

    return "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    ).casefold().strip()
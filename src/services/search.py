from __future__ import annotations

import unicodedata

from src.domain.models import Genealogy, Person


def search_people(
    genealogy: Genealogy,
    query: str,
    limit: int = 20,
) -> list[Person]:
    """Search people by given names and surname."""

    if limit <= 0:
        return []

    normalized_query = _normalize(query)

    if not normalized_query:
        return []

    matches = []

    for person in genealogy.persons.values():
        full_name = f"{person.given_names} {person.surname}"
        normalized_name = _normalize(full_name)

        if normalized_query in normalized_name:
            matches.append(person)

    matches.sort(
        key=lambda person: (
            _normalize(person.surname),
            _normalize(person.given_names),
            person.id,
        )
    )

    return matches[:limit]


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)

    return "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    ).casefold().strip()
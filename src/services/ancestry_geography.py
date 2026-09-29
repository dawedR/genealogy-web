from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.domain.models import Genealogy, PlaceEnrichment
from src.services.search import get_birth_place
from src.services.sosa import build_sosa_ancestry


@dataclass(frozen=True)
class AncestorPlaceOccurrence:
    """Birth-place information for one Sosa occurrence."""

    sosa: int
    generation: int
    person_id: str | None
    birth_place_original_name: str | None
    enrichment: PlaceEnrichment | None


def build_ancestry_geography(
    genealogy: Genealogy,
    root_person_id: str,
    generations: int,
    enrichments: Mapping[str, PlaceEnrichment],
) -> list[AncestorPlaceOccurrence]:
    """Project all Sosa occurrences onto their birth places.

    Unknown positions and repeated people remain distinct occurrences.
    """

    occurrences = build_sosa_ancestry(
        genealogy,
        root_person_id,
        generations,
    )

    result: list[AncestorPlaceOccurrence] = []

    for occurrence in occurrences:
        person = (
            genealogy.persons.get(occurrence.person_id)
            if occurrence.person_id is not None
            else None
        )
        birth_place_original_name = (
            get_birth_place(person) if person is not None else None
        )

        result.append(
            AncestorPlaceOccurrence(
                sosa=occurrence.sosa,
                generation=occurrence.generation,
                person_id=occurrence.person_id,
                birth_place_original_name=birth_place_original_name,
                enrichment=(
                    enrichments.get(birth_place_original_name)
                    if birth_place_original_name is not None
                    else None
                ),
            )
        )

    return result

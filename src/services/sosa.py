from __future__ import annotations

from dataclasses import dataclass

from src.domain.models import Genealogy, Person

@dataclass(frozen=True)
class AncestorOccurrence:
    person_id: str | None
    sosa: int
    generation: int


def build_sosa_ancestry(
    genealogy: Genealogy,
    root_person_id: str,
    generations: int,
) -> list[AncestorOccurrence]:
    """Build a complete Sosa ancestry up to the requested generation.

    Generation 0 contains Sosa 1.

    Missing ancestors are represented explicitly by occurrences whose
    person_id is None. This preserves the Sosa structure.

    A person may appear in several occurrences with different Sosa
    numbers in case of pedigree collapse (implex).
    """

    if root_person_id not in genealogy.persons:
        raise KeyError(
            f"Unknown person: {root_person_id}"
        )

    if generations < 0:
        raise ValueError(
            "generations must be zero or greater"
        )

    occurrences = [
        AncestorOccurrence(
            person_id=root_person_id,
            sosa=1,
            generation=0,
        )
    ]

    current = occurrences.copy()

    for generation in range(1, generations + 1):
        next_generation: list[AncestorOccurrence] = []

        for occurrence in current:
            father, mother = _get_father_and_mother(
                genealogy,
                occurrence.person_id,
            )

            next_generation.append(
                AncestorOccurrence(
                    person_id=(
                        father.id
                        if father is not None
                        else None
                    ),
                    sosa=occurrence.sosa * 2,
                    generation=generation,
                )
            )

            next_generation.append(
                AncestorOccurrence(
                    person_id=(
                        mother.id
                        if mother is not None
                        else None
                    ),
                    sosa=occurrence.sosa * 2 + 1,
                    generation=generation,
                )
            )

        occurrences.extend(next_generation)
        current = next_generation

    return occurrences


def _get_father_and_mother(
    genealogy: Genealogy,
    person_id: str | None,
) -> tuple[Person | None, Person | None]:
    if person_id is None:
        return None, None

    family = next(
        (
            family
            for family in genealogy.families.values()
            if person_id in family.children
        ),
        None,
    )

    if family is None:
        return None, None

    father = (
        genealogy.persons.get(family.father_id)
        if family.father_id is not None
        else None
    )

    mother = (
        genealogy.persons.get(family.mother_id)
        if family.mother_id is not None
        else None
    )

    return father, mother
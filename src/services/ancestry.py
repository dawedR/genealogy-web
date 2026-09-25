from __future__ import annotations

from dataclasses import dataclass

from src.domain.models import Genealogy, Person, Sex


@dataclass(frozen=True)
class Ancestor:
    person: Person
    generation: int


def get_parents(
    genealogy: Genealogy,
    person_id: str,
) -> list[Person]:
    """Return the known parents of a person.

    Parents are inferred from families where the person appears as a child.
    Father is returned before mother when sex information makes that possible.
    """

    parent_ids: list[str] = []

    for family in genealogy.families.values():
        if person_id not in family.children:
            continue

        for parent_id in family.partners:
            if parent_id not in parent_ids:
                parent_ids.append(parent_id)

    parents = [
        genealogy.persons[parent_id]
        for parent_id in parent_ids
        if parent_id in genealogy.persons
    ]

    return sorted(parents, key=_parent_sort_key)


def get_ancestors(
    genealogy: Genealogy,
    person_id: str,
    generations: int | None = None,
) -> list[Ancestor]:
    """Return the root person and their known ancestors.

    Generation 0 is the root person.
    Generation 1 contains their parents, generation 2 their grandparents, etc.

    A person is returned only once, at the nearest generation at which they
    are encountered. This also prevents malformed cyclic data from causing
    infinite recursion.
    """

    if person_id not in genealogy.persons:
        raise KeyError(f"Unknown person: {person_id}")

    if generations is not None and generations < 0:
        raise ValueError("generations must be zero or greater")

    result: list[Ancestor] = []
    visited: set[str] = set()

    current_generation = [genealogy.persons[person_id]]
    generation = 0

    while current_generation:
        next_generation: list[Person] = []

        for person in current_generation:
            if person.id in visited:
                continue

            visited.add(person.id)

            result.append(
                Ancestor(
                    person=person,
                    generation=generation,
                )
            )

            if generations is not None and generation >= generations:
                continue

            for parent in get_parents(genealogy, person.id):
                if parent.id not in visited:
                    next_generation.append(parent)

        if generations is not None and generation >= generations:
            break

        current_generation = _deduplicate_people(next_generation)
        generation += 1

    return result


def _parent_sort_key(person: Person) -> tuple[int, str]:
    if person.sex == Sex.MALE:
        sex_order = 0
    elif person.sex == Sex.FEMALE:
        sex_order = 1
    else:
        sex_order = 2

    return sex_order, person.id


def _deduplicate_people(people: list[Person]) -> list[Person]:
    result: list[Person] = []
    seen: set[str] = set()

    for person in people:
        if person.id not in seen:
            seen.add(person.id)
            result.append(person)

    return result

def format_ancestry(ancestors: list[Ancestor]) -> str:
    """Render an ancestry result as readable plain text."""

    lines: list[str] = []

    for ancestor in ancestors:
        person = ancestor.person

        name = " ".join(
            part
            for part in (
                person.given_names,
                person.surname,
            )
            if part
        )

        indent = "  " * ancestor.generation

        lines.append(
            f"{indent}G{ancestor.generation} "
            f"{person.id} {name}".rstrip()
        )

    return "\n".join(lines)
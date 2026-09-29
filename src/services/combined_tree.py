"""Renderer-independent projection for a combined family tree."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.domain.models import Family, Genealogy


@dataclass(frozen=True)
class CombinedTreeOptions:
    """Selection limits for one combined-tree projection."""

    root_person_id: str
    ancestor_generations: int
    descendant_generations: int

    def __post_init__(self) -> None:
        if self.ancestor_generations < 0:
            raise ValueError("ancestor_generations must be zero or greater")
        if self.descendant_generations < 0:
            raise ValueError("descendant_generations must be zero or greater")


@dataclass(frozen=True)
class TreePersonOccurrence:
    """One selected position, optionally occupied by an unknown person."""

    id: str
    person_id: str | None
    generation: int


class TreeUnionPartnerRole(str, Enum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    UNSPECIFIED = "UNSPECIFIED"


@dataclass(frozen=True)
class TreeUnionPartner:
    occurrence_id: str
    role: TreeUnionPartnerRole


@dataclass(frozen=True)
class TreeUnionOccurrence:
    """One occurrence of an existing GEDCOM family."""

    id: str
    family_id: str
    generation: int
    partners: tuple[TreeUnionPartner, ...]


@dataclass(frozen=True)
class TreeParentChildLink:
    union_occurrence_id: str
    child_occurrence_id: str


class TreeDiagnosticCode(str, Enum):
    MULTIPLE_PARENT_FAMILIES = "MULTIPLE_PARENT_FAMILIES"


@dataclass(frozen=True)
class TreeDiagnostic:
    code: TreeDiagnosticCode
    person_id: str
    family_ids: tuple[str, ...]
    selected_family_id: str


@dataclass(frozen=True)
class CombinedTree:
    root_occurrence_id: str
    options: CombinedTreeOptions
    person_occurrences: tuple[TreePersonOccurrence, ...]
    union_occurrences: tuple[TreeUnionOccurrence, ...]
    parent_child_links: tuple[TreeParentChildLink, ...]
    diagnostics: tuple[TreeDiagnostic, ...]


@dataclass(frozen=True)
class _CanonicalParentFamilySelection:
    family: Family | None
    candidate_family_ids: tuple[str, ...]


def select_canonical_parent_family(
    genealogy: Genealogy,
    person_id: str,
) -> _CanonicalParentFamilySelection:
    """Select a parent family without claiming to preserve GEDCOM FAMC order.

    The current domain model does not retain the order of FAMC references on
    an individual. When several families contain the same child, the V3
    fallback is therefore explicitly the lexicographically first Family.id.
    """

    candidates = sorted(
        (
            family
            for family in genealogy.families.values()
            if person_id in family.children
        ),
        key=lambda family: family.id,
    )

    return _CanonicalParentFamilySelection(
        family=candidates[0] if candidates else None,
        candidate_family_ids=tuple(family.id for family in candidates),
    )


def build_combined_tree(
    genealogy: Genealogy,
    options: CombinedTreeOptions,
) -> CombinedTree:
    """Select a renderer-independent combined tree around one root person.

    This initial V3 projection includes ancestry and the root person's own
    descendant families. It deliberately does not yet expand siblings,
    resolve cycles, or add presentation data such as portraits and colours.
    """

    if options.root_person_id not in genealogy.persons:
        raise KeyError(f"Unknown person: {options.root_person_id}")

    people: list[TreePersonOccurrence] = []
    unions: list[TreeUnionOccurrence] = []
    parent_child_links: list[TreeParentChildLink] = []
    diagnostics: list[TreeDiagnostic] = []

    root = TreePersonOccurrence(
        id="person:root",
        person_id=options.root_person_id,
        generation=0,
    )
    people.append(root)

    def add_person(
        occurrence_id: str,
        person_id: str | None,
        generation: int,
    ) -> TreePersonOccurrence:
        occurrence = TreePersonOccurrence(
            id=occurrence_id,
            person_id=person_id,
            generation=generation,
        )
        people.append(occurrence)
        return occurrence

    def add_parent_ancestry(
        child: TreePersonOccurrence,
        depth: int,
    ) -> None:
        if depth >= options.ancestor_generations or child.person_id is None:
            return

        selection = select_canonical_parent_family(genealogy, child.person_id)
        family = selection.family
        if family is None:
            return

        if len(selection.candidate_family_ids) > 1:
            diagnostics.append(
                TreeDiagnostic(
                    code=TreeDiagnosticCode.MULTIPLE_PARENT_FAMILIES,
                    person_id=child.person_id,
                    family_ids=selection.candidate_family_ids,
                    selected_family_id=family.id,
                )
            )

        union_id = f"union:{child.id}:parents:{family.id}"
        father = add_person(
            f"person:{union_id}:father",
            family.father_id,
            child.generation - 1,
        )
        mother = add_person(
            f"person:{union_id}:mother",
            family.mother_id,
            child.generation - 1,
        )
        unions.append(
            TreeUnionOccurrence(
                id=union_id,
                family_id=family.id,
                generation=child.generation - 1,
                partners=(
                    TreeUnionPartner(father.id, TreeUnionPartnerRole.FATHER),
                    TreeUnionPartner(mother.id, TreeUnionPartnerRole.MOTHER),
                ),
            )
        )
        parent_child_links.append(
            TreeParentChildLink(
                union_occurrence_id=union_id,
                child_occurrence_id=child.id,
            )
        )

        add_parent_ancestry(father, depth + 1)
        add_parent_ancestry(mother, depth + 1)

    def add_descendant_families(
        person: TreePersonOccurrence,
        depth: int,
    ) -> None:
        if person.person_id is None:
            return

        families = sorted(
            (
                family
                for family in genealogy.families.values()
                if person.person_id in family.partners
            ),
            key=lambda family: family.id,
        )

        for family in families:
            union_id = f"union:{person.id}:family:{family.id}"
            partners: list[TreeUnionPartner] = []
            used_current_person = False

            for index, partner_id in enumerate(family.partners):
                if partner_id == person.person_id and not used_current_person:
                    partner_occurrence = person
                    used_current_person = True
                else:
                    partner_occurrence = add_person(
                        f"person:{union_id}:partner:{index}",
                        partner_id,
                        person.generation,
                    )

                partners.append(
                    TreeUnionPartner(
                        occurrence_id=partner_occurrence.id,
                        role=_partner_role(family, partner_id),
                    )
                )

            unions.append(
                TreeUnionOccurrence(
                    id=union_id,
                    family_id=family.id,
                    generation=person.generation,
                    partners=tuple(partners),
                )
            )

            if depth >= options.descendant_generations:
                continue

            for index, child_id in enumerate(family.children):
                child = add_person(
                    f"person:{union_id}:child:{index}",
                    child_id,
                    person.generation + 1,
                )
                parent_child_links.append(
                    TreeParentChildLink(
                        union_occurrence_id=union_id,
                        child_occurrence_id=child.id,
                    )
                )
                add_descendant_families(child, depth + 1)

    add_parent_ancestry(root, depth=0)
    add_descendant_families(root, depth=0)

    return CombinedTree(
        root_occurrence_id=root.id,
        options=options,
        person_occurrences=tuple(people),
        union_occurrences=tuple(unions),
        parent_child_links=tuple(parent_child_links),
        diagnostics=tuple(diagnostics),
    )


def _partner_role(family: Family, person_id: str) -> TreeUnionPartnerRole:
    if person_id == family.father_id:
        return TreeUnionPartnerRole.FATHER
    if person_id == family.mother_id:
        return TreeUnionPartnerRole.MOTHER
    return TreeUnionPartnerRole.UNSPECIFIED

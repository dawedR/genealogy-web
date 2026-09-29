"""Renderer-independent projection for a combined family tree."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias

from src.domain.models import Family, Genealogy


@dataclass(frozen=True)
class CombinedTreeOptions:
    """Selection limits for one combined-tree projection."""

    root_person_id: str
    ancestor_generations: int
    descendant_generations: int
    show_siblings: bool = True

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
    missing_person_id: str | None = None
    cycle_truncated: bool = False


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
    CYCLE_TRUNCATED = "CYCLE_TRUNCATED"
    MISSING_PERSON_REFERENCE = "MISSING_PERSON_REFERENCE"


class TreeTraversal(str, Enum):
    ANCESTRY = "ANCESTRY"
    DESCENT = "DESCENT"


class TreeReferenceRole(str, Enum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    PARTNER = "PARTNER"
    CHILD = "CHILD"


@dataclass(frozen=True)
class MultipleParentFamiliesDiagnostic:
    person_id: str
    family_ids: tuple[str, ...]
    selected_family_id: str
    code: TreeDiagnosticCode = field(
        default=TreeDiagnosticCode.MULTIPLE_PARENT_FAMILIES,
        init=False,
    )


@dataclass(frozen=True)
class CycleTruncatedDiagnostic:
    person_id: str
    occurrence_id: str
    traversal: TreeTraversal
    path_person_ids: tuple[str, ...]
    code: TreeDiagnosticCode = field(
        default=TreeDiagnosticCode.CYCLE_TRUNCATED,
        init=False,
    )


@dataclass(frozen=True)
class MissingPersonReferenceDiagnostic:
    family_id: str
    missing_person_id: str
    role: TreeReferenceRole
    occurrence_id: str
    code: TreeDiagnosticCode = field(
        default=TreeDiagnosticCode.MISSING_PERSON_REFERENCE,
        init=False,
    )


TreeDiagnostic: TypeAlias = (
    MultipleParentFamiliesDiagnostic
    | CycleTruncatedDiagnostic
    | MissingPersonReferenceDiagnostic
)


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
    """Select a renderer-independent combined tree around one root person."""

    if options.root_person_id not in genealogy.persons:
        raise KeyError(f"Unknown person: {options.root_person_id}")

    people: list[TreePersonOccurrence] = []
    unions: list[TreeUnionOccurrence] = []
    parent_child_links: list[TreeParentChildLink] = []
    diagnostics: list[TreeDiagnostic] = []
    parent_selections: dict[str, _CanonicalParentFamilySelection] = {}
    diagnostic_person_ids: set[str] = set()
    parent_union_ids: dict[str, str] = {}

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
        *,
        missing_person_id: str | None = None,
        cycle_truncated: bool = False,
    ) -> TreePersonOccurrence:
        occurrence = TreePersonOccurrence(
            id=occurrence_id,
            person_id=person_id,
            generation=generation,
            missing_person_id=missing_person_id,
            cycle_truncated=cycle_truncated,
        )
        people.append(occurrence)
        return occurrence

    def add_family_reference(
        occurrence_id: str,
        referenced_person_id: str | None,
        generation: int,
        *,
        family_id: str,
        role: TreeReferenceRole,
        traversal: TreeTraversal,
        path_person_ids: tuple[str, ...],
    ) -> TreePersonOccurrence:
        if referenced_person_id is None:
            return add_person(occurrence_id, None, generation)

        if referenced_person_id not in genealogy.persons:
            occurrence = add_person(
                occurrence_id,
                None,
                generation,
                missing_person_id=referenced_person_id,
            )
            diagnostics.append(
                MissingPersonReferenceDiagnostic(
                    family_id=family_id,
                    missing_person_id=referenced_person_id,
                    role=role,
                    occurrence_id=occurrence.id,
                )
            )
            return occurrence

        cycle_truncated = referenced_person_id in path_person_ids
        occurrence = add_person(
            occurrence_id,
            referenced_person_id,
            generation,
            cycle_truncated=cycle_truncated,
        )
        if cycle_truncated:
            diagnostics.append(
                CycleTruncatedDiagnostic(
                    person_id=referenced_person_id,
                    occurrence_id=occurrence.id,
                    traversal=traversal,
                    path_person_ids=path_person_ids + (referenced_person_id,),
                )
            )
        return occurrence

    def canonical_parent_family_for(
        person_id: str,
    ) -> _CanonicalParentFamilySelection:
        selection = parent_selections.get(person_id)
        if selection is None:
            selection = select_canonical_parent_family(genealogy, person_id)
            parent_selections[person_id] = selection
        if (
            len(selection.candidate_family_ids) > 1
            and person_id not in diagnostic_person_ids
            and selection.family is not None
        ):
            diagnostics.append(
                MultipleParentFamiliesDiagnostic(
                    person_id=person_id,
                    family_ids=selection.candidate_family_ids,
                    selected_family_id=selection.family.id,
                )
            )
            diagnostic_person_ids.add(person_id)
        return selection

    def add_parent_ancestry(
        child: TreePersonOccurrence,
        depth: int,
        path_person_ids: tuple[str, ...],
    ) -> None:
        if (
            depth >= options.ancestor_generations
            or child.person_id is None
            or child.cycle_truncated
        ):
            return

        family = canonical_parent_family_for(child.person_id).family
        if family is None:
            return

        union_id = f"union:{child.id}:parents:{family.id}"
        father = add_family_reference(
            f"person:{union_id}:father",
            family.father_id,
            child.generation - 1,
            family_id=family.id,
            role=TreeReferenceRole.FATHER,
            traversal=TreeTraversal.ANCESTRY,
            path_person_ids=path_person_ids,
        )
        mother = add_family_reference(
            f"person:{union_id}:mother",
            family.mother_id,
            child.generation - 1,
            family_id=family.id,
            role=TreeReferenceRole.MOTHER,
            traversal=TreeTraversal.ANCESTRY,
            path_person_ids=path_person_ids,
        )
        parent_union_ids[child.id] = union_id
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

        if father.person_id is not None:
            add_parent_ancestry(
                father,
                depth + 1,
                path_person_ids + (father.person_id,),
            )
        if mother.person_id is not None:
            add_parent_ancestry(
                mother,
                depth + 1,
                path_person_ids + (mother.person_id,),
            )

    def add_descendant_families(
        person: TreePersonOccurrence,
        depth: int,
        path_person_ids: tuple[str, ...],
    ) -> None:
        if (
            person.person_id is None
            or person.cycle_truncated
            or depth >= options.descendant_generations
        ):
            return

        for family in _partner_families(genealogy, person.person_id):
            union_id = f"union:{person.id}:family:{family.id}"
            partners: list[TreeUnionPartner] = []
            used_current_person = False

            for index, partner_id in enumerate(family.partners):
                if partner_id == person.person_id and not used_current_person:
                    partner_occurrence = person
                    used_current_person = True
                else:
                    partner_occurrence = add_family_reference(
                        f"person:{union_id}:partner:{index}",
                        partner_id,
                        person.generation,
                        family_id=family.id,
                        role=TreeReferenceRole.PARTNER,
                        traversal=TreeTraversal.DESCENT,
                        path_person_ids=path_person_ids,
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

            for index, child_id in enumerate(family.children):
                child = add_family_reference(
                    f"person:{union_id}:child:{index}",
                    child_id,
                    person.generation + 1,
                    family_id=family.id,
                    role=TreeReferenceRole.CHILD,
                    traversal=TreeTraversal.DESCENT,
                    path_person_ids=path_person_ids,
                )
                parent_child_links.append(
                    TreeParentChildLink(
                        union_occurrence_id=union_id,
                        child_occurrence_id=child.id,
                    )
                )
                if child.person_id is not None:
                    add_descendant_families(
                        child,
                        depth + 1,
                        path_person_ids + (child.person_id,),
                    )

    add_parent_ancestry(
        root,
        depth=0,
        path_person_ids=(root.person_id,),
    )

    descendant_roots = [root]
    if options.show_siblings:
        root_parent_family = canonical_parent_family_for(root.person_id).family
        if root_parent_family is not None:
            descendant_roots = []
            parent_union_id = parent_union_ids.get(root.id)
            for index, child_id in enumerate(root_parent_family.children):
                if child_id == root.person_id:
                    sibling = root
                else:
                    sibling = add_family_reference(
                        (
                            "person:root:parent-family:"
                            f"{root_parent_family.id}:child:{index}"
                        ),
                        child_id,
                        0,
                        family_id=root_parent_family.id,
                        role=TreeReferenceRole.CHILD,
                        traversal=TreeTraversal.DESCENT,
                        path_person_ids=(root.person_id,),
                    )
                if parent_union_id is not None and sibling.id != root.id:
                    parent_child_links.append(
                        TreeParentChildLink(
                            union_occurrence_id=parent_union_id,
                            child_occurrence_id=sibling.id,
                        )
                    )
                descendant_roots.append(sibling)

    for descendant_root in descendant_roots:
        if descendant_root.person_id is not None:
            add_descendant_families(
                descendant_root,
                depth=0,
                path_person_ids=(descendant_root.person_id,),
            )

    return CombinedTree(
        root_occurrence_id=root.id,
        options=options,
        person_occurrences=tuple(people),
        union_occurrences=tuple(unions),
        parent_child_links=tuple(parent_child_links),
        diagnostics=tuple(diagnostics),
    )


def _partner_families(genealogy: Genealogy, person_id: str) -> list[Family]:
    """Return a person's partner families in the V3 deterministic fallback order.

    The current domain model does not preserve the source order of FAMS
    references. Family.id is therefore used only as a stable fallback, never
    as a claim about GEDCOM ordering.
    """

    return sorted(
        (
            family
            for family in genealogy.families.values()
            if person_id in family.partners
        ),
        key=lambda family: family.id,
    )


def _partner_role(family: Family, person_id: str) -> TreeUnionPartnerRole:
    if person_id == family.father_id:
        return TreeUnionPartnerRole.FATHER
    if person_id == family.mother_id:
        return TreeUnionPartnerRole.MOTHER
    return TreeUnionPartnerRole.UNSPECIFIED

"""Adversarial, data-independent geometry checks for synthetic family trees.

These tests deliberately do not adjust TreeLayout to accommodate a fixture.
"""

from __future__ import annotations

import pytest

from src.domain.models import Family, Genealogy, Person
from src.services.combined_tree import CombinedTreeOptions, build_combined_tree
from src.services.tree_layout import (
    LayoutEdgeKind,
    TreeLayoutConfiguration,
    layout_combined_tree,
)


class FamilyBuilder:
    def __init__(self) -> None:
        self.people: dict[str, Person] = {}
        self.families: dict[str, Family] = {}

    def person(self, name: str) -> str:
        identifier = f"@{name}@"
        self.people[identifier] = Person(id=identifier)
        return identifier

    def family(self, name: str, partners: list[str], children: list[str]) -> None:
        self.families[f"@{name}@"] = Family(
            id=f"@{name}@",
            partners=partners,
            father_id=partners[0] if partners else None,
            mother_id=partners[1] if len(partners) > 1 else None,
            children=children,
        )

    def ancestor_chain(self, child: str, prefix: str, depth: int) -> None:
        for level in range(depth):
            father = self.person(f"{prefix}_father_{level}")
            mother = self.person(f"{prefix}_mother_{level}")
            self.family(f"{prefix}_parents_{level}", [father, mother], [child])
            child = father

    def genealogy(self) -> Genealogy:
        return Genealogy(persons=self.people, families=self.families)


def scenario(name: str) -> tuple[Genealogy, CombinedTreeOptions]:
    b = FamilyBuilder()
    root = b.person("root")
    asc = desc = 0
    siblings = False

    if name == "root_without_union":
        pass
    elif name in ("one_union_one_child", "one_union_ten_children"):
        spouse = b.person("spouse")
        count = 1 if name == "one_union_one_child" else 10
        children = [b.person(f"child_{i}") for i in range(count)]
        b.family("union", [root, spouse], children)
        desc = 1
    elif name == "three_unbalanced_unions":
        for i, count in enumerate((1, 10, 2)):
            spouse = b.person(f"spouse_{i}")
            children = [b.person(f"child_{i}_{j}") for j in range(count)]
            b.family(f"union_{i}", [root, spouse], children)
            if i == 0:
                other = b.person("grandchild_parent")
                grandchild = b.person("grandchild")
                b.family("next_generation", [children[0], other], [grandchild])
        desc = 2
    elif name == "five_unions":
        for i in range(5):
            spouse = b.person(f"spouse_{i}")
            children = [b.person(f"child_{i}")] if i != 2 else []
            b.family(f"union_{i}", [root, spouse], children)
        desc = 1
    elif name in ("root_deep_ancestry", "all_core_deep_ancestry"):
        b.ancestor_chain(root, "root", 5)
        for i in range(3 if name == "all_core_deep_ancestry" else 1):
            spouse = b.person(f"spouse_{i}")
            b.family(f"union_{i}", [root, spouse], [])
            if name == "all_core_deep_ancestry":
                b.ancestor_chain(spouse, f"spouse_{i}", 5)
        asc = 5
    elif name == "asc_five_desc_five":
        spouse = b.person("spouse")
        b.ancestor_chain(root, "root", 5)
        b.ancestor_chain(spouse, "spouse", 5)
        previous = b.person("desc_1")
        b.family("central", [root, spouse], [previous])
        for level in range(2, 6):
            next_person = b.person(f"desc_{level}")
            partner = b.person(f"desc_spouse_{level}")
            b.family(f"desc_union_{level}", [previous, partner], [next_person])
            previous = next_person
        asc = desc = 5
    elif name == "multigeneration_remarriages":
        current = root
        for level in range(3):
            for union_index in range(2):
                spouse = b.person(f"spouse_{level}_{union_index}")
                child = b.person(f"child_{level}_{union_index}")
                b.family(f"union_{level}_{union_index}", [current, spouse], [child])
                if union_index == 0:
                    next_current = child
            current = next_current
        desc = 3
    elif name == "wide_siblings":
        father = b.person("father")
        mother = b.person("mother")
        siblings_ids = [root] + [b.person(f"sibling_{i}") for i in range(9)]
        b.family("parents", [father, mother], siblings_ids)
        for i, sibling in enumerate(siblings_ids):
            spouse = b.person(f"spouse_{i}")
            child = b.person(f"child_{i}")
            b.family(f"sibling_union_{i}", [sibling, spouse], [child])
        asc = desc = 1
        siblings = True
    elif name == "implex":
        father = b.person("father")
        mother = b.person("mother")
        shared = b.person("shared_grandparent")
        other_father = b.person("other_father")
        other_mother = b.person("other_mother")
        b.family("root_parents", [father, mother], [root])
        b.family("father_parents", [shared, other_father], [father])
        b.family("mother_parents", [shared, other_mother], [mother])
        asc = 2
    elif name == "truncated_cycle":
        spouse = b.person("spouse")
        child = b.person("child")
        next_spouse = b.person("next_spouse")
        b.family("central", [root, spouse], [child])
        b.family("cyclic", [child, next_spouse], [root])
        desc = 3
    else:
        raise AssertionError(name)

    return b.genealogy(), CombinedTreeOptions(root, asc, desc, siblings)


SCENARIOS = (
    "root_without_union",
    "one_union_one_child",
    "one_union_ten_children",
    "three_unbalanced_unions",
    "five_unions",
    "root_deep_ancestry",
    "all_core_deep_ancestry",
    "asc_five_desc_five",
    "multigeneration_remarriages",
    "wide_siblings",
    "implex",
    "truncated_cycle",
)


def segment_crosses_card_interior(a, b, card) -> bool:
    left, right = card.x, card.x + card.width
    top, bottom = card.y, card.y + card.height
    if a.x == b.x:
        return left < a.x < right and max(min(a.y, b.y), top) < min(max(a.y, b.y), bottom)
    if a.y == b.y:
        return top < a.y < bottom and max(min(a.x, b.x), left) < min(max(a.x, b.x), right)
    return False


@pytest.mark.parametrize("name", SCENARIOS)
def test_synthetic_layout_geometry(name: str) -> None:
    genealogy, options = scenario(name)
    tree = build_combined_tree(genealogy, options)
    layout = layout_combined_tree(tree)
    print(
        f"{name}: {layout.width:g}x{layout.height:g}; "
        f"persons={len(layout.person_nodes)}, unions={len(layout.union_nodes)}, "
        f"edges={len(layout.edges)}"
    )

    people = {node.occurrence_id: node for node in layout.person_nodes}
    unions = {node.union_occurrence_id: node for node in layout.union_nodes}
    assert len(people) == len(layout.person_nodes)
    assert len(unions) == len(layout.union_nodes)
    assert set(people) == {item.id for item in tree.person_occurrences}
    assert set(unions) == {item.id for item in tree.union_occurrences}

    core = tree.central_family_core
    assert core.member_occurrence_ids[0] == tree.root_occurrence_id
    assert len(set(core.member_occurrence_ids)) == len(core.member_occurrence_ids)
    assert all(item in people for item in core.member_occurrence_ids)
    assert all(item in unions for item in core.union_occurrence_ids)
    assert sum(node.occurrence_id == tree.root_occurrence_id for node in layout.person_nodes) == 1

    for index, first in enumerate(layout.person_nodes):
        for second in layout.person_nodes[index + 1 :]:
            assert (
                first.x + first.width <= second.x
                or second.x + second.width <= first.x
                or first.y + first.height <= second.y
                or second.y + second.height <= first.y
            ), f"overlap: {first.occurrence_id} / {second.occurrence_id}"

    expected_edges = {
        (LayoutEdgeKind.PARTNER, union.id, partner.occurrence_id)
        for union in tree.union_occurrences
        for partner in union.partners
    } | {
        (LayoutEdgeKind.PARENT_CHILD, link.union_occurrence_id, link.child_occurrence_id)
        for link in tree.parent_child_links
    }
    actual_edges = [
        (edge.kind, edge.union_occurrence_id, edge.person_occurrence_id)
        for edge in layout.edges
    ]
    assert len(actual_edges) == len(expected_edges)
    assert set(actual_edges) == expected_edges

    configuration = TreeLayoutConfiguration()
    projection_people = {item.id: item for item in tree.person_occurrences}
    family_by_union = {item.id: item.family_id for item in tree.union_occurrences}
    for union in tree.union_occurrences:
        suffix = f":family:{family_by_union[union.id]}"
        pivot_id = union.id.removeprefix("union:").removesuffix(suffix)
        if (
            union.id in core.union_occurrence_ids
            or not union.id.endswith(suffix)
            or pivot_id not in people
            or projection_people[pivot_id].generation < 0
        ):
            continue
        pivot = people[pivot_id]
        other_partners = [
            people[partner.occurrence_id]
            for partner in union.partners
            if partner.occurrence_id != pivot_id
        ]
        if other_partners:
            assert {
                partner.y for partner in other_partners
            } == {pivot.y + pivot.height + configuration.descendant_partner_gap}
        assert unions[union.id].y == (
            pivot.y
            + pivot.height
            + configuration.descendant_partner_gap / 2
        )

    occurrence_person_ids = {item.id: item.person_id for item in tree.person_occurrences}
    union_family_ids = {item.id: item.family_id for item in tree.union_occurrences}
    for link in tree.parent_child_links:
        family = genealogy.families[union_family_ids[link.union_occurrence_id]]
        assert occurrence_person_ids[link.child_occurrence_id] in family.children

    bounds = layout.bounds
    assert layout.width == bounds.width and layout.height == bounds.height
    for node in layout.person_nodes:
        assert bounds.x <= node.x and node.x + node.width <= bounds.x + bounds.width
        assert bounds.y <= node.y and node.y + node.height <= bounds.y + bounds.height
    for node in layout.union_nodes:
        assert bounds.x <= node.x <= bounds.x + bounds.width
        assert bounds.y <= node.y <= bounds.y + bounds.height
    for edge in layout.edges:
        for point in edge.points:
            assert bounds.x <= point.x <= bounds.x + bounds.width
            assert bounds.y <= point.y <= bounds.y + bounds.height
        for a, b in zip(edge.points, edge.points[1:]):
            assert a.x == b.x or a.y == b.y, f"diagonal: {edge}"
            for card in layout.person_nodes:
                assert not segment_crosses_card_interior(a, b, card), (
                    f"edge {edge.kind.value} {edge.union_occurrence_id} / "
                    f"{edge.person_occurrence_id} crosses {card.occurrence_id}: {a} -> {b}"
                )

    second_tree = build_combined_tree(genealogy, options)
    assert tree == second_tree
    assert layout == layout_combined_tree(second_tree)


def test_synthetic_implex_and_cycle_are_present() -> None:
    genealogy, options = scenario("implex")
    tree = build_combined_tree(genealogy, options)
    assert sum(item.person_id == "@shared_grandparent@" for item in tree.person_occurrences) == 2

    genealogy, options = scenario("truncated_cycle")
    tree = build_combined_tree(genealogy, options)
    assert any(item.cycle_truncated for item in tree.person_occurrences)


@pytest.mark.parametrize(
    ("name", "minimum_generation", "maximum_generation", "core_unions"),
    (
        ("root_deep_ancestry", -5, 0, 1),
        ("all_core_deep_ancestry", -5, 0, 3),
        ("asc_five_desc_five", -5, 5, 1),
        ("three_unbalanced_unions", 0, 2, 3),
        ("five_unions", 0, 1, 5),
        ("wide_siblings", -1, 1, 1),
    ),
)
def test_synthetic_scenario_reaches_intended_depth_and_core(
    name: str, minimum_generation: int, maximum_generation: int, core_unions: int
) -> None:
    genealogy, options = scenario(name)
    tree = build_combined_tree(genealogy, options)
    assert min(item.generation for item in tree.person_occurrences) == minimum_generation
    assert max(item.generation for item in tree.person_occurrences) == maximum_generation
    assert len(tree.central_family_core.union_occurrence_ids) == core_unions

from src.domain.models import Family, Genealogy, Person
from src.services.combined_tree import CombinedTreeOptions, build_combined_tree
from src.services.tree_layout import (
    LayoutBounds,
    LayoutEdgeKind,
    PersonLayoutNode,
    UnionLayoutNode,
    layout_combined_tree,
)


def genealogy_with_ancestry_and_descendance() -> Genealogy:
    return Genealogy(
        persons={
            person_id: Person(id=person_id)
            for person_id in ("@R@", "@F@", "@M@", "@S@", "@C1@", "@C2@")
        },
        families={
            "@P@": Family(id="@P@", father_id="@F@", mother_id="@M@", children=["@R@"]),
            "@U@": Family(id="@U@", partners=["@R@", "@S@"], children=["@C1@", "@C2@"]),
        },
    )


def make_layout(genealogy: Genealogy, root: str = "@R@", ancestors: int = 1, descendants: int = 1):
    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions(root, ancestors, descendants, show_siblings=False),
    )
    return tree, layout_combined_tree(tree)


def nodes_by_occurrence(layout):
    return {node.occurrence_id: node for node in layout.person_nodes}


def unions_by_occurrence(layout):
    return {node.union_occurrence_id: node for node in layout.union_nodes}


def rectangles_overlap(first, second) -> bool:
    return not (
        first.x + first.width <= second.x
        or second.x + second.width <= first.x
        or first.y + first.height <= second.y
        or second.y + second.height <= first.y
    )


def test_layout_places_ancestry_above_descendance_without_card_overlap():
    tree, layout = make_layout(genealogy_with_ancestry_and_descendance())
    nodes = nodes_by_occurrence(layout)

    assert len(nodes) == len(tree.person_occurrences)
    assert len(layout.union_nodes) == len(tree.union_occurrences)
    assert all(
        not rectangles_overlap(first, second)
        for index, first in enumerate(layout.person_nodes)
        for second in layout.person_nodes[index + 1 :]
    )
    for edge in layout.edges:
        if edge.kind is LayoutEdgeKind.PARENT_CHILD:
            union = unions_by_occurrence(layout)[edge.union_occurrence_id]
            child = nodes[edge.person_occurrence_id]
            assert union.y < child.y


def test_layout_keeps_partners_on_one_generation_and_union_between_them():
    _, layout = make_layout(genealogy_with_ancestry_and_descendance())
    nodes = nodes_by_occurrence(layout)
    unions = unions_by_occurrence(layout)
    root = nodes["person:root"]
    spouse = next(node for node in layout.person_nodes if node.occurrence_id.endswith(":partner:1"))
    union = unions["union:person:root:family:@U@"]

    assert root.y == spouse.y
    assert min(root.x + root.width / 2, spouse.x + spouse.width / 2) < union.x < max(
        root.x + root.width / 2,
        spouse.x + spouse.width / 2,
    )


def test_layout_groups_children_below_their_union_in_source_order():
    _, layout = make_layout(genealogy_with_ancestry_and_descendance())
    nodes = nodes_by_occurrence(layout)
    union = unions_by_occurrence(layout)["union:person:root:family:@U@"]
    children = sorted(
        (
            node
            for node in layout.person_nodes
            if ":child:" in node.occurrence_id
        ),
        key=lambda node: node.x,
    )

    assert len(children) == 2
    assert union.y < children[0].y
    assert children[0].x < children[1].x
    assert children[0].x + children[0].width / 2 < union.x < children[1].x + children[1].width / 2


def test_layout_has_one_pivot_card_and_three_distinct_unions():
    genealogy = Genealogy(
        persons={
            person_id: Person(id=person_id)
            for person_id in ("@A@", "@B@", "@E@", "@H@", "@C@", "@D@", "@F@")
        },
        families={
            "@U1@": Family(id="@U1@", partners=["@A@", "@B@"], children=["@C@"]),
            "@U2@": Family(id="@U2@", partners=["@A@", "@E@"], children=["@D@"]),
            "@U3@": Family(id="@U3@", partners=["@A@", "@H@"], children=["@F@"]),
        },
    )
    tree, layout = make_layout(genealogy, root="@A@", ancestors=0, descendants=1)

    assert [node.occurrence_id for node in layout.person_nodes].count("person:root") == 1
    assert len(layout.union_nodes) == 3
    assert len({node.union_occurrence_id for node in layout.union_nodes}) == 3
    root = nodes_by_occurrence(layout)["person:root"]
    assert all(
        min(root.x + root.width / 2, next(
            node.x + node.width / 2
            for node in layout.person_nodes
            if node.occurrence_id == partner.occurrence_id
        )) < union.x < max(
            root.x + root.width / 2,
            next(
                node.x + node.width / 2
                for node in layout.person_nodes
                if node.occurrence_id == partner.occurrence_id
            ),
        )
        for union in layout.union_nodes
        for source_union in tree.union_occurrences
        if source_union.id == union.union_occurrence_id
        for partner in source_union.partners
        if partner.occurrence_id != "person:root"
    )


def test_layout_keeps_childless_union_visible():
    genealogy = Genealogy(
        persons={"@A@": Person(id="@A@"), "@B@": Person(id="@B@")},
        families={"@U@": Family(id="@U@", partners=["@A@", "@B@"])},
    )
    _, layout = make_layout(genealogy, root="@A@", ancestors=0, descendants=1)

    assert len(layout.union_nodes) == 1
    assert [edge.kind for edge in layout.edges] == [LayoutEdgeKind.PARTNER, LayoutEdgeKind.PARTNER]


def test_layout_treats_cycle_terminal_and_unknown_occurrences_as_leaves():
    genealogy = Genealogy(
        persons={"@A@": Person(id="@A@"), "@B@": Person(id="@B@")},
        families={"@U@": Family(id="@U@", partners=["@A@", "@B@"], children=["@A@"])},
    )
    tree, layout = make_layout(genealogy, root="@A@", ancestors=0, descendants=3)

    terminal = next(item for item in tree.person_occurrences if item.id.endswith(":child:0"))
    assert terminal.cycle_truncated is True
    assert terminal.id in nodes_by_occurrence(layout)
    assert len(layout.union_nodes) == 1


def test_layout_is_deterministic():
    tree, first = make_layout(genealogy_with_ancestry_and_descendance())
    second = layout_combined_tree(tree)

    assert first == second



def test_layout_accepts_linked_sibling_roots_without_duplicate_pivot():
    genealogy = Genealogy(
        persons={
            person_id: Person(id=person_id)
            for person_id in ("@R@", "@S@", "@F@", "@M@", "@P@", "@C@")
        },
        families={
            "@PARENTS@": Family(
                id="@PARENTS@",
                father_id="@F@",
                mother_id="@M@",
                children=["@R@", "@S@"],
            ),
            "@S_UNION@": Family(id="@S_UNION@", partners=["@S@", "@P@"], children=["@C@"]),
        },
    )
    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=1, show_siblings=True),
    )
    layout = layout_combined_tree(tree)

    assert len(layout.person_nodes) == len(tree.person_occurrences)
    assert [node.occurrence_id for node in layout.person_nodes].count("person:root") == 1
    assert any(node.union_occurrence_id.endswith("@S_UNION@") for node in layout.union_nodes)



def central_ancestry_genealogy() -> Genealogy:
    return Genealogy(
        persons={
            person_id: Person(id=person_id)
            for person_id in (
                "@R@", "@S@", "@RF@", "@RM@", "@SF@", "@SM@", "@C@",
            )
        },
        families={
            "@U@": Family(id="@U@", partners=["@R@", "@S@"], children=["@C@"]),
            "@RP@": Family(id="@RP@", father_id="@RF@", mother_id="@RM@", children=["@R@"]),
            "@SP@": Family(id="@SP@", father_id="@SF@", mother_id="@SM@", children=["@S@"]),
        },
    )


def test_layout_places_one_central_union_with_both_ancestries():
    tree = build_combined_tree(
        central_ancestry_genealogy(),
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=1, show_siblings=False),
    )
    layout = layout_combined_tree(tree)
    nodes = nodes_by_occurrence(layout)
    core = tree.central_family_core

    assert set(core.member_occurrence_ids) == {"person:root", core.member_occurrence_ids[1]}
    root = nodes["person:root"]
    spouse = nodes[core.member_occurrence_ids[1]]
    assert root.y == spouse.y
    assert abs((root.x + root.width / 2) - (spouse.x + spouse.width / 2)) == 192
    assert {"@RF@", "@RM@", "@SF@", "@SM@"} <= {
        occurrence.person_id
        for occurrence in tree.person_occurrences
        if occurrence.id in nodes
    }


def test_layout_keeps_multi_union_core_compact_despite_wide_ancestry():
    people = {
        person_id: Person(id=person_id)
        for person_id in (
            "@R@", "@S1@", "@S2@", "@RF@", "@RM@", "@A@", "@B@",
            "@S1F@", "@S1M@", "@C@", "@D@", "@S2F@", "@S2M@", "@E@", "@F@",
        )
    }
    families = {
        "@U1@": Family(id="@U1@", partners=["@R@", "@S1@"]),
        "@U2@": Family(id="@U2@", partners=["@R@", "@S2@"]),
        "@RP@": Family(id="@RP@", father_id="@RF@", mother_id="@RM@", children=["@R@"]),
        "@S1P@": Family(id="@S1P@", father_id="@S1F@", mother_id="@S1M@", children=["@S1@"]),
        "@S2P@": Family(id="@S2P@", father_id="@S2F@", mother_id="@S2M@", children=["@S2@"]),
        "@RFP@": Family(id="@RFP@", father_id="@A@", mother_id="@B@", children=["@RF@"]),
        "@S1FP@": Family(id="@S1FP@", father_id="@C@", mother_id="@D@", children=["@S1F@"]),
        "@S2FP@": Family(id="@S2FP@", father_id="@E@", mother_id="@F@", children=["@S2F@"]),
    }
    tree = build_combined_tree(
        Genealogy(persons=people, families=families),
        CombinedTreeOptions("@R@", ancestor_generations=2, descendant_generations=1, show_siblings=False),
    )
    layout = layout_combined_tree(tree)
    nodes = nodes_by_occurrence(layout)
    core_nodes = [nodes[item] for item in tree.central_family_core.member_occurrence_ids]

    assert len(core_nodes) == 3
    assert max(node.x + node.width / 2 for node in core_nodes) - min(
        node.x + node.width / 2 for node in core_nodes
    ) == 384
    assert all(
        not rectangles_overlap(first, second)
        for index, first in enumerate(layout.person_nodes)
        for second in layout.person_nodes[index + 1 :]
    )


def test_layout_places_three_central_unions_without_duplicate_root():
    genealogy = Genealogy(
        persons={person_id: Person(id=person_id) for person_id in ("@R@", "@A@", "@B@", "@C@")},
        families={
            "@U1@": Family(id="@U1@", partners=["@R@", "@A@"]),
            "@U2@": Family(id="@U2@", partners=["@R@", "@B@"]),
            "@U3@": Family(id="@U3@", partners=["@R@", "@C@"]),
        },
    )
    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=0, descendant_generations=0, show_siblings=False),
    )
    layout = layout_combined_tree(tree)

    assert [node.occurrence_id for node in layout.person_nodes].count("person:root") == 1
    assert len(layout.union_nodes) == 3
    assert len(tree.central_family_core.member_occurrence_ids) == 4


def test_layout_keeps_central_core_complete_at_descendant_depth_zero():
    tree = build_combined_tree(
        central_ancestry_genealogy(),
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=0, show_siblings=False),
    )
    layout = layout_combined_tree(tree)

    assert {node.occurrence_id for node in layout.person_nodes} == {
        occurrence.id for occurrence in tree.person_occurrences
    }
    assert len(layout.union_nodes) == 3
    assert not any(
        edge.kind is LayoutEdgeKind.PARENT_CHILD
        and edge.union_occurrence_id in tree.central_family_core.union_occurrence_ids
        for edge in layout.edges
    )


def test_multicore_layout_is_deterministic():
    tree = build_combined_tree(
        central_ancestry_genealogy(),
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=1, show_siblings=False),
    )

    assert layout_combined_tree(tree) == layout_combined_tree(tree)



def three_union_genealogy() -> Genealogy:
    return Genealogy(
        persons={
            person_id: Person(id=person_id)
            for person_id in ("@A@", "@B@", "@E@", "@H@", "@C@", "@D@", "@F@")
        },
        families={
            "@U1@": Family(id="@U1@", partners=["@A@", "@B@"], children=["@C@"]),
            "@U2@": Family(id="@U2@", partners=["@A@", "@E@"], children=["@D@"]),
            "@U3@": Family(id="@U3@", partners=["@A@", "@H@"], children=["@F@"]),
        },
    )


def assert_edges_are_orthogonal_and_avoid_cards(layout):
    for edge in layout.edges:
        assert len(edge.points) >= 2
        for start, end in zip(edge.points, edge.points[1:]):
            assert start.x == end.x or start.y == end.y, edge
            for card in layout.person_nodes:
                if start.x == end.x:
                    crosses_interior = (
                        card.x < start.x < card.x + card.width
                        and max(min(start.y, end.y), card.y)
                        < min(max(start.y, end.y), card.y + card.height)
                    )
                else:
                    crosses_interior = (
                        card.y < start.y < card.y + card.height
                        and max(min(start.x, end.x), card.x)
                        < min(max(start.x, end.x), card.x + card.width)
                    )
                assert not crosses_interior, (edge, card)


def test_routing_does_not_change_simple_fixture_placements():
    _, layout = make_layout(genealogy_with_ancestry_and_descendance())

    assert layout.person_nodes == (
        PersonLayoutNode("person:root", 40.0, 184.0, 160.0, 72.0),
        PersonLayoutNode("person:union:person:root:family:@U@:partner:1", 232.0, 184.0, 160.0, 72.0),
        PersonLayoutNode("person:union:person:root:parents:@P@:father", 40.0, 40.0, 160.0, 72.0),
        PersonLayoutNode("person:union:person:root:parents:@P@:mother", 232.0, 40.0, 160.0, 72.0),
        PersonLayoutNode("person:union:person:root:family:@U@:child:0", 40.0, 328.0, 160.0, 72.0),
        PersonLayoutNode("person:union:person:root:family:@U@:child:1", 232.0, 328.0, 160.0, 72.0),
    )
    assert layout.union_nodes == (
        UnionLayoutNode("union:person:root:family:@U@", 216.0, 292.0),
        UnionLayoutNode("union:person:root:parents:@P@", 216.0, 148.0),
    )
    assert (layout.width, layout.height, layout.bounds) == (
        432.0,
        440.0,
        LayoutBounds(0.0, 0.0, 432.0, 440.0),
    )


def test_routing_keeps_multicore_centers_and_bounds():
    tree = build_combined_tree(
        central_ancestry_genealogy(),
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=1, show_siblings=False),
    )
    layout = layout_combined_tree(tree)
    nodes = nodes_by_occurrence(layout)
    unions = unions_by_occurrence(layout)

    assert (nodes["person:root"].x, nodes["person:root"].y) == (240.0, 184.0)
    spouse_id = tree.central_family_core.member_occurrence_ids[1]
    assert (nodes[spouse_id].x, nodes[spouse_id].y) == (432.0, 184.0)
    assert (unions[tree.central_family_core.union_occurrence_ids[0]].x,
            unions[tree.central_family_core.union_occurrence_ids[0]].y) == (416.0, 292.0)
    assert (layout.width, layout.height, layout.bounds) == (
        832.0,
        440.0,
        LayoutBounds(0.0, 0.0, 832.0, 440.0),
    )


def test_all_routes_are_orthogonal_and_clear_of_cards():
    simple = make_layout(genealogy_with_ancestry_and_descendance())[1]
    multicore = layout_combined_tree(build_combined_tree(
        central_ancestry_genealogy(),
        CombinedTreeOptions("@R@", 1, 1, show_siblings=False),
    ))
    three_unions = make_layout(three_union_genealogy(), root="@A@", ancestors=0, descendants=1)[1]

    for layout in (simple, multicore, three_unions):
        assert_edges_are_orthogonal_and_avoid_cards(layout)


def test_siblings_of_one_union_share_the_same_bus():
    _, layout = make_layout(genealogy_with_ancestry_and_descendance())
    union_id = "union:person:root:family:@U@"
    edges = [
        edge for edge in layout.edges
        if edge.kind is LayoutEdgeKind.PARENT_CHILD
        and edge.union_occurrence_id == union_id
    ]
    union = unions_by_occurrence(layout)[union_id]
    children = nodes_by_occurrence(layout)

    assert len(edges) == 2
    assert len({edge.points[1].y for edge in edges}) == 1
    bus_y = edges[0].points[1].y
    assert union.y < bus_y < min(children[edge.person_occurrence_id].y for edge in edges)
    assert all(edge.points[0].x == union.x for edge in edges)
    assert all(edge.points[-1].x == children[edge.person_occurrence_id].x
               + children[edge.person_occurrence_id].width / 2 for edge in edges)


def test_single_offset_child_uses_an_orthogonal_dogleg():
    _, layout = make_layout(genealogy_with_ancestry_and_descendance())
    edge = next(
        edge for edge in layout.edges
        if edge.kind is LayoutEdgeKind.PARENT_CHILD
        and edge.union_occurrence_id == "union:person:root:parents:@P@"
    )
    union = unions_by_occurrence(layout)[edge.union_occurrence_id]
    child = nodes_by_occurrence(layout)[edge.person_occurrence_id]

    assert len(edge.points) == 4
    assert edge.points[0].x == edge.points[1].x == union.x
    assert edge.points[1].y == edge.points[2].y
    assert edge.points[2].x == edge.points[3].x == child.x + child.width / 2
    assert_edges_are_orthogonal_and_avoid_cards(layout)


def test_single_aligned_child_uses_only_a_vertical():
    genealogy = Genealogy(
        persons={"@A@": Person(id="@A@"), "@C@": Person(id="@C@")},
        families={"@U@": Family(id="@U@", partners=["@A@"], children=["@C@"])},
    )
    _, layout = make_layout(genealogy, root="@A@", ancestors=0, descendants=1)
    edge = next(edge for edge in layout.edges if edge.kind is LayoutEdgeKind.PARENT_CHILD)

    assert len(edge.points) == 2
    assert edge.points[0].x == edge.points[1].x
    assert_edges_are_orthogonal_and_avoid_cards(layout)


def test_multiple_unions_use_distinct_partner_tracks():
    tree, layout = make_layout(three_union_genealogy(), root="@A@", ancestors=0, descendants=1)
    root_edges = [
        edge for edge in layout.edges
        if edge.kind is LayoutEdgeKind.PARTNER
        and edge.person_occurrence_id == tree.root_occurrence_id
    ]

    assert len(root_edges) == 3
    assert len({edge.points[1].y for edge in root_edges}) == 3
    assert len({edge.union_occurrence_id for edge in root_edges}) == 3
    assert_edges_are_orthogonal_and_avoid_cards(layout)

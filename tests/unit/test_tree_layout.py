from src.domain.models import Family, Genealogy, Person
from src.services.combined_tree import CombinedTreeOptions, build_combined_tree
from src.services.tree_layout import LayoutEdgeKind, layout_combined_tree


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

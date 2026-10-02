from src.domain.models import Family, Genealogy, Person
from src.services.combined_tree import CombinedTreeOptions, build_combined_tree
from src.services.tree_layout import layout_combined_tree
from src.services.tree_view import PORTRAIT_TREE_LAYOUT_CONFIGURATION


def test_portrait_view_preset_uses_fixed_cards_without_overlap():
    genealogy = Genealogy(
        persons={person_id: Person(id=person_id) for person_id in ("@R@", "@S@", "@C1@", "@C2@")},
        families={"@F@": Family(id="@F@", partners=["@R@", "@S@"], children=["@C1@", "@C2@"])},
    )
    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", 0, 1, show_siblings=False),
    )
    layout = layout_combined_tree(tree, PORTRAIT_TREE_LAYOUT_CONFIGURATION)

    assert {(node.width, node.height) for node in layout.person_nodes} == {(160.0, 220.0)}
    assert all(
        first.x + first.width <= second.x
        or second.x + second.width <= first.x
        or first.y + first.height <= second.y
        or second.y + second.height <= first.y
        for index, first in enumerate(layout.person_nodes)
        for second in layout.person_nodes[index + 1 :]
    )

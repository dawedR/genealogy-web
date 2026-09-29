import pytest

from src.domain.models import Family, Genealogy, Person
from src.services.combined_tree import (
    CombinedTreeOptions,
    TreeDiagnosticCode,
    TreeUnionPartnerRole,
    build_combined_tree,
)


def make_genealogy() -> Genealogy:
    return Genealogy(
        persons={
            "@R@": Person(id="@R@", given_names="Racine"),
            "@F@": Person(id="@F@", given_names="Père"),
            "@M@": Person(id="@M@", given_names="Mère"),
            "@S@": Person(id="@S@", given_names="Conjointe"),
            "@C1@": Person(id="@C1@", given_names="Enfant un"),
            "@C2@": Person(id="@C2@", given_names="Enfant deux"),
            "@GF@": Person(id="@GF@", given_names="Grand-père"),
            "@GM@": Person(id="@GM@", given_names="Grand-mère"),
        },
        families={
            "@PARENTS@": Family(
                id="@PARENTS@",
                father_id="@F@",
                mother_id="@M@",
                children=["@R@"],
            ),
            "@UNION@": Family(
                id="@UNION@",
                partners=["@R@", "@S@"],
                father_id="@R@",
                mother_id="@S@",
                children=["@C1@", "@C2@"],
            ),
            "@GRANDPARENTS@": Family(
                id="@GRANDPARENTS@",
                father_id="@GF@",
                mother_id="@GM@",
                children=["@F@"],
            ),
        },
    )


def options(
    ancestors: int = 1,
    descendants: int = 1,
    show_siblings: bool = True,
) -> CombinedTreeOptions:
    return CombinedTreeOptions(
        root_person_id="@R@",
        ancestor_generations=ancestors,
        descendant_generations=descendants,
        show_siblings=show_siblings,
    )


def occurrences_by_id(tree):
    return {occurrence.id: occurrence for occurrence in tree.person_occurrences}


def test_projects_root_parents_union_spouse_and_children():
    tree = build_combined_tree(make_genealogy(), options())

    people = occurrences_by_id(tree)
    assert people["person:root"].person_id == "@R@"
    assert people["person:root"].generation == 0

    parent_union = "union:person:root:parents:@PARENTS@"
    assert {
        people[partner.occurrence_id].person_id
        for union in tree.union_occurrences
        if union.id == parent_union
        for partner in union.partners
    } == {"@F@", "@M@"}

    descendant_union = "union:person:root:family:@UNION@"
    assert {
        people[partner.occurrence_id].person_id
        for union in tree.union_occurrences
        if union.id == descendant_union
        for partner in union.partners
    } == {"@R@", "@S@"}
    assert [
        people[link.child_occurrence_id].person_id
        for link in tree.parent_child_links
        if link.union_occurrence_id == descendant_union
    ] == ["@C1@", "@C2@"]


def test_ancestor_and_descendant_depths_are_independent():
    tree = build_combined_tree(make_genealogy(), options(ancestors=2, descendants=0))

    assert {occurrence.generation for occurrence in tree.person_occurrences} == {-2, -1, 0}
    assert all(
        ":child:" not in link.child_occurrence_id
        for link in tree.parent_child_links
        if ":family:" in link.union_occurrence_id
    )
    assert all(union.family_id != "@UNION@" for union in tree.union_occurrences)


def test_depth_zero_keeps_only_root_when_there_is_no_union():
    genealogy = Genealogy(persons={"@R@": Person(id="@R@")})

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=0, descendant_generations=0),
    )

    assert [(occurrence.person_id, occurrence.generation) for occurrence in tree.person_occurrences] == [
        ("@R@", 0)
    ]
    assert tree.union_occurrences == ()
    assert tree.parent_child_links == ()


def test_conjoint_without_child_is_projected():
    genealogy = Genealogy(
        persons={"@R@": Person(id="@R@"), "@S@": Person(id="@S@")},
        families={
            "@U@": Family(
                id="@U@",
                partners=["@R@", "@S@"],
                father_id="@R@",
                mother_id="@S@",
            )
        },
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=0, descendant_generations=1),
    )

    assert len(tree.union_occurrences) == 1
    assert [occurrence.person_id for occurrence in tree.person_occurrences] == ["@R@", "@S@"]
    assert tree.parent_child_links == ()


def test_missing_parent_in_existing_family_creates_unknown_occurrence():
    genealogy = Genealogy(
        persons={"@R@": Person(id="@R@"), "@M@": Person(id="@M@")},
        families={
            "@P@": Family(
                id="@P@",
                mother_id="@M@",
                children=["@R@"],
            )
        },
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=0),
    )

    union = tree.union_occurrences[0]
    people = occurrences_by_id(tree)
    by_role = {partner.role: people[partner.occurrence_id].person_id for partner in union.partners}
    assert by_role == {
        TreeUnionPartnerRole.FATHER: None,
        TreeUnionPartnerRole.MOTHER: "@M@",
    }


def test_no_parent_family_does_not_create_unknown_parents():
    genealogy = Genealogy(persons={"@R@": Person(id="@R@")})

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=0),
    )

    assert [occurrence.person_id for occurrence in tree.person_occurrences] == ["@R@"]


def test_multiple_parent_families_use_explicit_deterministic_fallback():
    genealogy = Genealogy(
        persons={"@R@": Person(id="@R@"), "@A@": Person(id="@A@"), "@B@": Person(id="@B@")},
        families={
            "@Z@": Family(id="@Z@", father_id="@B@", children=["@R@"]),
            "@A@": Family(id="@A@", father_id="@A@", children=["@R@"]),
        },
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=0),
    )

    assert len(tree.diagnostics) == 1
    diagnostic = tree.diagnostics[0]
    assert diagnostic.code is TreeDiagnosticCode.MULTIPLE_PARENT_FAMILIES
    assert diagnostic.person_id == "@R@"
    assert diagnostic.family_ids == ("@A@", "@Z@")
    assert diagnostic.selected_family_id == "@A@"
    assert tree.union_occurrences[0].family_id == "@A@"


def test_identical_constructions_produce_identical_occurrence_ids():
    genealogy = make_genealogy()

    first = build_combined_tree(genealogy, options(ancestors=2, descendants=1))
    second = build_combined_tree(genealogy, options(ancestors=2, descendants=1))

    assert [occurrence.id for occurrence in first.person_occurrences] == [
        occurrence.id for occurrence in second.person_occurrences
    ]
    assert [union.id for union in first.union_occurrences] == [
        union.id for union in second.union_occurrences
    ]


@pytest.mark.parametrize(
    "ancestor_generations, descendant_generations",
    [(-1, 0), (0, -1)],
)
def test_negative_depth_is_rejected(
    ancestor_generations: int,
    descendant_generations: int,
):
    with pytest.raises(ValueError, match="generations must be zero or greater"):
        CombinedTreeOptions("@R@", ancestor_generations, descendant_generations)



def multiple_unions_genealogy() -> Genealogy:
    return Genealogy(
        persons={
            person_id: Person(id=person_id)
            for person_id in ("@A@", "@B@", "@E@", "@H@", "@C@", "@D@", "@F@")
        },
        families={
            "@U2@": Family(
                id="@U2@",
                partners=["@A@", "@E@"],
                father_id="@A@",
                mother_id="@E@",
                children=["@F@"],
            ),
            "@U3@": Family(
                id="@U3@",
                partners=["@A@", "@H@"],
                father_id="@A@",
                mother_id="@H@",
            ),
            "@U1@": Family(
                id="@U1@",
                partners=["@A@", "@B@"],
                father_id="@A@",
                mother_id="@B@",
                children=["@C@", "@D@"],
            ),
        },
    )


def test_three_unions_keep_children_attached_to_their_own_union():
    tree = build_combined_tree(
        multiple_unions_genealogy(),
        CombinedTreeOptions("@A@", ancestor_generations=0, descendant_generations=1, show_siblings=False),
    )
    people = occurrences_by_id(tree)

    union_ids = [union.id for union in tree.union_occurrences]
    assert union_ids == [
        "union:person:root:family:@U1@",
        "union:person:root:family:@U2@",
        "union:person:root:family:@U3@",
    ]
    children_by_union = {
        union.id: [
            people[link.child_occurrence_id].person_id
            for link in tree.parent_child_links
            if link.union_occurrence_id == union.id
        ]
        for union in tree.union_occurrences
    }
    assert children_by_union == {
        "union:person:root:family:@U1@": ["@C@", "@D@"],
        "union:person:root:family:@U2@": ["@F@"],
        "union:person:root:family:@U3@": [],
    }
    assert all(link.child_occurrence_id != "person:root" for link in tree.parent_child_links)


def test_absent_conjoint_does_not_create_an_artificial_person():
    genealogy = Genealogy(
        persons={"@A@": Person(id="@A@"), "@C@": Person(id="@C@")},
        families={
            "@U@": Family(id="@U@", partners=["@A@"], father_id="@A@", children=["@C@"])},
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@A@", ancestor_generations=0, descendant_generations=1, show_siblings=False),
    )

    assert [partner.occurrence_id for partner in tree.union_occurrences[0].partners] == ["person:root"]
    assert [occurrence.person_id for occurrence in tree.person_occurrences] == ["@A@", "@C@"]


def siblings_genealogy() -> Genealogy:
    return Genealogy(
        persons={
            person_id: Person(id=person_id)
            for person_id in ("@R@", "@S1@", "@S2@", "@F@", "@M@", "@P@", "@C@")
        },
        families={
            "@PARENTS@": Family(
                id="@PARENTS@",
                father_id="@F@",
                mother_id="@M@",
                children=["@R@", "@S1@", "@S2@"],
            ),
            "@S2_UNION@": Family(
                id="@S2_UNION@",
                partners=["@S2@", "@P@"],
                father_id="@S2@",
                mother_id="@P@",
                children=["@C@"],
            ),
        },
    )


def test_show_siblings_true_selects_canonical_parent_family_children():
    tree = build_combined_tree(
        siblings_genealogy(),
        CombinedTreeOptions("@R@", ancestor_generations=0, descendant_generations=1, show_siblings=True),
    )
    people = occurrences_by_id(tree)

    assert [
        (occurrence.person_id, occurrence.generation)
        for occurrence in tree.person_occurrences
    ] == [
        ("@R@", 0),
        ("@S1@", 0),
        ("@S2@", 0),
        ("@P@", 0),
        ("@C@", 1),
    ]
    assert [union.family_id for union in tree.union_occurrences] == ["@S2_UNION@"]
    assert people["person:root:parent-family:@PARENTS@:child:1"].person_id == "@S1@"


def test_show_siblings_false_keeps_only_root_descendant_branch():
    tree = build_combined_tree(
        siblings_genealogy(),
        CombinedTreeOptions("@R@", ancestor_generations=0, descendant_generations=1, show_siblings=False),
    )

    assert [(occurrence.person_id, occurrence.generation) for occurrence in tree.person_occurrences] == [
        ("@R@", 0)
    ]
    assert tree.union_occurrences == ()


def test_descendant_depth_zero_with_siblings_contains_g0_roots_only():
    tree = build_combined_tree(
        siblings_genealogy(),
        CombinedTreeOptions("@R@", ancestor_generations=0, descendant_generations=0, show_siblings=True),
    )

    assert [(occurrence.person_id, occurrence.generation) for occurrence in tree.person_occurrences] == [
        ("@R@", 0),
        ("@S1@", 0),
        ("@S2@", 0),
    ]
    assert tree.union_occurrences == ()
    assert tree.parent_child_links == ()


def test_descendant_depth_zero_without_siblings_contains_root_only():
    tree = build_combined_tree(
        siblings_genealogy(),
        CombinedTreeOptions("@R@", ancestor_generations=0, descendant_generations=0, show_siblings=False),
    )

    assert [(occurrence.person_id, occurrence.generation) for occurrence in tree.person_occurrences] == [
        ("@R@", 0)
    ]
    assert tree.union_occurrences == ()


def test_siblings_are_limited_to_the_canonical_parent_family():
    genealogy = Genealogy(
        persons={
            person_id: Person(id=person_id)
            for person_id in ("@R@", "@FULL@", "@HALF@", "@F@", "@M@", "@OTHER@")
        },
        families={
            "@PARENTS@": Family(
                id="@PARENTS@",
                father_id="@F@",
                mother_id="@M@",
                children=["@R@", "@FULL@"],
            ),
            "@OTHER_UNION@": Family(
                id="@OTHER_UNION@",
                father_id="@F@",
                mother_id="@OTHER@",
                children=["@HALF@"],
            ),
        },
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=0, descendant_generations=0, show_siblings=True),
    )

    assert [occurrence.person_id for occurrence in tree.person_occurrences] == ["@R@", "@FULL@"]


def test_sibling_selection_keeps_ids_deterministic():
    genealogy = siblings_genealogy()
    options = CombinedTreeOptions("@R@", ancestor_generations=0, descendant_generations=1, show_siblings=True)

    first = build_combined_tree(genealogy, options)
    second = build_combined_tree(genealogy, options)

    assert [occurrence.id for occurrence in first.person_occurrences] == [
        occurrence.id for occurrence in second.person_occurrences
    ]
    assert [union.id for union in first.union_occurrences] == [
        union.id for union in second.union_occurrences
    ]

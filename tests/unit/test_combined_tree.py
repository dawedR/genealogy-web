import pytest

from src.domain.models import Family, Genealogy, Person
from src.services.combined_tree import (
    CombinedTreeOptions,
    CycleTruncatedDiagnostic,
    MissingPersonReferenceDiagnostic,
    TreeDiagnosticCode,
    TreeReferenceRole,
    TreeTraversal,
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
    assert any(union.family_id == "@UNION@" for union in tree.union_occurrences)
    assert core_member_person_ids(tree) == ["@R@", "@S@"]
    assert tree.central_family_core.union_occurrence_ids == (
        "union:person:root:family:@UNION@",
    )


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


def test_descendant_depth_zero_keeps_the_complete_central_core():
    genealogy = Genealogy(
        persons={"@R@": Person(id="@R@"), "@S@": Person(id="@S@")},
        families={"@U@": Family(id="@U@", partners=["@R@", "@S@"])},
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=0, descendant_generations=0, show_siblings=False),
    )

    assert core_member_person_ids(tree) == ["@R@", "@S@"]
    assert tree.central_family_core.union_occurrence_ids == (
        "union:person:root:family:@U@",
    )
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



def test_ancestry_implex_keeps_two_normal_occurrences_for_the_same_person():
    genealogy = Genealogy(
        persons={person_id: Person(id=person_id) for person_id in ("@C@", "@A@", "@B@", "@X@")},
        families={
            "@ROOT@": Family(id="@ROOT@", father_id="@A@", mother_id="@B@", children=["@C@"]),
            "@A_PARENTS@": Family(id="@A_PARENTS@", father_id="@X@", children=["@A@"]),
            "@B_PARENTS@": Family(id="@B_PARENTS@", father_id="@X@", children=["@B@"]),
        },
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@C@", ancestor_generations=2, descendant_generations=0, show_siblings=False),
    )

    x_occurrences = [occurrence for occurrence in tree.person_occurrences if occurrence.person_id == "@X@"]
    assert len(x_occurrences) == 2
    assert len({occurrence.id for occurrence in x_occurrences}) == 2
    assert all(not occurrence.cycle_truncated for occurrence in x_occurrences)
    assert not any(diagnostic.code is TreeDiagnosticCode.CYCLE_TRUNCATED for diagnostic in tree.diagnostics)


def test_descendant_repetition_in_distinct_contexts_is_not_a_cycle():
    genealogy = Genealogy(
        persons={person_id: Person(id=person_id) for person_id in ("@A@", "@B@", "@E@", "@C@")},
        families={
            "@U1@": Family(id="@U1@", partners=["@A@", "@B@"], children=["@C@"]),
            "@U2@": Family(id="@U2@", partners=["@A@", "@E@"], children=["@C@"]),
        },
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@A@", ancestor_generations=0, descendant_generations=1, show_siblings=False),
    )

    c_occurrences = [occurrence for occurrence in tree.person_occurrences if occurrence.person_id == "@C@"]
    assert len(c_occurrences) == 2
    assert len({occurrence.id for occurrence in c_occurrences}) == 2
    assert all(not occurrence.cycle_truncated for occurrence in c_occurrences)


def test_ancestor_cycle_is_terminal_and_keeps_the_complete_path():
    genealogy = Genealogy(
        persons={person_id: Person(id=person_id) for person_id in ("@A@", "@B@", "@C@")},
        families={
            "@F1@": Family(id="@F1@", father_id="@B@", children=["@A@"]),
            "@F2@": Family(id="@F2@", father_id="@C@", children=["@B@"]),
            "@F3@": Family(id="@F3@", father_id="@A@", children=["@C@"]),
        },
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@A@", ancestor_generations=3, descendant_generations=0, show_siblings=False),
    )

    terminal = [
        occurrence
        for occurrence in tree.person_occurrences
        if occurrence.person_id == "@A@" and occurrence.id != "person:root"
    ]
    assert len(terminal) == 1
    assert terminal[0].cycle_truncated is True
    diagnostic = next(
        diagnostic
        for diagnostic in tree.diagnostics
        if isinstance(diagnostic, CycleTruncatedDiagnostic)
    )
    assert diagnostic.traversal is TreeTraversal.ANCESTRY
    assert diagnostic.occurrence_id == terminal[0].id
    assert diagnostic.path_person_ids == ("@A@", "@B@", "@C@", "@A@")


def test_descendant_cycle_is_terminal_and_keeps_the_complete_path():
    genealogy = Genealogy(
        persons={person_id: Person(id=person_id) for person_id in ("@A@", "@B@", "@C@", "@D@")},
        families={
            "@U1@": Family(id="@U1@", partners=["@A@", "@B@"], children=["@C@"]),
            "@U2@": Family(id="@U2@", partners=["@C@", "@D@"], children=["@A@"]),
        },
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@A@", ancestor_generations=0, descendant_generations=3, show_siblings=False),
    )

    diagnostic = next(
        diagnostic
        for diagnostic in tree.diagnostics
        if isinstance(diagnostic, CycleTruncatedDiagnostic)
    )
    terminal = next(
        occurrence
        for occurrence in tree.person_occurrences
        if occurrence.id == diagnostic.occurrence_id
    )
    assert diagnostic.traversal is TreeTraversal.DESCENT
    assert diagnostic.path_person_ids == ("@A@", "@C@", "@A@")
    assert terminal.person_id == "@A@"
    assert terminal.cycle_truncated is True


def test_direct_union_parenthood_cycle_is_not_developed():
    genealogy = Genealogy(
        persons={"@A@": Person(id="@A@"), "@B@": Person(id="@B@")},
        families={"@U@": Family(id="@U@", partners=["@A@", "@B@"], children=["@A@"])},
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@A@", ancestor_generations=0, descendant_generations=3, show_siblings=False),
    )

    assert len(tree.union_occurrences) == 1
    assert any(
        isinstance(diagnostic, CycleTruncatedDiagnostic)
        and diagnostic.path_person_ids == ("@A@", "@A@")
        for diagnostic in tree.diagnostics
    )


def test_parent_without_reference_stays_unknown_without_diagnostic():
    genealogy = Genealogy(
        persons={"@R@": Person(id="@R@"), "@M@": Person(id="@M@")},
        families={"@P@": Family(id="@P@", mother_id="@M@", children=["@R@"])},
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=0, show_siblings=False),
    )

    father = next(occurrence for occurrence in tree.person_occurrences if occurrence.id.endswith(":father"))
    assert father.person_id is None
    assert father.missing_person_id is None
    assert tree.diagnostics == ()


def test_missing_parent_reference_is_unknown_and_diagnosed():
    genealogy = Genealogy(
        persons={"@R@": Person(id="@R@"), "@M@": Person(id="@M@")},
        families={"@P@": Family(id="@P@", father_id="@MISSING@", mother_id="@M@", children=["@R@"])},
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=0, show_siblings=False),
    )

    father = next(occurrence for occurrence in tree.person_occurrences if occurrence.id.endswith(":father"))
    diagnostic = next(diagnostic for diagnostic in tree.diagnostics if isinstance(diagnostic, MissingPersonReferenceDiagnostic))
    assert father.person_id is None
    assert father.missing_person_id == "@MISSING@"
    assert diagnostic.family_id == "@P@"
    assert diagnostic.role is TreeReferenceRole.FATHER
    assert diagnostic.occurrence_id == father.id


def test_missing_partner_reference_is_unknown_and_diagnosed():
    genealogy = Genealogy(
        persons={"@A@": Person(id="@A@")},
        families={"@U@": Family(id="@U@", partners=["@A@", "@MISSING@"])} ,
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@A@", ancestor_generations=0, descendant_generations=1, show_siblings=False),
    )

    partner = next(occurrence for occurrence in tree.person_occurrences if occurrence.id.endswith(":partner:1"))
    diagnostic = next(diagnostic for diagnostic in tree.diagnostics if isinstance(diagnostic, MissingPersonReferenceDiagnostic))
    assert partner.person_id is None
    assert partner.missing_person_id == "@MISSING@"
    assert diagnostic.role is TreeReferenceRole.PARTNER


def test_missing_child_reference_is_unknown_and_diagnosed():
    genealogy = Genealogy(
        persons={"@A@": Person(id="@A@"), "@B@": Person(id="@B@")},
        families={"@U@": Family(id="@U@", partners=["@A@", "@B@"], children=["@MISSING@"])},
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@A@", ancestor_generations=0, descendant_generations=1, show_siblings=False),
    )

    child = next(occurrence for occurrence in tree.person_occurrences if occurrence.id.endswith(":child:0"))
    diagnostic = next(diagnostic for diagnostic in tree.diagnostics if isinstance(diagnostic, MissingPersonReferenceDiagnostic))
    assert child.person_id is None
    assert child.missing_person_id == "@MISSING@"
    assert diagnostic.role is TreeReferenceRole.CHILD


def test_cycle_and_missing_reference_diagnostics_are_deterministic():
    genealogy = Genealogy(
        persons={"@A@": Person(id="@A@"), "@B@": Person(id="@B@")},
        families={
            "@U1@": Family(id="@U1@", partners=["@A@", "@MISSING@"], children=["@B@"]),
            "@U2@": Family(id="@U2@", partners=["@B@"], children=["@A@"]),
        },
    )
    options = CombinedTreeOptions("@A@", ancestor_generations=0, descendant_generations=2, show_siblings=False)

    first = build_combined_tree(genealogy, options)
    second = build_combined_tree(genealogy, options)

    assert first == second
    assert first.diagnostics == second.diagnostics


def core_member_person_ids(tree):
    people = occurrences_by_id(tree)
    return [
        people[occurrence_id].person_id
        for occurrence_id in tree.central_family_core.member_occurrence_ids
    ]


def test_central_core_without_union_contains_only_the_root():
    tree = build_combined_tree(
        Genealogy(persons={"@R@": Person(id="@R@")} ),
        CombinedTreeOptions("@R@", ancestor_generations=0, descendant_generations=1),
    )

    assert tree.central_family_core.root_occurrence_id == "person:root"
    assert tree.central_family_core.member_occurrence_ids == ("person:root",)
    assert tree.central_family_core.union_occurrence_ids == ()


def test_central_partner_receives_own_ancestry():
    genealogy = Genealogy(
        persons={
            person_id: Person(id=person_id)
            for person_id in ("@R@", "@S@", "@RF@", "@RM@", "@SF@", "@SM@")
        },
        families={
            "@U@": Family(id="@U@", partners=["@R@", "@S@"]),
            "@RP@": Family(id="@RP@", father_id="@RF@", mother_id="@RM@", children=["@R@"]),
            "@SP@": Family(id="@SP@", father_id="@SF@", mother_id="@SM@", children=["@S@"]),
        },
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=1, show_siblings=False),
    )

    assert core_member_person_ids(tree) == ["@R@", "@S@"]
    assert tree.central_family_core.union_occurrence_ids == (
        "union:person:root:family:@U@",
    )
    assert {occurrence.person_id for occurrence in tree.person_occurrences} >= {
        "@RF@", "@RM@", "@SF@", "@SM@",
    }


def test_central_core_keeps_three_unions_and_contextual_partners_in_order():
    tree = build_combined_tree(
        multiple_unions_genealogy(),
        CombinedTreeOptions("@A@", ancestor_generations=0, descendant_generations=1, show_siblings=False),
    )

    assert core_member_person_ids(tree) == ["@A@", "@B@", "@E@", "@H@"]
    assert tree.central_family_core.union_occurrence_ids == (
        "union:person:root:family:@U1@",
        "union:person:root:family:@U2@",
        "union:person:root:family:@U3@",
    )


def test_unknown_and_broken_central_partners_are_members_without_ancestry():
    unknown = Genealogy(
        persons={"@R@": Person(id="@R@")},
        families={"@U@": Family(id="@U@", partners=["@R@", None])},
    )
    broken = Genealogy(
        persons={"@R@": Person(id="@R@")},
        families={"@U@": Family(id="@U@", partners=["@R@", "@MISSING@"])},
    )

    unknown_tree = build_combined_tree(
        unknown,
        CombinedTreeOptions("@R@", ancestor_generations=2, descendant_generations=1, show_siblings=False),
    )
    broken_tree = build_combined_tree(
        broken,
        CombinedTreeOptions("@R@", ancestor_generations=2, descendant_generations=1, show_siblings=False),
    )

    assert core_member_person_ids(unknown_tree) == ["@R@", None]
    assert len(unknown_tree.person_occurrences) == 2
    assert core_member_person_ids(broken_tree) == ["@R@", None]
    broken_partner = occurrences_by_id(broken_tree)[
        broken_tree.central_family_core.member_occurrence_ids[1]
    ]
    assert broken_partner.missing_person_id == "@MISSING@"
    assert [diagnostic.role for diagnostic in broken_tree.diagnostics] == [
        TreeReferenceRole.PARTNER,
    ]


def test_descendant_partner_does_not_receive_central_ancestry():
    genealogy = Genealogy(
        persons={
            person_id: Person(id=person_id)
            for person_id in ("@R@", "@S@", "@C@", "@D@", "@DF@", "@DM@")
        },
        families={
            "@U@": Family(id="@U@", partners=["@R@", "@S@"], children=["@C@"]),
            "@CU@": Family(id="@CU@", partners=["@C@", "@D@"]),
            "@DP@": Family(id="@DP@", father_id="@DF@", mother_id="@DM@", children=["@D@"]),
        },
    )

    tree = build_combined_tree(
        genealogy,
        CombinedTreeOptions("@R@", ancestor_generations=1, descendant_generations=2, show_siblings=False),
    )

    assert "@D@" in {occurrence.person_id for occurrence in tree.person_occurrences}
    assert "@DF@" not in {occurrence.person_id for occurrence in tree.person_occurrences}
    assert "@DM@" not in {occurrence.person_id for occurrence in tree.person_occurrences}


def test_central_ancestry_implex_and_diagnostics_are_deterministic():
    genealogy = Genealogy(
        persons={
            person_id: Person(id=person_id)
            for person_id in ("@R@", "@S@", "@RF@", "@SF@", "@X@")
        },
        families={
            "@U@": Family(id="@U@", partners=["@R@", "@S@"]),
            "@RP@": Family(id="@RP@", father_id="@RF@", children=["@R@"]),
            "@SP@": Family(id="@SP@", father_id="@SF@", children=["@S@"]),
            "@RGP@": Family(id="@RGP@", father_id="@X@", children=["@RF@"]),
            "@SGP@": Family(id="@SGP@", father_id="@X@", children=["@SF@"]),
        },
    )
    options = CombinedTreeOptions("@R@", ancestor_generations=2, descendant_generations=1, show_siblings=False)

    first = build_combined_tree(genealogy, options)
    second = build_combined_tree(genealogy, options)
    x_occurrences = [item for item in first.person_occurrences if item.person_id == "@X@"]

    assert len(x_occurrences) == 2
    assert len({item.id for item in x_occurrences}) == 2
    assert first == second
    assert first.diagnostics == second.diagnostics

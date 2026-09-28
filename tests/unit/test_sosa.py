import pytest

from src.domain.models import (
    Family,
    Genealogy,
    Person,
    Sex,
)
from src.services.sosa import build_sosa_ancestry


def make_genealogy() -> Genealogy:
    persons = {
        "@I1@": Person(
            id="@I1@",
            given_names="Paul",
            surname="Dupont",
            sex=Sex.MALE,
        ),
        "@I2@": Person(
            id="@I2@",
            given_names="Jean",
            surname="Dupont",
            sex=Sex.MALE,
        ),
        "@I3@": Person(
            id="@I3@",
            given_names="Marie",
            surname="Martin",
            sex=Sex.FEMALE,
        ),
        "@I4@": Person(
            id="@I4@",
            given_names="Pierre",
            surname="Dupont",
            sex=Sex.MALE,
        ),
        "@I5@": Person(
            id="@I5@",
            given_names="Anne",
            surname="Durand",
            sex=Sex.FEMALE,
        ),
    }

    families = {
        "@F1@": Family(
            id="@F1@",
            partners=["@I2@", "@I3@"],
            children=["@I1@"],
            father_id="@I2@",
            mother_id="@I3@",
        ),
        "@F2@": Family(
            id="@F2@",
            partners=["@I4@", "@I5@"],
            children=["@I2@"],
            father_id="@I4@",
            mother_id="@I5@",
        ),
    }

    return Genealogy(
        persons=persons,
        families=families,
    )


def test_sosa_numbering():
    genealogy = make_genealogy()

    occurrences = build_sosa_ancestry(
        genealogy,
        "@I1@",
        generations=2,
    )

    assert [
        (
            occurrence.sosa,
            occurrence.person_id,
            occurrence.generation,
        )
        for occurrence in occurrences
    ] == [
        (1, "@I1@", 0),
        (2, "@I2@", 1),
        (3, "@I3@", 1),
        (4, "@I4@", 2),
        (5, "@I5@", 2),
        (6, None, 2),
        (7, None, 2),
    ]


def test_missing_parent_positions_are_preserved():
    genealogy = make_genealogy()

    occurrences = build_sosa_ancestry(
        genealogy,
        "@I1@",
        generations=3,
    )

    assert len(occurrences) == 15

    by_sosa = {
        occurrence.sosa: occurrence
        for occurrence in occurrences
    }

    assert by_sosa[6].person_id is None
    assert by_sosa[7].person_id is None

    assert by_sosa[12].person_id is None
    assert by_sosa[13].person_id is None
    assert by_sosa[14].person_id is None
    assert by_sosa[15].person_id is None

def test_generation_zero_contains_only_root():
    genealogy = make_genealogy()

    occurrences = build_sosa_ancestry(
        genealogy,
        "@I1@",
        generations=0,
    )

    assert len(occurrences) == 1
    assert occurrences[0].sosa == 1
    assert occurrences[0].person_id == "@I1@"


def test_unknown_root():
    genealogy = make_genealogy()

    with pytest.raises(
        KeyError,
        match="Unknown person",
    ):
        build_sosa_ancestry(
            genealogy,
            "@UNKNOWN@",
            generations=3,
        )


def test_negative_generations():
    genealogy = make_genealogy()

    with pytest.raises(
        ValueError,
        match="generations must be zero or greater",
    ):
        build_sosa_ancestry(
            genealogy,
            "@I1@",
            generations=-1,
        )


def test_implex_keeps_multiple_occurrences():
    genealogy = make_genealogy()

    genealogy.families["@F3@"] = Family(
        id="@F3@",
        partners=["@I4@", "@I5@"],
        children=["@I3@"],
        father_id="@I4@",
        mother_id="@I5@",
    )

    occurrences = build_sosa_ancestry(
        genealogy,
        "@I1@",
        generations=2,
    )

    by_sosa = {
        occurrence.sosa: occurrence.person_id
        for occurrence in occurrences
    }

    assert by_sosa[4] == "@I4@"
    assert by_sosa[5] == "@I5@"

    # Same physical people, different ancestry occurrences.
    assert by_sosa[6] == "@I4@"
    assert by_sosa[7] == "@I5@"

def test_parent_role_does_not_depend_on_sex():
    genealogy = make_genealogy()

    genealogy.persons["@I2@"].sex = Sex.UNKNOWN
    genealogy.persons["@I3@"].sex = Sex.UNKNOWN

    occurrences = build_sosa_ancestry(
        genealogy,
        "@I1@",
        generations=1,
    )

    by_sosa = {
        occurrence.sosa: occurrence.person_id
        for occurrence in occurrences
    }

    assert by_sosa[2] == "@I2@"
    assert by_sosa[3] == "@I3@"
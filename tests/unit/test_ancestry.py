import pytest

from src.domain.models import Family, Genealogy, Person, Sex
from src.services.ancestry import get_ancestors, get_parents


def make_genealogy() -> Genealogy:
    persons = {
        "@I1@": Person(
            id="@I1@",
            given_names="Jean",
            surname="Dupont",
            sex=Sex.MALE,
        ),
        "@I2@": Person(
            id="@I2@",
            given_names="Marie",
            surname="Martin",
            sex=Sex.FEMALE,
        ),
        "@I3@": Person(
            id="@I3@",
            given_names="Paul",
            surname="Dupont",
            sex=Sex.MALE,
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
            partners=["@I1@", "@I2@"],
            children=["@I3@"],
        ),
        "@F2@": Family(
            id="@F2@",
            partners=["@I4@", "@I5@"],
            children=["@I1@"],
        ),
    }

    return Genealogy(
        persons=persons,
        families=families,
    )


def test_get_parents():
    genealogy = make_genealogy()

    parents = get_parents(genealogy, "@I3@")

    assert [person.id for person in parents] == [
        "@I1@",
        "@I2@",
    ]


def test_get_parents_when_unknown():
    genealogy = make_genealogy()

    assert get_parents(genealogy, "@I4@") == []


def test_get_ancestors_by_generation():
    genealogy = make_genealogy()

    ancestors = get_ancestors(genealogy, "@I3@")

    assert [
        (ancestor.person.id, ancestor.generation)
        for ancestor in ancestors
    ] == [
        ("@I3@", 0),
        ("@I1@", 1),
        ("@I2@", 1),
        ("@I4@", 2),
        ("@I5@", 2),
    ]


def test_limit_ancestry_generations():
    genealogy = make_genealogy()

    ancestors = get_ancestors(
        genealogy,
        "@I3@",
        generations=1,
    )

    assert [
        (ancestor.person.id, ancestor.generation)
        for ancestor in ancestors
    ] == [
        ("@I3@", 0),
        ("@I1@", 1),
        ("@I2@", 1),
    ]


def test_unknown_root_person():
    genealogy = make_genealogy()

    with pytest.raises(KeyError, match="Unknown person"):
        get_ancestors(genealogy, "@UNKNOWN@")


def test_negative_generation_limit():
    genealogy = make_genealogy()

    with pytest.raises(
        ValueError,
        match="generations must be zero or greater",
    ):
        get_ancestors(
            genealogy,
            "@I3@",
            generations=-1,
        )


def test_cycle_does_not_loop_forever():
    genealogy = make_genealogy()

    genealogy.families["@BROKEN@"] = Family(
        id="@BROKEN@",
        partners=["@I3@"],
        children=["@I4@"],
    )

    ancestors = get_ancestors(genealogy, "@I3@")

    ids = [ancestor.person.id for ancestor in ancestors]

    assert len(ids) == len(set(ids))
    assert set(ids) == {
        "@I1@",
        "@I2@",
        "@I3@",
        "@I4@",
        "@I5@",
    }

def test_format_ancestry():
    genealogy = make_genealogy()

    ancestors = get_ancestors(
        genealogy,
        "@I3@",
        generations=1,
    )

    from src.services.ancestry import format_ancestry

    text = format_ancestry(ancestors)

    assert text == (
        "G0 @I3@ Paul Dupont\n"
        "  G1 @I1@ Jean Dupont\n"
        "  G1 @I2@ Marie Martin"
    )
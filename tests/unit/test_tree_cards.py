from pathlib import Path

from src.domain.models import Event, EventDate, Genealogy, Person, Sex
from src.services.combined_tree import TreePersonOccurrence
from src.services.portraits import PortraitKind, PortraitResolver
from src.services.tree_cards import build_tree_person_card


def resolver(tmp_path):
    return PortraitResolver(tmp_path / "portraits.json", tmp_path / "portraits")


def test_card_preserves_sources_and_exposes_legacy_display_values(tmp_path):
    person = Person(
        id="@I1@",
        given_names="Marie Josette Louise",
        surname="d'Este",
        sex=Sex.FEMALE,
        events=[
            Event(type="BIRT", date=EventDate("01 FEB 1903")),
            Event(type="DEAT", date=EventDate("05 NOV 1989")),
        ],
    )
    card = build_tree_person_card(
        TreePersonOccurrence("person:root", "@I1@", 0),
        Genealogy(persons={person.id: person}),
        resolver(tmp_path),
    )

    assert card.given_names == "Marie Josette Louise"
    assert card.display_given_name == "Marie"
    assert card.surname == "d'Este"
    assert card.display_surname == "D'ESTE"
    assert card.birth_date == "01 FEB 1903"
    assert card.display_birth_date == "1 FEV 1903"
    assert card.death_date == "05 NOV 1989"
    assert card.display_death_date == "5 NOV 1989"
    assert card.portrait.kind is PortraitKind.FALLBACK_FEMALE


def test_unknown_or_broken_occurrence_has_no_invented_person_data(tmp_path):
    card = build_tree_person_card(
        TreePersonOccurrence(
            "person:missing", None, -1, missing_person_id="@MISSING@"
        ),
        Genealogy(),
        resolver(tmp_path),
    )

    assert card.is_unknown is True
    assert card.person_id is None
    assert card.given_names is None
    assert card.display_given_name is None
    assert card.birth_date is None
    assert card.display_birth_date is None
    assert card.portrait.kind is PortraitKind.FALLBACK_UNKNOWN

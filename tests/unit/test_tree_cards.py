from pathlib import Path

from src.domain.models import Event, EventDate, Genealogy, Person, Sex
from src.services.combined_tree import TreePersonOccurrence
from src.services.portraits import PortraitKind, PortraitResolver
import pytest

from src.services.tree_cards import build_tree_person_card, format_tree_date


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
    assert card.display_given_name == "Marie Josette Louise"
    assert card.surname == "d'Este"
    assert card.display_surname == "D'ESTE"
    assert card.birth_date == "01 FEB 1903"
    assert card.display_birth_date == "1 FEV 1903"
    assert card.death_date == "05 NOV 1989"
    assert card.display_death_date == "5 NOV 1989"
    assert card.portrait.kind is PortraitKind.FALLBACK_FEMALE


def test_card_keeps_all_given_names_and_variant_separator(tmp_path):
    person = Person(
        id="@I31@",
        given_names="Dwojra / Rachel",
        surname="ZYLBERSZTAJN",
        sex=Sex.FEMALE,
    )
    card = build_tree_person_card(
        TreePersonOccurrence("person:root", "@I31@", 0),
        Genealogy(persons={person.id: person}),
        resolver(tmp_path),
    )

    assert card.given_names == "Dwojra / Rachel"
    assert card.display_given_name == "Dwojra / Rachel"
    assert card.surname == "ZYLBERSZTAJN"
    assert card.display_surname == "ZYLBERSZTAJN"


def test_card_preserves_long_given_and_compound_surname_without_truncation(tmp_path):
    person = Person(
        id="@I1@",
        given_names="Marie Josephine Alexandrine Catherine",
        surname="DE LA ROCHE-SAINT-ANDRÉ",
    )
    card = build_tree_person_card(
        TreePersonOccurrence("person:root", "@I1@", 0),
        Genealogy(persons={person.id: person}),
        resolver(tmp_path),
    )

    assert card.display_given_name == "Marie Josephine Alexandrine Catherine"
    assert card.display_surname == "DE LA ROCHE-SAINT-ANDRÉ"


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


@pytest.mark.parametrize(
    ("source", "display"),
    [
        ("ABOUT 1850", "~ 1850"),
        ("ABT 1850", "~ 1850"),
        ("BEFORE 1900", "< 1900"),
        ("BEF 1900", "< 1900"),
        ("AFTER 1875", "> 1875"),
        ("AFT 1875", "> 1875"),
    ],
)
def test_tree_date_formats_approximate_qualifiers_only_for_presentation(source, display):
    assert format_tree_date(source) == display


def test_tree_date_preserves_ordinary_gedcom_formats_and_absence():
    assert format_tree_date("01 FEB 1903") == "1 FEV 1903"
    assert format_tree_date("BETWEEN 1970 AND 1975") == "BETWEEN 1970 AND 1975"
    assert format_tree_date(None) is None


def test_tree_card_keeps_approximate_gedcom_values_while_formatting_display(tmp_path):
    person = Person(
        id="@I1@",
        sex=Sex.UNKNOWN,
        events=[
            Event(type="BIRT", date=EventDate("ABOUT 1850")),
            Event(type="DEAT", date=EventDate("BEF 1900")),
        ],
    )
    card = build_tree_person_card(
        TreePersonOccurrence("person:root", "@I1@", 0),
        Genealogy(persons={person.id: person}),
        resolver(tmp_path),
    )

    assert card.birth_date == "ABOUT 1850"
    assert card.display_birth_date == "~ 1850"
    assert card.death_date == "BEF 1900"
    assert card.display_death_date == "< 1900"

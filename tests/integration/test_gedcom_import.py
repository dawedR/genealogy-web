from pathlib import Path

from src.domain.models import Sex
from src.gedcom.importer import import_gedcom


FIXTURE = Path("tests/fixtures/gedcom-edge-cases.ged")


def test_import_edge_cases():
    genealogy, report = import_gedcom(FIXTURE)

    # Global structure
    assert len(genealogy.persons) == 3
    assert len(genealogy.families) == 1

    # Unicode and approximate date
    eleonore = genealogy.persons["@I1@"]
    assert eleonore.given_names == "Éléonore"
    assert eleonore.surname == "ŻÓŁĆ"
    assert eleonore.sex == Sex.FEMALE

    birth = next(event for event in eleonore.events if event.type == "BIRT")
    assert birth.date is not None
    assert birth.date.value == "ABOUT 1901"
    assert birth.place is not None
    assert birth.place.original_name == "Łódź, Pologne"

    death = next(event for event in eleonore.events if event.type == "DEAT")
    assert death.date is not None
    assert death.date.value == "BEFORE 1980"

    # Date range
    jean = genealogy.persons["@I2@"]
    death = next(event for event in jean.events if event.type == "DEAT")
    assert death.date is not None
    assert death.date.value == "BETWEEN 1970 AND 1975"

    burial = next(event for event in eleonore.events if event.type == "BURI")
    assert burial.date is not None
    assert burial.date.value == "1980"
    assert burial.place is not None
    assert burial.place.original_name == "Łódź, Pologne"

    # FROM ... TO ...
    marie = genealogy.persons["@I3@"]
    birth = next(event for event in marie.events if event.type == "BIRT")
    assert birth.date is not None
    assert birth.date.value == "FROM 1902 TO 1904"

    baptism = next(event for event in marie.events if event.type == "BAPM")
    assert baptism.date is not None
    assert baptism.date.value == "1904"
    assert baptism.place is not None
    assert baptism.place.original_name == "Écully, France"

    # Family relationships
    family = genealogy.families["@F1@"]
    assert family.partners == ["@I2@", "@I1@"]
    assert family.children == ["@I3@"]

    marriage = next(event for event in family.events if event.type == "MARR")
    assert marriage.date is not None
    assert marriage.date.value == "1925"
    assert marriage.place is not None
    assert marriage.place.original_name == "Écully, France"

    # Import report
    assert report.persons_count == 3
    assert report.families_count == 1

    assert report.events_count == 8
    assert report.places_count == 2

    assert {place.original_name for place in genealogy.places} == {
        "Łódź, Pologne",
        "Écully, France",
    }
from src.domain.models import (
    Event,
    EventDate,
    Family,
    Genealogy,
    Person,
    Place,
    Sex,
)


def test_create_person_with_birth_event():
    place = Place(original_name="Paris, France")
    date = EventDate(value="ABOUT 1884")

    birth = Event(
        type="BIRT",
        date=date,
        place=place,
    )

    person = Person(
        id="@I1@",
        given_names="Jean",
        surname="Dupont",
        sex=Sex.MALE,
        events=[birth],
    )

    assert person.id == "@I1@"
    assert person.given_names == "Jean"
    assert person.surname == "Dupont"
    assert person.sex == Sex.MALE

    assert len(person.events) == 1
    assert person.events[0].type == "BIRT"
    assert person.events[0].date.value == "ABOUT 1884"
    assert person.events[0].place.original_name == "Paris, France"


def test_create_family_relationships():
    family = Family(
        id="@F1@",
        partners=["@I1@", "@I2@"],
        children=["@I3@"],
    )

    assert family.partners == ["@I1@", "@I2@"]
    assert family.children == ["@I3@"]


def test_genealogy_stores_entities_by_identifier():
    person = Person(id="@I1@", given_names="Jean", surname="Dupont")
    family = Family(id="@F1@")

    genealogy = Genealogy(
        persons={person.id: person},
        families={family.id: family},
    )

    assert genealogy.persons["@I1@"] is person
    assert genealogy.families["@F1@"] is family


def test_partial_date_is_preserved_semantically():
    date = EventDate(value="BETWEEN 1970 AND 1975")

    assert date.value == "BETWEEN 1970 AND 1975"
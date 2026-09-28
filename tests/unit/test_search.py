from src.domain.models import (
    Event,
    EventDate,
    Genealogy,
    Person,
)
from src.services.search import (
    get_birth_date,
    get_birth_year,
    search_people,
)

def make_genealogy() -> Genealogy:
    people = [
        Person(
            id="@I1@",
            given_names="Maurice",
            surname="ZYLBERBERG",
        ),
        Person(
            id="@I2@",
            given_names="Éléonore",
            surname="ŻÓŁĆ",
        ),
        Person(
            id="@I3@",
            given_names="Marie",
            surname="DUPONT",
        ),
    ]

    return Genealogy(
        persons={person.id: person for person in people}
    )


def test_search_by_surname():
    genealogy = make_genealogy()

    results = search_people(genealogy, "zylberberg")

    assert [person.id for person in results] == ["@I1@"]


def test_search_is_case_insensitive():
    genealogy = make_genealogy()

    results = search_people(genealogy, "MAURICE")

    assert [person.id for person in results] == ["@I1@"]


def test_search_ignores_accents():
    genealogy = make_genealogy()

    results = search_people(genealogy, "eleonore")

    assert [person.id for person in results] == ["@I2@"]


def test_empty_search_returns_nothing():
    genealogy = make_genealogy()

    assert search_people(genealogy, "   ") == []


def test_search_limit():
    genealogy = Genealogy(
        persons={
            f"@I{index}@": Person(
                id=f"@I{index}@",
                given_names=f"Jean {index}",
                surname="DUPONT",
            )
            for index in range(10)
        }
    )

    results = search_people(
        genealogy,
        "dupont",
        limit=3,
    )

    assert len(results) == 3

def test_birth_date_and_year():
    person = Person(
        id="@I10@",
        given_names="Jean",
        surname="Dupont",
        events=[
            Event(
                type="BIRT",
                date=EventDate(
                    value="17 JUL 1946"
                ),
            )
        ],
    )

    assert get_birth_date(person) == "17 JUL 1946"
    assert get_birth_year(person) == "1946"


def test_approximate_birth_year():
    person = Person(
        id="@I10@",
        events=[
            Event(
                type="BIRT",
                date=EventDate(
                    value="ABOUT 1901"
                ),
            )
        ],
    )

    assert get_birth_year(person) == "1901"


def test_search_by_name_and_birth_year():
    people = [
        Person(
            id="@I1@",
            given_names="Jean",
            surname="Dupont",
            events=[
                Event(
                    type="BIRT",
                    date=EventDate(value="1901"),
                )
            ],
        ),
        Person(
            id="@I2@",
            given_names="Jean",
            surname="Dupont",
            events=[
                Event(
                    type="BIRT",
                    date=EventDate(value="1932"),
                )
            ],
        ),
    ]

    genealogy = Genealogy(
        persons={
            person.id: person
            for person in people
        }
    )

    results = search_people(
        genealogy,
        "Jean Dupont 1932",
    )

    assert [person.id for person in results] == [
        "@I2@"
    ]


def test_search_by_birth_year_only():
    people = [
        Person(
            id="@I1@",
            given_names="Jean",
            surname="Dupont",
            events=[
                Event(
                    type="BIRT",
                    date=EventDate(value="1901"),
                )
            ],
        ),
        Person(
            id="@I2@",
            given_names="Marie",
            surname="Martin",
            events=[
                Event(
                    type="BIRT",
                    date=EventDate(value="1932"),
                )
            ],
        ),
    ]

    genealogy = Genealogy(
        persons={
            person.id: person
            for person in people
        }
    )

    results = search_people(
        genealogy,
        "1932",
    )

    assert [person.id for person in results] == [
        "@I2@"
    ]
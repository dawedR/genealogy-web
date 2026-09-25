from src.domain.models import Genealogy, Person
from src.services.search import search_people


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
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.domain.models import Family, Genealogy, Person, Sex


def make_genealogy() -> Genealogy:
    persons = {
        "@I1@": Person(
            id="@I1@",
            given_names="Jean",
            surname="Dupont",
            sex=Sex.MALE,
            occupations=["Cordonnier"],
        ),
        "@I2@": Person(
            id="@I2@",
            given_names="Éléonore",
            surname="ŻÓŁĆ",
            sex=Sex.FEMALE,
        ),
        "@I3@": Person(
            id="@I3@",
            given_names="Paul",
            surname="Dupont",
            sex=Sex.MALE,
        ),
    }

    families = {
        "@F1@": Family(
            id="@F1@",
            partners=["@I1@", "@I2@"],
            children=["@I3@"],
        )
    }

    return Genealogy(
        persons=persons,
        families=families,
    )


def make_client() -> TestClient:
    return TestClient(
        create_app(make_genealogy())
    )


def test_health():
    with make_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "persons_count": 3,
        "families_count": 1,
    }


def test_search_people():
    with make_client() as client:
        response = client.get(
            "/people",
            params={"q": "dupont"},
        )

    assert response.status_code == 200

    data = response.json()

    assert [person["id"] for person in data] == [
        "@I1@",
        "@I3@",
    ]


def test_search_people_ignores_accents():
    with make_client() as client:
        response = client.get(
            "/people",
            params={"q": "eleonore"},
        )

    assert response.status_code == 200
    assert response.json()[0]["id"] == "@I2@"


def test_get_person():
    with make_client() as client:
        response = client.get("/people/@I1@")

    assert response.status_code == 200

    assert response.json() == {
        "id": "@I1@",
        "given_names": "Jean",
        "surname": "Dupont",
        "sex": "M",
        "occupations": ["Cordonnier"],
    }


def test_unknown_person_returns_404():
    with make_client() as client:
        response = client.get("/people/@UNKNOWN@")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Person not found",
    }


def test_get_ancestors():
    with make_client() as client:
        response = client.get(
            "/people/@I3@/ancestors",
            params={"generations": 1},
        )

    assert response.status_code == 200

    data = response.json()

    assert [
        (
            ancestor["person"]["id"],
            ancestor["generation"],
        )
        for ancestor in data
    ] == [
        ("@I3@", 0),
        ("@I1@", 1),
        ("@I2@", 1),
    ]


def test_ancestor_generation_limit_is_validated():
    with make_client() as client:
        response = client.get(
            "/people/@I3@/ancestors",
            params={"generations": -1},
        )

    assert response.status_code == 422

from pathlib import Path


GEDCOM_FIXTURE = Path(
    "tests/fixtures/gedcom-edge-cases.ged"
)


def test_upload_gedcom_replaces_active_genealogy():
    with make_client() as client:
        before = client.get("/health")

        assert before.json()["persons_count"] == 3

        with GEDCOM_FIXTURE.open("rb") as gedcom_file:
            response = client.post(
                "/imports",
                files={
                    "file": (
                        "edge-cases.ged",
                        gedcom_file,
                        "application/octet-stream",
                    )
                },
            )

        assert response.status_code == 200

        report = response.json()

        assert report["filename"] == "edge-cases.ged"
        assert report["persons_count"] == 3
        assert report["families_count"] == 1
        assert report["events_count"] == 11
        assert report["places_count"] == 2
        assert report["warnings"] == []
        assert report["ignored_tags"] == [
            {
                "tag": "_CUSTOM",
                "record_id": "@I1@",
            }
        ]

        person = client.get("/people/@I2@")

        assert person.status_code == 200
        assert person.json()["given_names"] == "Jean"
        assert person.json()["occupations"] == [
            "Cordonnier"
        ]


def test_uploaded_genealogy_can_be_searched():
    with make_client() as client:
        with GEDCOM_FIXTURE.open("rb") as gedcom_file:
            response = client.post(
                "/imports",
                files={
                    "file": (
                        "edge-cases.ged",
                        gedcom_file,
                        "application/octet-stream",
                    )
                },
            )

        assert response.status_code == 200

        response = client.get(
            "/people",
            params={"q": "eleonore"},
        )

        assert response.status_code == 200
        assert response.json()[0]["id"] == "@I1@"


def test_failed_import_keeps_previous_genealogy():
    invalid_gedcom = b"This is not a GEDCOM file."

    with make_client() as client:
        before = client.get("/health").json()

        response = client.post(
            "/imports",
            files={
                "file": (
                    "broken.ged",
                    invalid_gedcom,
                    "application/octet-stream",
                )
            },
        )

        assert response.status_code == 400

        after = client.get("/health").json()

        assert after == before

        person = client.get("/people/@I1@")

        assert person.status_code == 200
        assert person.json()["given_names"] == "Jean"
from urllib import response

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
        "birth_date": None,
        "birth_year": None,
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
        assert report["persons_count"] == 4
        assert report["families_count"] == 1
        assert report["events_count"] == 11
        assert report["places_count"] == 2
        assert report["warnings"] == [
            "@I4@: valeur SEX non reconnue : X"
        ]
        assert report["ignored_tags"] == [
            {
                "tag": "_CUSTOM",
                "record_id": "@I1@",
            },
            {
                "tag": "UNKNOWN",
                "record_id": "@I4@",
            },
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

def test_index_page():
    with make_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Genealogy Web" in response.text
    assert 'id="import-form"' in response.text
    assert 'id="search-form"' in response.text
    assert 'id="warnings-section"' in response.text
    assert 'id="ignored-tags-section"' in response.text
    assert 'id="fan-opening"' in response.text
    assert 'id="fan-chart"' in response.text


def test_static_javascript():
    with make_client() as client:
        response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "loadAncestry" in response.text
    assert "renderImportDetails" in response.text
    assert "createFanGeometry" in response.text
    assert "setFanViewBox" in response.text
    assert "labelTransform" in response.text

def test_search_uploaded_people_by_birth_year():
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
            params={"q": "Jean Dupont 1900"},
        )

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 1
        assert data[0]["id"] == "@I2@"
        assert data[0]["birth_date"] == "1900"
        assert data[0]["birth_year"] == "1900"

def test_get_sosa_ancestry():
    genealogy = make_genealogy()

    genealogy.families["@F1@"].father_id = "@I1@"
    genealogy.families["@F1@"].mother_id = "@I2@"

    with TestClient(create_app(genealogy)) as client:
        response = client.get(
            "/people/@I3@/sosa",
            params={"generations": 1},
        )

    assert response.status_code == 200

    data = response.json()

    assert [
        (
            item["sosa"],
            item["generation"],
            (
                item["person"]["id"]
                if item["person"] is not None
                else None
            ),
        )
        for item in data
    ] == [
        (1, 0, "@I3@"),
        (2, 1, "@I1@"),
        (3, 1, "@I2@"),
    ]


def test_sosa_keeps_unknown_positions():
    genealogy = make_genealogy()

    genealogy.families["@F1@"].father_id = "@I1@"
    genealogy.families["@F1@"].mother_id = "@I2@"

    with TestClient(create_app(genealogy)) as client:
        response = client.get(
            "/people/@I3@/sosa",
            params={"generations": 2},
        )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 7

    by_sosa = {
        item["sosa"]: item
        for item in data
    }

    assert by_sosa[4]["person"] is None
    assert by_sosa[5]["person"] is None
    assert by_sosa[6]["person"] is None
    assert by_sosa[7]["person"] is None


def test_sosa_generation_limit():
    with make_client() as client:
        too_small = client.get(
            "/people/@I3@/sosa",
            params={"generations": 0},
        )

        too_large = client.get(
            "/people/@I3@/sosa",
            params={"generations": 11},
        )

    assert too_small.status_code == 422
    assert too_large.status_code == 422
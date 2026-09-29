from urllib import response

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.domain.models import (
    Event,
    Family,
    Genealogy,
    Person,
    Place,
    PlaceEnrichment,
    PlaceEnrichmentStatus,
    Sex,
)
from src.services.geocoding import (
    FakeGeocoder,
    GeocodingCandidate,
    GeocodingNetworkError,
    GeocodingProviderError,
    GeocodingRequestRejectedError,
    GeocodingResponseError,
    GeocodingTimeoutError,
)
from src.storage.place_enrichments import InMemoryPlaceEnrichmentStore


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


def test_get_places_inventory():
    genealogy = make_genealogy()
    genealogy.persons["@I1@"].events.append(
        Event(type="BIRT", place=Place(original_name="Écully, France"))
    )
    genealogy.persons["@I2@"].events.append(
        Event(type="DEAT", place=Place(original_name="Lyon, France"))
    )
    genealogy.families["@F1@"].events.append(
        Event(type="MARR", place=Place(original_name="Écully, France"))
    )

    with TestClient(create_app(genealogy)) as client:
        response = client.get("/places")

    assert response.status_code == 200
    assert response.json() == [
        {
            "original_name": "Écully, France",
            "occurrences_count": 2,
            "persons_count": 2,
            "event_counts": {"BIRT": 1, "MARR": 1},
            "enrichment": None,
        },
        {
            "original_name": "Lyon, France",
            "occurrences_count": 1,
            "persons_count": 1,
            "event_counts": {"DEAT": 1},
            "enrichment": None,
        },
    ]


def test_upsert_place_enrichment_and_expose_it_in_inventory():
    genealogy = make_genealogy()
    genealogy.persons["@I1@"].events.append(
        Event(type="BIRT", place=Place(original_name="Ecully"))
    )
    store = InMemoryPlaceEnrichmentStore()

    with TestClient(create_app(genealogy, store)) as client:
        response = client.put(
            "/place-enrichments",
            json={
                "original_name": "Ecully",
                "normalized_name": "Écully",
                "latitude": 45.776,
                "longitude": 4.778,
                "comment": "Saisie manuelle",
            },
        )

        places = client.get("/places")

    assert response.status_code == 200
    assert response.json() == {
        "original_name": "Ecully",
        "normalized_name": "Écully",
        "latitude": 45.776,
        "longitude": 4.778,
        "status": "MANUAL",
        "source": None,
        "confidence": None,
        "comment": "Saisie manuelle",
    }
    assert places.json()[0]["enrichment"] == response.json()


def test_place_enrichment_rejects_unknown_places_and_invalid_coordinates():
    genealogy = make_genealogy()
    genealogy.persons["@I1@"].events.append(
        Event(type="BIRT", place=Place(original_name="Ecully"))
    )

    with TestClient(create_app(genealogy)) as client:
        missing = client.put(
            "/place-enrichments",
            json={"original_name": "Écully"},
        )
        invalid = client.put(
            "/place-enrichments",
            json={"original_name": "Ecully", "latitude": 90.1},
        )

    assert missing.status_code == 404
    assert missing.json() == {"detail": "Place not found"}
    assert invalid.status_code == 422
    assert "latitude" in invalid.json()["detail"]


def test_place_enrichment_survives_rebuilt_genealogy_only_for_exact_label():
    store = InMemoryPlaceEnrichmentStore()
    initial = Genealogy(
        persons={
            "@I1@": Person(
                id="@I1@",
                events=[Event(type="BIRT", place=Place(original_name="Ecully"))],
            )
        }
    )

    with TestClient(create_app(initial, store)) as client:
        response = client.put(
            "/place-enrichments",
            json={"original_name": "Ecully", "comment": "Conserver"},
        )

    rebuilt = Genealogy(
        persons={
            "@I2@": Person(
                id="@I2@",
                events=[
                    Event(type="DEAT", place=Place(original_name="Ecully")),
                    Event(type="BIRT", place=Place(original_name="Écully")),
                ],
            )
        }
    )

    with TestClient(create_app(rebuilt, store)) as client:
        places = client.get("/places")

    assert response.status_code == 200
    by_name = {place["original_name"]: place for place in places.json()}
    assert by_name["Ecully"]["enrichment"]["comment"] == "Conserver"
    assert by_name["Écully"]["enrichment"] is None

def test_geocoding_candidates_and_explicit_geoapify_selection():
    genealogy = make_genealogy()
    genealogy.persons["@I1@"].events.append(
        Event(type="BIRT", place=Place(original_name="Lyon 4 ?"))
    )
    candidates = [
        GeocodingCandidate(
            provider="geoapify",
            provider_id="first",
            display_name="Lyon 4e Arrondissement, France",
            latitude=45.78,
            longitude=4.83,
            city="Lyon",
            postcode="69004",
            region="Auvergne-Rhône-Alpes",
            country="France",
        ),
        GeocodingCandidate(
            provider="geoapify",
            provider_id="second",
            display_name="Autre Lyon",
            latitude=45.79,
            longitude=4.84,
        ),
    ]
    geocoder = FakeGeocoder(
        {"Lyon 4e arrondissement, France": candidates}
    )
    store = InMemoryPlaceEnrichmentStore()

    with TestClient(create_app(genealogy, store, geocoder)) as client:
        searched = client.post(
            "/geocoding/candidates",
            json={
                "original_name": "Lyon 4 ?",
                "query": "Lyon 4e arrondissement, France",
            },
        )
        token = searched.json()[0]["selection_token"]
        selected = client.post(
            "/place-enrichments/geoapify-selection",
            json={
                "original_name": "Lyon 4 ?",
                "candidate_token": token,
            },
        )
        places = client.get("/places")

    assert geocoder.queries == [("Lyon 4e arrondissement, France", 5)]
    assert searched.status_code == 200
    assert len(searched.json()) == 2
    assert searched.json()[0]["city"] == "Lyon"
    assert selected.json() == {
        "original_name": "Lyon 4 ?",
        "normalized_name": "Lyon 4e Arrondissement, France",
        "latitude": 45.78,
        "longitude": 4.83,
        "status": "MANUAL",
        "source": "geoapify",
        "confidence": None,
        "comment": None,
    }
    assert places.json()[0]["enrichment"] == selected.json()


def test_geocoding_returns_no_candidates_for_unicode_query():
    genealogy = make_genealogy()
    genealogy.persons["@I1@"].events.append(
        Event(type="BIRT", place=Place(original_name="Łódź, Pologne"))
    )
    geocoder = FakeGeocoder({"Łódź, Pologne": []})

    with TestClient(create_app(genealogy, geocoder=geocoder)) as client:
        response = client.post(
            "/geocoding/candidates",
            json={"original_name": "Łódź, Pologne"},
        )

    assert response.status_code == 200
    assert response.json() == []
    assert geocoder.queries == [("Łódź, Pologne", 5)]


def test_geocoding_does_not_accept_an_arbitrary_candidate_token():
    genealogy = make_genealogy()
    genealogy.persons["@I1@"].events.append(
        Event(type="BIRT", place=Place(original_name="Ecully"))
    )

    with TestClient(create_app(genealogy, geocoder=FakeGeocoder())) as client:
        selected = client.post(
            "/place-enrichments/geoapify-selection",
            json={"original_name": "Ecully", "candidate_token": "forged"},
        )
        missing = client.post(
            "/geocoding/candidates",
            json={"original_name": "Écully"},
        )

    assert selected.status_code == 404
    assert missing.status_code == 404


def test_geocoding_errors_are_distinct_and_safe():
    genealogy = make_genealogy()
    genealogy.persons["@I1@"].events.append(
        Event(type="BIRT", place=Place(original_name="Radoszyce"))
    )

    cases = [
        (None, 503, "n’est pas configuré"),
        (GeocodingRequestRejectedError(400), 422, "HTTP 400"),
        (GeocodingTimeoutError(), 504, "a expiré"),
        (GeocodingNetworkError(), 502, "réseau"),
        (GeocodingResponseError(), 502, "impossible à interpréter"),
        (GeocodingProviderError("détail interne"), 502, "a échoué"),
    ]

    for error, expected_status, expected_message in cases:
        geocoder = None
        if error is not None:
            geocoder = FakeGeocoder()
            geocoder.error = error

        with TestClient(create_app(genealogy, geocoder=geocoder)) as client:
            response = client.post(
                "/geocoding/candidates",
                json={"original_name": "Radoszyce"},
            )

        assert response.status_code == expected_status
        assert expected_message in response.json()["detail"]
        assert "détail interne" not in response.json()["detail"]


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
        "birth_place": None,
        "death_date": None,
        "death_year": None,
        "death_place": None,
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
    for element_id in (
        "places-status",
        "places-table",
        "places-list",
        "place-enrichment-form",
        "place-enrichment-original-name",
        "place-enrichment-status",
        "place-enrichment-normalized-name",
        "place-enrichment-latitude",
        "place-enrichment-longitude",
        "place-enrichment-comment",
        "place-enrichment-validate",
        "place-geocoding-query",
        "place-geocoding-search",
        "place-geocoding-results",
    ):
        assert f'id="{element_id}"' in response.text

    assert 'id="fan-opening"' in response.text
    assert 'id="fan-chart"' in response.text
    assert 'id="fan-legend"' in response.text
    assert 'id="fan-legend-list"' in response.text
    assert 'id="fan-label-sosa"' in response.text
    assert 'id="fan-label-name"' in response.text
    assert 'id="fan-label-birth"' in response.text
    assert 'id="fan-label-death"' in response.text


def test_static_javascript():
    with make_client() as client:
        response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "loadAncestry" in response.text
    assert "loadPlaces" in response.text
    assert "selectPlace" in response.text
    assert "optionalCoordinate" in response.text
    assert "formatPlaceEventCounts" in response.text
    assert "renderGeocodingCandidates" in response.text
    assert "selectGeocodingCandidate" in response.text
    assert "placeStatusLabel" in response.text
    assert "place-enrichments/validate" in response.text
    assert "loadFanChart(person.id);" in response.text
    assert "renderImportDetails" in response.text
    assert "createFanGeometry" in response.text
    assert "setFanViewBox" in response.text
    assert "labelTransform" in response.text
    assert "getFanLabelConfig" in response.text
    assert "buildPersonLabelVariants" in response.text
    assert "buildSecondaryLabelLines" in response.text
    assert "abbreviatePersonName" in response.text
    assert "formatEventLabel" in response.text
    assert "renderFanLegend" in response.text
    assert "legendEntryForOccurrence" in response.text
    assert "compareLegendEntries" in response.text
    assert "${occurrence.color_kind}:${occurrence.birth_place_original_name}" in response.text
    assert "Non vérifié" in response.text
    assert "existing.occurrencesCount += 1" in response.text
    assert "occurrence.person === null && !showUnknown" in response.text
    assert "second.occurrencesCount - first.occurrencesCount" in response.text


def test_static_javascript_loads_fan_chart_when_selecting_a_person():
    with make_client() as client:
        response = client.get("/static/app.js")

    assert response.status_code == 200

    selection_start = response.text.index(
        'button.addEventListener("click", () => {'
    )
    selection_end = response.text.index(
        "item.appendChild(button);",
        selection_start,
    )
    selection_handler = response.text[selection_start:selection_end]

    assert selection_handler.index("loadAncestry(person.id);") < (
        selection_handler.index("loadFanChart(person.id);")
    )


def test_static_javascript_uses_ordered_label_degradation():
    with make_client() as client:
        response = client.get("/static/app.js")

    assert response.status_code == 200

    script = response.text

    variants_start = script.index("function buildPersonLabelVariants")
    variants_end = script.index(
        "function buildPrimaryLabelLines",
        variants_start,
    )
    variants = script[variants_start:variants_end]

    assert '"full"' in variants
    assert '"year"' in variants
    assert variants.index('"full"') < variants.index('"year"')
    assert "config,\n            true," in variants
    assert "abbreviatePersonName" in script
    assert "buildPersonLabelLines" not in script
    assert 'precision === "year"' in script
    assert "variants[variants.length - 1]" in script

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

def test_validate_existing_manual_enrichment_and_reject_incomplete_coordinates():
    genealogy = make_genealogy()
    genealogy.persons["@I1@"].events.append(
        Event(type="BIRT", place=Place(original_name="Ecully"))
    )
    store = InMemoryPlaceEnrichmentStore()

    with TestClient(create_app(genealogy, store)) as client:
        created = client.put(
            "/place-enrichments",
            json={
                "original_name": "Ecully",
                "normalized_name": "Écully",
                "latitude": 45.776,
                "longitude": 4.778,
                "comment": None,
            },
        )
        validated = client.post(
            "/place-enrichments/validate",
            json={"original_name": "Ecully"},
        )

        incomplete = client.put(
            "/place-enrichments",
            json={
                "original_name": "Ecully",
                "normalized_name": "Écully",
                "latitude": None,
                "longitude": None,
                "comment": None,
            },
        )
        rejected = client.post(
            "/place-enrichments/validate",
            json={"original_name": "Ecully"},
        )
        absent = client.post(
            "/place-enrichments/validate",
            json={"original_name": "Lyon"},
        )
        store.save(
            PlaceEnrichment(
                original_name="Orphelin",
                latitude=45.0,
                longitude=4.0,
                status=PlaceEnrichmentStatus.MANUAL,
            )
        )
        orphan = client.post(
            "/place-enrichments/validate",
            json={"original_name": "Orphelin"},
        )

    assert created.json()["status"] == "MANUAL"
    assert validated.json()["status"] == "VALIDATED"
    assert incomplete.json()["status"] == "MANUAL"
    assert rejected.status_code == 422
    assert "VALIDATED" in rejected.json()["detail"]
    assert absent.status_code == 404
    assert orphan.status_code == 404


def test_editing_validated_enrichment_applies_provenance_rules():
    genealogy = make_genealogy()
    genealogy.persons["@I1@"].events.append(
        Event(type="BIRT", place=Place(original_name="Ecully"))
    )
    store = InMemoryPlaceEnrichmentStore()

    def validated_enrichment():
        return PlaceEnrichment(
            original_name="Ecully",
            normalized_name="Écully",
            latitude=45.776,
            longitude=4.778,
            status=PlaceEnrichmentStatus.VALIDATED,
            source="geoapify",
            confidence=0.9,
            comment="Initial",
        )

    with TestClient(create_app(genealogy, store)) as client:
        store.save(validated_enrichment())
        comment_only = client.put(
            "/place-enrichments",
            json={
                "original_name": "Ecully",
                "normalized_name": "Écully",
                "latitude": 45.776,
                "longitude": 4.778,
                "comment": "Documenté",
            },
        )

        store.save(validated_enrichment())
        normalized_name = client.put(
            "/place-enrichments",
            json={
                "original_name": "Ecully",
                "normalized_name": "Écully (Rhône)",
                "latitude": 45.776,
                "longitude": 4.778,
                "comment": "Initial",
            },
        )

        store.save(validated_enrichment())
        coordinates = client.put(
            "/place-enrichments",
            json={
                "original_name": "Ecully",
                "normalized_name": "Écully",
                "latitude": 45.777,
                "longitude": 4.778,
                "comment": "Initial",
            },
        )

    assert comment_only.json()["status"] == "VALIDATED"
    assert comment_only.json()["source"] == "geoapify"
    assert comment_only.json()["confidence"] == 0.9
    assert normalized_name.json()["status"] == "MANUAL"
    assert normalized_name.json()["source"] == "geoapify"
    assert normalized_name.json()["confidence"] is None
    assert coordinates.json()["status"] == "MANUAL"
    assert coordinates.json()["source"] is None
    assert coordinates.json()["confidence"] is None


def test_sosa_places_endpoint_keeps_missing_places_and_enrichment_statuses():
    genealogy = Genealogy(
        persons={
            "@I1@": Person(
                id="@I1@",
                events=[Event(type="BIRT", place=Place(original_name="Manuel"))],
            ),
            "@I2@": Person(
                id="@I2@",
                events=[Event(type="BIRT", place=Place(original_name="Sans enrichissement"))],
            ),
            "@I3@": Person(
                id="@I3@",
                events=[Event(type="BIRT", place=Place(original_name="Validé"))],
            ),
        },
        families={
            "@F1@": Family(
                id="@F1@",
                children=["@I1@"],
                father_id="@I2@",
                mother_id="@I3@",
            ),
        },
    )
    store = InMemoryPlaceEnrichmentStore()
    store.save(
        PlaceEnrichment(
            original_name="Manuel",
            latitude=45.0,
            longitude=4.0,
            status=PlaceEnrichmentStatus.MANUAL,
        )
    )
    store.save(
        PlaceEnrichment(
            original_name="Validé",
            latitude=46.0,
            longitude=5.0,
            status=PlaceEnrichmentStatus.VALIDATED,
        )
    )

    with TestClient(create_app(genealogy, store)) as client:
        response = client.get(
            "/people/@I1@/sosa/places",
            params={"generations": 2},
        )

    assert response.status_code == 200
    assert [
        (
            item["sosa"],
            item["person_id"],
            item["birth_place_original_name"],
            item["enrichment"]["status"] if item["enrichment"] else None,
        )
        for item in response.json()
    ] == [
        (1, "@I1@", "Manuel", "MANUAL"),
        (2, "@I2@", "Sans enrichissement", None),
        (3, "@I3@", "Validé", "VALIDATED"),
        (4, None, None, None),
        (5, None, None, None),
        (6, None, None, None),
        (7, None, None, None),
    ]


def test_sosa_birth_place_colors_are_computed_server_side():
    genealogy = Genealogy(
        persons={
            "@I1@": Person(
                id="@I1@",
                events=[Event(type="BIRT", place=Place(original_name="Racine"))],
            ),
            "@I2@": Person(
                id="@I2@",
                events=[Event(type="BIRT", place=Place(original_name="Validé"))],
            ),
            "@I3@": Person(
                id="@I3@",
                events=[Event(type="BIRT", place=Place(original_name="Manuel"))],
            ),
        },
        families={
            "@F1@": Family(
                id="@F1@",
                children=["@I1@"],
                father_id="@I2@",
                mother_id="@I3@",
            ),
        },
    )
    store = InMemoryPlaceEnrichmentStore()
    store.save(
        PlaceEnrichment(
            original_name="Racine",
            latitude=45.7484,
            longitude=4.8256,
            status=PlaceEnrichmentStatus.VALIDATED,
        )
    )
    store.save(
        PlaceEnrichment(
            original_name="Validé",
            normalized_name="Lieu validé",
            latitude=46.0,
            longitude=5.0,
            status=PlaceEnrichmentStatus.VALIDATED,
        )
    )
    store.save(
        PlaceEnrichment(
            original_name="Manuel",
            latitude=45.0,
            longitude=4.0,
            status=PlaceEnrichmentStatus.MANUAL,
        )
    )

    with TestClient(create_app(genealogy, store)) as client:
        response = client.get(
            "/people/@I1@/sosa",
            params={"generations": 2, "color_mode": "BIRTH_PLACE"},
        )

    assert response.status_code == 200
    by_sosa = {item["sosa"]: item for item in response.json()}
    assert by_sosa[1]["birth_place_original_name"] == "Racine"
    assert by_sosa[1]["birth_place_display_name"] == "Racine"
    assert by_sosa[1]["color_kind"] == "GEOGRAPHIC"
    assert by_sosa[1]["color_css"] == "#B49CB1"
    assert by_sosa[1]["color_reliable"] is True
    assert by_sosa[2]["birth_place_original_name"] == "Validé"
    assert by_sosa[2]["birth_place_display_name"] == "Lieu validé"
    assert by_sosa[2]["color_kind"] == "GEOGRAPHIC"
    assert by_sosa[2]["color_css"] != by_sosa[1]["color_css"]
    assert by_sosa[2]["color_reliable"] is True
    assert by_sosa[3]["birth_place_original_name"] == "Manuel"
    assert by_sosa[3]["birth_place_display_name"] == "Manuel"
    assert by_sosa[3]["color_kind"] == "UNVERIFIED_PLACE"
    assert by_sosa[3]["color_css"] == "#D8D8D8"
    assert by_sosa[3]["color_reliable"] is False
    for sosa in (4, 5, 6, 7):
        assert by_sosa[sosa]["birth_place_original_name"] is None
        assert by_sosa[sosa]["birth_place_display_name"] is None
        assert by_sosa[sosa]["color_kind"] == "UNKNOWN_BIRTH"
        assert by_sosa[sosa]["color_css"] == "#EFEFEF"
        assert by_sosa[sosa]["color_reliable"] is False


def test_sosa_birth_place_colors_require_a_validated_root_birth_place():
    genealogy = Genealogy(persons={"@I1@": Person(id="@I1@")})

    with TestClient(create_app(genealogy)) as client:
        response = client.get(
            "/people/@I1@/sosa",
            params={"color_mode": "BIRTH_PLACE"},
        )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "BIRTH_PLACE color mode requires a VALIDATED birth place "
            "for the root person"
        )
    }


def test_sosa_none_color_mode_preserves_monochrome_response():
    genealogy = make_genealogy()

    with TestClient(create_app(genealogy)) as client:
        response = client.get(
            "/people/@I3@/sosa",
            params={"generations": 1, "color_mode": "NONE"},
        )

    assert response.status_code == 200
    assert all(item["birth_place_original_name"] is None for item in response.json())
    assert all(item["birth_place_display_name"] is None for item in response.json())
    assert all(item["color_kind"] is None for item in response.json())
    assert all(item["color_css"] is None for item in response.json())
    assert all(item["color_reliable"] is None for item in response.json())


def test_sosa_geographic_fields_preserve_implex_occurrences():
    genealogy = Genealogy(
        persons={
            "@I1@": Person(
                id="@I1@",
                events=[Event(type="BIRT", place=Place(original_name="Racine"))],
            ),
            "@I2@": Person(
                id="@I2@",
                events=[Event(type="BIRT", place=Place(original_name="Parent A"))],
            ),
            "@I3@": Person(
                id="@I3@",
                events=[Event(type="BIRT", place=Place(original_name="Parent B"))],
            ),
            "@I4@": Person(
                id="@I4@",
                events=[Event(type="BIRT", place=Place(original_name="Partagé"))],
            ),
        },
        families={
            "@F1@": Family(
                id="@F1@",
                children=["@I1@"],
                father_id="@I2@",
                mother_id="@I3@",
            ),
            "@F2@": Family(
                id="@F2@",
                children=["@I2@"],
                father_id="@I4@",
            ),
            "@F3@": Family(
                id="@F3@",
                children=["@I3@"],
                father_id="@I4@",
            ),
        },
    )
    store = InMemoryPlaceEnrichmentStore()
    for original_name, latitude, longitude in (
        ("Racine", 45.7484, 4.8256),
        ("Parent A", 46.0, 5.0),
        ("Parent B", 45.0, 4.0),
        ("Partagé", 50.0, 20.0),
    ):
        store.save(
            PlaceEnrichment(
                original_name=original_name,
                normalized_name=(
                    "Lieu partagé" if original_name == "Partagé" else None
                ),
                latitude=latitude,
                longitude=longitude,
                status=PlaceEnrichmentStatus.VALIDATED,
            )
        )

    with TestClient(create_app(genealogy, store)) as client:
        response = client.get(
            "/people/@I1@/sosa",
            params={"generations": 2, "color_mode": "BIRTH_PLACE"},
        )

    assert response.status_code == 200
    shared_occurrences = [
        item
        for item in response.json()
        if item["birth_place_original_name"] == "Partagé"
    ]
    assert [item["sosa"] for item in shared_occurrences] == [4, 6]
    assert {item["birth_place_display_name"] for item in shared_occurrences} == {
        "Lieu partagé"
    }
    assert len({item["color_css"] for item in shared_occurrences}) == 1


def test_sosa_geographic_fields_keep_unverified_places_separate():
    genealogy = Genealogy(
        persons={
            "@I1@": Person(
                id="@I1@",
                events=[Event(type="BIRT", place=Place(original_name="Racine"))],
            ),
            "@I2@": Person(
                id="@I2@",
                events=[Event(type="BIRT", place=Place(original_name="Non vérifié A"))],
            ),
            "@I3@": Person(
                id="@I3@",
                events=[Event(type="BIRT", place=Place(original_name="Non vérifié B"))],
            ),
        },
        families={
            "@F1@": Family(
                id="@F1@",
                children=["@I1@"],
                father_id="@I2@",
                mother_id="@I3@",
            ),
        },
    )
    store = InMemoryPlaceEnrichmentStore()
    store.save(
        PlaceEnrichment(
            original_name="Racine",
            latitude=45.7484,
            longitude=4.8256,
            status=PlaceEnrichmentStatus.VALIDATED,
        )
    )
    for original_name in ("Non vérifié A", "Non vérifié B"):
        store.save(
            PlaceEnrichment(
                original_name=original_name,
                normalized_name="Même libellé normalisé",
                status=PlaceEnrichmentStatus.MANUAL,
            )
        )

    with TestClient(create_app(genealogy, store)) as client:
        response = client.get(
            "/people/@I1@/sosa",
            params={"generations": 1, "color_mode": "BIRTH_PLACE"},
        )

    assert response.status_code == 200
    unverified = [
        item
        for item in response.json()
        if item["color_kind"] == "UNVERIFIED_PLACE"
    ]
    assert [item["birth_place_original_name"] for item in unverified] == [
        "Non vérifié A",
        "Non vérifié B",
    ]
    assert {item["birth_place_display_name"] for item in unverified} == {
        "Même libellé normalisé"
    }
    assert {item["color_css"] for item in unverified} == {"#D8D8D8"}

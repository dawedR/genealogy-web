import json

import pytest

from src.domain.models import (
    GeographicReference,
    PlaceEnrichment,
    PlaceEnrichmentStatus,
)
from src.storage.place_enrichments import JsonPlaceEnrichmentStore


def manual_enrichment(
    original_name: str = "Écully, France",
    **changes,
) -> PlaceEnrichment:
    values = {
        "original_name": original_name,
        "normalized_name": "Écully",
        "latitude": 45.776,
        "longitude": 4.778,
        "status": PlaceEnrichmentStatus.MANUAL,
        "source": None,
        "confidence": None,
        "comment": "Saisie manuelle",
    }
    values.update(changes)
    return PlaceEnrichment(**values)


def test_json_store_returns_empty_collection_when_file_is_absent(tmp_path):
    store = JsonPlaceEnrichmentStore(tmp_path / "place_enrichments.json")

    assert store.get("Écully, France") is None


def test_json_store_round_trips_unicode_and_optional_coordinates(tmp_path):
    path = tmp_path / "place_enrichments.json"
    enrichment = manual_enrichment(
        original_name="Łódź, Pologne",
        normalized_name=None,
        latitude=None,
        longitude=None,
        comment="Libellé conservé sans coordonnées",
    )

    JsonPlaceEnrichmentStore(path).save(enrichment)

    assert JsonPlaceEnrichmentStore(path).get("Łódź, Pologne") == enrichment
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": 1,
        "enrichments": {
            "Łódź, Pologne": {
                "original_name": "Łódź, Pologne",
                "normalized_name": None,
                "latitude": None,
                "longitude": None,
                "status": "MANUAL",
                "source": None,
                "confidence": None,
                "comment": "Libellé conservé sans coordonnées",
            }
        },
    }


def test_json_store_replaces_only_the_same_exact_label(tmp_path):
    store = JsonPlaceEnrichmentStore(tmp_path / "place_enrichments.json")

    store.save(manual_enrichment(comment="Premier commentaire"))
    store.save(manual_enrichment(comment="Commentaire remplacé"))
    store.save(manual_enrichment("Ecully, France"))

    assert store.get("Écully, France").comment == "Commentaire remplacé"
    assert store.get("Ecully, France") is not None
    assert store.get("Écully, France") != store.get("Ecully, France")


@pytest.mark.parametrize(
    ("latitude", "longitude", "message"),
    [
        (90.1, None, "latitude"),
        (-90.1, None, "latitude"),
        (None, 180.1, "longitude"),
        (None, -180.1, "longitude"),
    ],
)
def test_place_enrichment_rejects_out_of_range_coordinates(
    latitude,
    longitude,
    message,
):
    with pytest.raises(ValueError, match=message):
        manual_enrichment(latitude=latitude, longitude=longitude)


def test_place_enrichment_accepts_coordinate_boundaries():
    enrichment = manual_enrichment(latitude=-90, longitude=180)

    assert enrichment.latitude == -90
    assert enrichment.longitude == 180


def test_validated_enrichment_requires_both_coordinates():
    with pytest.raises(ValueError, match="VALIDATED"):
        manual_enrichment(
            latitude=45.776,
            longitude=None,
            status=PlaceEnrichmentStatus.VALIDATED,
        )


def test_json_store_round_trips_validated_status(tmp_path):
    path = tmp_path / "place_enrichments.json"
    enrichment = manual_enrichment(status=PlaceEnrichmentStatus.VALIDATED)

    JsonPlaceEnrichmentStore(path).save(enrichment)

    assert JsonPlaceEnrichmentStore(path).get(enrichment.original_name) == enrichment


def test_json_store_round_trips_optional_geographic_reference(tmp_path):
    path = tmp_path / "place_enrichments.json"
    reference = GeographicReference(
        provider="geoapify",
        provider_id="place-123",
        formatted="Chanéac, Ardèche, France",
        latitude=44.917,
        longitude=4.286,
        language="fr",
        country="France",
        country_code="fr",
        state="Auvergne-Rhône-Alpes",
        county="Ardèche",
        city="Chanéac",
        postcode="07310",
        result_type="city",
        datasource_name="openstreetmap",
        datasource_attribution="© OpenStreetMap contributors",
        datasource_license="ODbL",
        datasource_url="https://www.openstreetmap.org/copyright",
        rank_confidence=0.98,
        rank_match_type="full_match",
    )
    enrichment = manual_enrichment(geographic_reference=reference)

    JsonPlaceEnrichmentStore(path).save(enrichment)

    assert JsonPlaceEnrichmentStore(path).get(enrichment.original_name) == enrichment
    stored_reference = json.loads(path.read_text(encoding="utf-8"))["enrichments"][
        enrichment.original_name
    ]["geographic_reference"]
    assert stored_reference["postcode"] == "07310"
    assert "insee_code" not in stored_reference


def test_json_store_reads_existing_version_one_document_without_geographic_reference(tmp_path):
    path = tmp_path / "place_enrichments.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "enrichments": {
                    "Écully, France": {
                        "original_name": "Écully, France",
                        "normalized_name": "Écully, France",
                        "latitude": 45.776,
                        "longitude": 4.778,
                        "status": "VALIDATED",
                        "source": "geoapify",
                        "confidence": None,
                        "comment": None,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    enrichment = JsonPlaceEnrichmentStore(path).get("Écully, France")

    assert enrichment is not None
    assert enrichment.geographic_reference is None
    assert enrichment.coordinates_overridden is False

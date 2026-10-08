import io
import socket
from urllib.error import HTTPError

import pytest

from src.services.geoapify import GeoapifyGeocoder
from src.services.geocoding import (
    GeocodingNetworkError,
    GeocodingRequestRejectedError,
    GeocodingResponseError,
    GeocodingTimeoutError,
)


class FakeResponse:
    def __init__(self, payload: str) -> None:
        self._payload = payload

    def __enter__(self):
        return io.StringIO(self._payload)

    def __exit__(self, *args):
        return False


def test_geoapify_geocoder_maps_structured_candidates(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse(
            '{"results": [{"place_id": "123", "formatted": "Écully, France", "lat": 45.777, "lon": 4.778, "city": "Écully", "suburb": "Le Centre", "district": "Lyon", "postcode": "69130", "county": "Rhône", "county_code": "69", "state": "Auvergne-Rhône-Alpes", "state_code": "ARA", "country": "France", "country_code": "fr", "result_type": "city", "datasource": {"sourcename": "openstreetmap", "attribution": "© OpenStreetMap contributors", "license": "ODbL", "url": "https://www.openstreetmap.org/copyright"}, "rank": {"confidence": 0.98, "match_type": "full_match"}}]}'
        )

    monkeypatch.setattr("src.services.geoapify.urlopen", fake_urlopen)

    candidates = GeoapifyGeocoder("test-key", timeout_seconds=2).search(
        "Écully",
        limit=5,
    )

    assert "text=%C3%89cully" in captured["url"]
    assert "format=json" in captured["url"]
    assert "limit=5" in captured["url"]
    assert "lang=fr" in captured["url"]
    assert captured["timeout"] == 2
    assert candidates[0].display_name == "Écully, France"
    assert candidates[0].provider == "geoapify"
    assert candidates[0].city == "Écully"
    assert candidates[0].country_code == "fr"
    assert candidates[0].county == "Rhône"
    assert candidates[0].district == "Lyon"
    assert candidates[0].datasource_attribution == "© OpenStreetMap contributors"
    assert candidates[0].rank_confidence == 0.98
    assert candidates[0].language == "fr"


def test_geoapify_geocoder_converts_network_errors(monkeypatch):
    def failing_urlopen(request, timeout):
        raise OSError("network failure")

    monkeypatch.setattr("src.services.geoapify.urlopen", failing_urlopen)

    with pytest.raises(GeocodingNetworkError):
        GeoapifyGeocoder("test-key").search("Radoszyce", limit=5)


@pytest.mark.parametrize(
    ("error", "error_type"),
    [
        (HTTPError("https://example.test", 400, "Bad request", {}, None), GeocodingRequestRejectedError),
        (socket.timeout(), GeocodingTimeoutError),
    ],
)
def test_geoapify_geocoder_classifies_http_and_timeout_errors(
    monkeypatch,
    error,
    error_type,
):
    def failing_urlopen(request, timeout):
        raise error

    monkeypatch.setattr("src.services.geoapify.urlopen", failing_urlopen)

    with pytest.raises(error_type):
        GeoapifyGeocoder("test-key").search("Lyon 4 ?", limit=5)


def test_geoapify_geocoder_rejects_uninterpretable_responses(monkeypatch):
    def invalid_urlopen(request, timeout):
        return FakeResponse("[]")

    monkeypatch.setattr("src.services.geoapify.urlopen", invalid_urlopen)

    with pytest.raises(GeocodingResponseError):
        GeoapifyGeocoder("test-key").search("Ecully", limit=5)

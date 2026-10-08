from __future__ import annotations

import json
import logging
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.services.geocoding import (
    GeocodingCandidate,
    GeocodingNetworkError,
    GeocodingRequestRejectedError,
    GeocodingResponseError,
    GeocodingTimeoutError,
)


logger = logging.getLogger(__name__)


class GeoapifyGeocoder:
    """Adapter for Geoapify Forward Geocoding."""

    _endpoint = "https://api.geoapify.com/v1/geocode/search"

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def search(
        self,
        query: str,
        limit: int,
    ) -> list[GeocodingCandidate]:
        parameters = urlencode(
            {
                "text": query,
                "format": "json",
                "lang": "fr",
                "limit": limit,
                "apiKey": self._api_key,
            }
        )
        request = Request(
            f"{self._endpoint}?{parameters}",
            headers={"Accept": "application/json"},
        )

        try:
            with urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                payload = json.load(response)
        except HTTPError as exc:
            logger.warning("Geoapify rejected a request: HTTP %s", exc.code)
            raise GeocodingRequestRejectedError(exc.code) from exc
        except (socket.timeout, TimeoutError) as exc:
            logger.warning("Geoapify request timed out")
            raise GeocodingTimeoutError() from exc
        except (URLError, OSError) as exc:
            logger.warning("Geoapify network request failed: %s", type(exc).__name__)
            raise GeocodingNetworkError() from exc
        except json.JSONDecodeError as exc:
            logger.warning("Geoapify returned malformed JSON")
            raise GeocodingResponseError() from exc

        if not isinstance(payload, dict):
            logger.warning("Geoapify returned a non-object JSON response")
            raise GeocodingResponseError()

        results = payload.get("results")

        if not isinstance(results, list):
            logger.warning("Geoapify response has no results list")
            raise GeocodingResponseError()

        return [
            candidate
            for result in results
            if (candidate := _candidate_from_result(result)) is not None
        ][:limit]


def _candidate_from_result(
    result: object,
) -> GeocodingCandidate | None:
    if not isinstance(result, dict):
        return None

    try:
        provider_id = str(result["place_id"])
        display_name = str(result["formatted"])
        latitude = float(result["lat"])
        longitude = float(result["lon"])
    except (KeyError, TypeError, ValueError):
        return None

    return GeocodingCandidate(
        provider="geoapify",
        provider_id=provider_id,
        display_name=display_name,
        latitude=latitude,
        longitude=longitude,
        city=_optional_string(result, "city"),
        postcode=_optional_string(result, "postcode"),
        region=_optional_string(result, "state"),
        country=_optional_string(result, "country"),
        country_code=_optional_string(result, "country_code"),
        state_code=_optional_string(result, "state_code"),
        county=_optional_string(result, "county"),
        county_code=_optional_string(result, "county_code"),
        suburb=_optional_string(result, "suburb"),
        district=_optional_string(result, "district"),
        result_type=_optional_string(result, "result_type"),
        datasource_name=_optional_nested_string(result, "datasource", "sourcename"),
        datasource_attribution=_optional_nested_string(result, "datasource", "attribution"),
        datasource_license=_optional_nested_string(result, "datasource", "license"),
        datasource_url=_optional_nested_string(result, "datasource", "url"),
        rank_confidence=_optional_nested_number(result, "rank", "confidence"),
        rank_match_type=_optional_nested_string(result, "rank", "match_type"),
        language="fr",
    )


def _optional_string(
    result: dict[str, object],
    field: str,
) -> str | None:
    value = result.get(field)
    return str(value) if value is not None else None


def _optional_nested_string(
    result: dict[str, object], container: str, field: str
) -> str | None:
    value = result.get(container)
    return _optional_string(value, field) if isinstance(value, dict) else None


def _optional_nested_number(
    result: dict[str, object], container: str, field: str
) -> float | None:
    value = result.get(container)
    if not isinstance(value, dict) or value.get(field) is None:
        return None
    try:
        return float(value[field])
    except (TypeError, ValueError):
        return None

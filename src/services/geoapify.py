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
        result_type=_optional_string(result, "result_type"),
    )


def _optional_string(
    result: dict[str, object],
    field: str,
) -> str | None:
    value = result.get(field)
    return str(value) if value is not None else None

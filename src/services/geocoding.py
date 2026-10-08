from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.domain.models import GeographicReference


@dataclass(frozen=True)
class GeocodingCandidate:
    provider: str
    provider_id: str
    display_name: str
    latitude: float
    longitude: float
    city: str | None = None
    postcode: str | None = None
    region: str | None = None
    country: str | None = None
    result_type: str | None = None
    country_code: str | None = None
    state_code: str | None = None
    county: str | None = None
    county_code: str | None = None
    suburb: str | None = None
    district: str | None = None
    datasource_name: str | None = None
    datasource_attribution: str | None = None
    datasource_license: str | None = None
    datasource_url: str | None = None
    rank_confidence: float | None = None
    rank_match_type: str | None = None
    language: str | None = None

    def geographic_reference(self) -> GeographicReference:
        return GeographicReference(
            provider=self.provider,
            provider_id=self.provider_id,
            formatted=self.display_name,
            latitude=self.latitude,
            longitude=self.longitude,
            language=self.language,
            country=self.country,
            country_code=self.country_code,
            state=self.region,
            state_code=self.state_code,
            county=self.county,
            county_code=self.county_code,
            city=self.city,
            suburb=self.suburb,
            district=self.district,
            postcode=self.postcode,
            result_type=self.result_type,
            datasource_name=self.datasource_name,
            datasource_attribution=self.datasource_attribution,
            datasource_license=self.datasource_license,
            datasource_url=self.datasource_url,
            rank_confidence=self.rank_confidence,
            rank_match_type=self.rank_match_type,
        )


class GeocodingUnavailableError(Exception):
    """Raised when no geocoding provider is configured."""


class GeocodingProviderError(Exception):
    """Base class for safe, provider-side geocoding failures."""


class GeocodingRequestRejectedError(GeocodingProviderError):
    def __init__(self, http_status: int) -> None:
        self.http_status = http_status
        super().__init__("La requête a été refusée par Geoapify.")


class GeocodingTimeoutError(GeocodingProviderError):
    def __init__(self) -> None:
        super().__init__("La recherche Geoapify a expiré.")


class GeocodingNetworkError(GeocodingProviderError):
    def __init__(self) -> None:
        super().__init__("Le réseau ne permet pas de joindre Geoapify.")


class GeocodingResponseError(GeocodingProviderError):
    def __init__(self) -> None:
        super().__init__("La réponse Geoapify est impossible à interpréter.")


class Geocoder(Protocol):
    def search(
        self,
        query: str,
        limit: int,
    ) -> list[GeocodingCandidate]:
        """Search candidates for one explicit place query."""


class UnavailableGeocoder:
    def search(
        self,
        query: str,
        limit: int,
    ) -> list[GeocodingCandidate]:
        raise GeocodingUnavailableError(
            "Le géocodage Geoapify n’est pas configuré."
        )


class FakeGeocoder:
    """Deterministic in-memory geocoder for tests."""

    def __init__(
        self,
        candidates_by_query: dict[str, list[GeocodingCandidate]] | None = None,
    ) -> None:
        self.candidates_by_query = candidates_by_query or {}
        self.queries: list[tuple[str, int]] = []
        self.error: Exception | None = None

    def search(
        self,
        query: str,
        limit: int,
    ) -> list[GeocodingCandidate]:
        self.queries.append((query, limit))

        if self.error is not None:
            raise self.error

        return self.candidates_by_query.get(query, [])[:limit]

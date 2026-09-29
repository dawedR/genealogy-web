from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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

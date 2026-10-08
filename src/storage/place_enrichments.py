from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from src.domain.models import (
    GeographicReference,
    PlaceEnrichment,
    PlaceEnrichmentStatus,
)


class PlaceEnrichmentStore(Protocol):
    """Persistence boundary for local place metadata."""

    def get(self, original_name: str) -> PlaceEnrichment | None:
        """Return the enrichment keyed by the exact GEDCOM label."""

    def get_all(self) -> dict[str, PlaceEnrichment]:
        """Return enrichments keyed by their exact GEDCOM labels."""

    def save(self, enrichment: PlaceEnrichment) -> None:
        """Create or replace an enrichment keyed by its exact GEDCOM label."""


class InMemoryPlaceEnrichmentStore:
    """Side-effect-free store intended for tests and ephemeral app instances."""

    def __init__(self) -> None:
        self._enrichments: dict[str, PlaceEnrichment] = {}

    def get(self, original_name: str) -> PlaceEnrichment | None:
        return self._enrichments.get(_storage_key(original_name))

    def get_all(self) -> dict[str, PlaceEnrichment]:
        return dict(self._enrichments)

    def save(self, enrichment: PlaceEnrichment) -> None:
        self._enrichments[_storage_key(enrichment.original_name)] = enrichment


class JsonPlaceEnrichmentStore:
    """JSON-backed store with atomic replacement writes."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def get(self, original_name: str) -> PlaceEnrichment | None:
        return self.get_all().get(_storage_key(original_name))

    def get_all(self) -> dict[str, PlaceEnrichment]:
        return self._load()

    def save(self, enrichment: PlaceEnrichment) -> None:
        enrichments = self._load()
        enrichments[_storage_key(enrichment.original_name)] = enrichment
        self._write(enrichments)

    def _load(self) -> dict[str, PlaceEnrichment]:
        if not self._path.exists():
            return {}

        with self._path.open(encoding="utf-8") as file:
            document = json.load(file)

        if document.get("version") != 1:
            raise ValueError("Unsupported place enrichments version")

        raw_enrichments = document.get("enrichments")

        if not isinstance(raw_enrichments, Mapping):
            raise ValueError("Invalid place enrichments document")

        enrichments: dict[str, PlaceEnrichment] = {}

        for original_name, payload in raw_enrichments.items():
            if not isinstance(original_name, str) or not isinstance(payload, Mapping):
                raise ValueError("Invalid place enrichment entry")

            enrichment = _deserialize_enrichment(payload)

            if enrichment.original_name != original_name:
                raise ValueError("Place enrichment key does not match original_name")

            enrichments[original_name] = enrichment

        return enrichments

    def _write(self, enrichments: Mapping[str, PlaceEnrichment]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        document = {
            "version": 1,
            "enrichments": {
                original_name: _serialize_enrichment(enrichment)
                for original_name, enrichment in sorted(enrichments.items())
            },
        }

        temp_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._path.parent,
                prefix=f".{self._path.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                temp_path = Path(file.name)
                json.dump(
                    document,
                    file,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())

            os.replace(temp_path, self._path)

        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()


def _storage_key(original_name: str) -> str:
    """Current provisional identity strategy; deliberately no normalization."""

    return original_name


def _serialize_enrichment(enrichment: PlaceEnrichment) -> dict[str, object]:
    payload: dict[str, object] = {
        "original_name": enrichment.original_name,
        "normalized_name": enrichment.normalized_name,
        "latitude": enrichment.latitude,
        "longitude": enrichment.longitude,
        "status": enrichment.status.value,
        "source": enrichment.source,
        "confidence": enrichment.confidence,
        "comment": enrichment.comment,
    }
    if enrichment.geographic_reference is not None:
        payload["geographic_reference"] = _serialize_geographic_reference(
            enrichment.geographic_reference
        )
    return payload


def _deserialize_enrichment(payload: Mapping[str, object]) -> PlaceEnrichment:
    return PlaceEnrichment(
        original_name=_required_string(payload, "original_name"),
        normalized_name=_optional_string(payload, "normalized_name"),
        latitude=_optional_number(payload, "latitude"),
        longitude=_optional_number(payload, "longitude"),
        status=PlaceEnrichmentStatus(_required_string(payload, "status")),
        source=_optional_string(payload, "source"),
        confidence=_optional_number(payload, "confidence"),
        comment=_optional_string(payload, "comment"),
        geographic_reference=_optional_geographic_reference(
            payload.get("geographic_reference")
        ),
    )


def _serialize_geographic_reference(reference: GeographicReference) -> dict[str, object]:
    return {
        "provider": reference.provider,
        "provider_id": reference.provider_id,
        "formatted": reference.formatted,
        "latitude": reference.latitude,
        "longitude": reference.longitude,
        "language": reference.language,
        "country": reference.country,
        "country_code": reference.country_code,
        "state": reference.state,
        "state_code": reference.state_code,
        "county": reference.county,
        "county_code": reference.county_code,
        "city": reference.city,
        "suburb": reference.suburb,
        "district": reference.district,
        "postcode": reference.postcode,
        "result_type": reference.result_type,
        "datasource_name": reference.datasource_name,
        "datasource_attribution": reference.datasource_attribution,
        "datasource_license": reference.datasource_license,
        "datasource_url": reference.datasource_url,
        "rank_confidence": reference.rank_confidence,
        "rank_match_type": reference.rank_match_type,
    }


def _optional_geographic_reference(value: object) -> GeographicReference | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("Invalid geographic_reference")
    return GeographicReference(
        provider=_required_string(value, "provider"),
        provider_id=_required_string(value, "provider_id"),
        formatted=_required_string(value, "formatted"),
        latitude=_required_number(value, "latitude"),
        longitude=_required_number(value, "longitude"),
        language=_optional_string(value, "language"),
        country=_optional_string(value, "country"),
        country_code=_optional_string(value, "country_code"),
        state=_optional_string(value, "state"),
        state_code=_optional_string(value, "state_code"),
        county=_optional_string(value, "county"),
        county_code=_optional_string(value, "county_code"),
        city=_optional_string(value, "city"),
        suburb=_optional_string(value, "suburb"),
        district=_optional_string(value, "district"),
        postcode=_optional_string(value, "postcode"),
        result_type=_optional_string(value, "result_type"),
        datasource_name=_optional_string(value, "datasource_name"),
        datasource_attribution=_optional_string(value, "datasource_attribution"),
        datasource_license=_optional_string(value, "datasource_license"),
        datasource_url=_optional_string(value, "datasource_url"),
        rank_confidence=_optional_number(value, "rank_confidence"),
        rank_match_type=_optional_string(value, "rank_match_type"),
    )


def _required_string(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)

    if not isinstance(value, str):
        raise ValueError(f"Invalid place enrichment {field}")

    return value


def _optional_string(
    payload: Mapping[str, object],
    field: str,
) -> str | None:
    value = payload.get(field)

    if value is not None and not isinstance(value, str):
        raise ValueError(f"Invalid place enrichment {field}")

    return value


def _optional_number(
    payload: Mapping[str, object],
    field: str,
) -> float | None:
    value = payload.get(field)

    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Invalid place enrichment {field}")

    return float(value)


def _required_number(payload: Mapping[str, object], field: str) -> float:
    value = _optional_number(payload, field)
    if value is None:
        raise ValueError(f"Invalid geographic_reference {field}")
    return value

"""Deterministic genealogical place labels derived from trusted metadata."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from src.domain.models import (
    AdministrativeReference,
    AdministrativeReferenceStatus,
    PlaceEnrichment,
)
from src.services.cog import COG_VINTAGE, CogResolver


class PresentationProvenance(str, Enum):
    GEDCOM = "GEDCOM"
    ADMINISTRATIVE_REFERENCE = "ADMINISTRATIVE_REFERENCE"


class PresentationWarning(str, Enum):
    NO_CONFIRMED_ADMINISTRATIVE_REFERENCE = "NO_CONFIRMED_ADMINISTRATIVE_REFERENCE"
    ADMINISTRATIVE_REFERENCE_NOT_CONFIRMED = "ADMINISTRATIVE_REFERENCE_NOT_CONFIRMED"
    ADMINISTRATIVE_REFERENCE_OBSOLETE = "ADMINISTRATIVE_REFERENCE_OBSOLETE"
    NO_STRUCTURED_GEOGRAPHIC_REFERENCE = "NO_STRUCTURED_GEOGRAPHIC_REFERENCE"


class PresentationSource(str, Enum):
    GEDCOM_FALLBACK = "GEDCOM_FALLBACK"
    ADMINISTRATIVE_REFERENCE = "ADMINISTRATIVE_REFERENCE"


@dataclass(frozen=True)
class PresentationComponent:
    kind: str
    value: str
    provenance: PresentationProvenance
    verified: bool


@dataclass(frozen=True)
class PlacePresentation:
    original_name: str
    full_label: str
    short_label: str
    components: tuple[PresentationComponent, ...]
    warnings: tuple[PresentationWarning, ...]
    generated_from: PresentationSource


class PlacePresentationService:
    """Compose labels without changing GEDCOM, enrichment, or COG decisions."""

    def __init__(self, cog_resolver: CogResolver) -> None:
        self._cog_resolver = cog_resolver

    def present(
        self,
        original_name: str,
        enrichment: PlaceEnrichment | None = None,
        administrative_reference: AdministrativeReference | None = None,
    ) -> PlacePresentation:
        # Enrichment is deliberately accepted but not substituted for GEDCOM:
        # normalized_name and provider snapshots are not an administrative
        # confirmation, and could describe an orphaned historical decision.
        del enrichment
        if self._is_current_confirmation(administrative_reference):
            assert administrative_reference is not None
            return self._from_administrative_reference(
                original_name, administrative_reference
            )
        return self._gedcom_fallback(original_name, administrative_reference)

    def _is_current_confirmation(
        self, reference: AdministrativeReference | None
    ) -> bool:
        return (
            reference is not None
            and reference.status is AdministrativeReferenceStatus.CONFIRMED
            and reference.source == "insee_cog"
            and reference.vintage == COG_VINTAGE
            and self._cog_resolver.lookup(reference.cog_code, reference.cog_type)
            is not None
        )

    def _from_administrative_reference(
        self, original_name: str, reference: AdministrativeReference
    ) -> PlacePresentation:
        historical_name = reference.historical_name
        precision, source_commune = _historical_precision(
            original_name, reference.commune, historical_name
        )
        commune = _display_commune(reference.commune, reference.cog_type)
        primary_name = historical_name or commune
        components: list[PresentationComponent] = []
        if precision:
            components.append(PresentationComponent(
                "HISTORICAL_PRECISION", precision, PresentationProvenance.GEDCOM, True
            ))
        if historical_name:
            components.append(PresentationComponent(
                "HISTORICAL_COMMUNE", historical_name,
                PresentationProvenance.ADMINISTRATIVE_REFERENCE, True
            ))
            components.append(PresentationComponent(
                "CURRENT_COMMUNE", commune,
                PresentationProvenance.ADMINISTRATIVE_REFERENCE, True
            ))
        else:
            components.append(PresentationComponent(
                "COMMUNE", commune, PresentationProvenance.ADMINISTRATIVE_REFERENCE, True
            ))
        components.append(PresentationComponent(
            "COG_CODE", reference.cog_code,
            PresentationProvenance.ADMINISTRATIVE_REFERENCE, True
        ))
        administrative_parts = [
            primary_name,
            reference.cog_code,
            reference.department,
            reference.region,
            "France",
        ]
        if reference.department:
            components.append(PresentationComponent(
                "DEPARTMENT", reference.department,
                PresentationProvenance.ADMINISTRATIVE_REFERENCE, True
            ))
        if reference.region:
            components.append(PresentationComponent(
                "REGION", reference.region,
                PresentationProvenance.ADMINISTRATIVE_REFERENCE, True
            ))
        components.append(PresentationComponent(
            "COUNTRY", "France", PresentationProvenance.ADMINISTRATIVE_REFERENCE, True
        ))
        full_label = ", ".join(part for part in administrative_parts if part)
        if precision:
            full_label = f"{precision} – {full_label}"
        if historical_name:
            short_label = historical_name
        elif precision:
            short_label = (
                f"{precision} ({source_commune})"
                if source_commune else f"{precision} ({commune})"
            )
        else:
            short_label = commune
        return PlacePresentation(
            original_name=original_name,
            full_label=full_label,
            short_label=short_label,
            components=tuple(components),
            warnings=(),
            generated_from=PresentationSource.ADMINISTRATIVE_REFERENCE,
        )

    def _gedcom_fallback(
        self, original_name: str, reference: AdministrativeReference | None
    ) -> PlacePresentation:
        if reference is None:
            warning = (
                PresentationWarning.NO_CONFIRMED_ADMINISTRATIVE_REFERENCE
                if "france" in original_name.casefold()
                else PresentationWarning.NO_STRUCTURED_GEOGRAPHIC_REFERENCE
            )
        elif reference.status is not AdministrativeReferenceStatus.CONFIRMED:
            warning = PresentationWarning.ADMINISTRATIVE_REFERENCE_NOT_CONFIRMED
        else:
            warning = PresentationWarning.ADMINISTRATIVE_REFERENCE_OBSOLETE
        return PlacePresentation(
            original_name=original_name,
            full_label=original_name,
            short_label=_first_locality(original_name),
            components=(PresentationComponent(
                "GEDCOM_LABEL", original_name, PresentationProvenance.GEDCOM, True
            ),),
            warnings=(warning,),
            generated_from=PresentationSource.GEDCOM_FALLBACK,
        )


def _historical_precision(
    original_name: str, commune: str, historical_name: str | None
) -> tuple[str | None, str | None]:
    if historical_name:
        return None, None
    parts = [part.strip() for part in original_name.split(",")]
    if len(parts) < 2 or _name_key(parts[0]) == _name_key(commune):
        return None, None
    matching_part = next(
        (part for part in parts[1:] if _name_key(commune) in _name_key(part)),
        None,
    )
    return (parts[0], matching_part) if matching_part else (None, None)


def _first_locality(original_name: str) -> str:
    return original_name.split(",", maxsplit=1)[0].strip()


def _display_commune(commune: str, cog_type: str) -> str:
    if cog_type == "ARM":
        return commune.replace(" Arrondissement", " arrondissement")
    return commune


def _name_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.translate(str.maketrans({"Ł": "L", "ł": "l"})))
    return " ".join(re.findall(
        r"[a-z0-9]+", "".join(
            character for character in decomposed if not unicodedata.combining(character)
        ).casefold(),
    )).removeprefix("les ").removeprefix("la ").removeprefix("le ")

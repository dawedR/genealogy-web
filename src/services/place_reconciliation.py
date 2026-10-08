"""Read-only suggestions for reusing historical place enrichments.

The GEDCOM label remains the sole identity of a place.  This module only
compares labels to explain possible historical correspondences; it never
creates aliases, changes enrichments, or persists a decision.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from collections.abc import Mapping

from src.domain.models import PlaceEnrichment, PlaceEnrichmentStatus
from src.services.places import PlaceInventoryEntry


class HistoricalMatchClassification(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"
    REVIEW = "REVIEW"
    AMBIGUOUS = "AMBIGUOUS"
    NO_MATCH = "NO_MATCH"


class CoordinateReuseReliability(str, Enum):
    """How safely a historical coordinate can be proposed for another label."""

    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    REVIEW = "REVIEW"
    UNAVAILABLE = "UNAVAILABLE"


class HistoricalMatchReason(str, Enum):
    NORMALIZED_FULL_LABEL_MATCH = "NORMALIZED_FULL_LABEL_MATCH"
    LOCALITY_MATCH = "LOCALITY_MATCH"
    COUNTRY_MATCH = "COUNTRY_MATCH"
    CODE_MATCH = "CODE_MATCH"
    DISTRICT_NUMBER_MATCHES_CODE_SUFFIX = "DISTRICT_NUMBER_MATCHES_CODE_SUFFIX"
    ADMINISTRATIVE_COMPONENTS_MATCH = "ADMINISTRATIVE_COMPONENTS_MATCH"
    HISTORICAL_ENRICHMENT_VALIDATED = "HISTORICAL_ENRICHMENT_VALIDATED"
    HISTORICAL_COORDINATES_AVAILABLE = "HISTORICAL_COORDINATES_AVAILABLE"


class HistoricalMatchWarning(str, Enum):
    LEADING_UNCERTAINTY_MARKER = "LEADING_UNCERTAINTY_MARKER"
    LOCALITY_ONLY_MATCH = "LOCALITY_ONLY_MATCH"
    CODE_MISMATCH = "CODE_MISMATCH"
    ADMINISTRATIVE_VARIANT = "ADMINISTRATIVE_VARIANT"
    HISTORICAL_ENRICHMENT_NOT_VALIDATED = "HISTORICAL_ENRICHMENT_NOT_VALIDATED"
    HISTORICAL_COORDINATES_MISSING = "HISTORICAL_COORDINATES_MISSING"
    COMPETING_HISTORICAL_MATCHES = "COMPETING_HISTORICAL_MATCHES"
    SECONDARY_TOPONYMS_DIFFER = "SECONDARY_TOPONYMS_DIFFER"
    SECONDARY_TOPONYMS_NOT_DOCUMENTED = "SECONDARY_TOPONYMS_NOT_DOCUMENTED"
    NORMALIZED_SECONDARY_TOPONYMS_DIFFER = "NORMALIZED_SECONDARY_TOPONYMS_DIFFER"


@dataclass(frozen=True)
class HistoricalPlaceProposal:
    source_original_name: str
    historical_original_name: str
    historical_status: PlaceEnrichmentStatus
    historical_normalized_name: str | None
    latitude: float | None
    longitude: float | None
    # ``score`` ranks documentary label similarity only.  It deliberately
    # excludes validation state and coordinates, which are reported through
    # ``coordinate_reuse_reliability`` instead.
    score: int
    classification: HistoricalMatchClassification
    coordinate_reuse_reliability: CoordinateReuseReliability
    reasons: tuple[HistoricalMatchReason, ...]
    warnings: tuple[HistoricalMatchWarning, ...]


@dataclass(frozen=True)
class HistoricalPlaceReconciliation:
    source_original_name: str
    classification: HistoricalMatchClassification
    proposals: tuple[HistoricalPlaceProposal, ...]


@dataclass(frozen=True)
class _PlaceComponents:
    full_key: str
    locality_key: str
    country: str | None
    codes: frozenset[str]
    administrative_tokens: frozenset[str]
    secondary_toponyms: frozenset[str]
    ordinal_numbers: frozenset[int]
    starts_with_uncertainty_marker: bool


def reconcile_historical_places(
    active_places: list[PlaceInventoryEntry],
    enrichments: Mapping[str, PlaceEnrichment],
) -> list[HistoricalPlaceReconciliation]:
    """Suggest orphan enrichments for active places without an exact match.

    Only orphan enrichments are considered historical.  This keeps an active
    place's exact enrichment authoritative and avoids treating another active
    label as an implicit alias.
    """

    active_names = {entry.original_name for entry in active_places}
    historical_enrichments = [
        enrichment
        for original_name, enrichment in enrichments.items()
        if original_name not in active_names
    ]

    reconciliations = [
        _reconcile_place(entry.original_name, historical_enrichments)
        for entry in active_places
        if entry.original_name not in enrichments
    ]
    return reconciliations


def _reconcile_place(
    source_original_name: str,
    historical_enrichments: list[PlaceEnrichment],
) -> HistoricalPlaceReconciliation:
    source = _components(source_original_name)
    proposals = [
        proposal
        for enrichment in historical_enrichments
        if (
            proposal := _proposal_for(source_original_name, source, enrichment)
        )
        is not None
    ]
    proposals.sort(
        key=lambda proposal: (-proposal.score, proposal.historical_original_name)
    )

    if not proposals:
        return HistoricalPlaceReconciliation(
            source_original_name=source_original_name,
            classification=HistoricalMatchClassification.NO_MATCH,
            proposals=(),
        )

    classification = proposals[0].classification
    if _has_competing_matches(proposals):
        classification = HistoricalMatchClassification.AMBIGUOUS
        proposals = [
            _with_warning(
                proposal,
                HistoricalMatchWarning.COMPETING_HISTORICAL_MATCHES,
                HistoricalMatchClassification.AMBIGUOUS,
            )
            for proposal in proposals
        ]

    return HistoricalPlaceReconciliation(
        source_original_name=source_original_name,
        classification=classification,
        proposals=tuple(proposals),
    )


def _proposal_for(
    source_original_name: str,
    source: _PlaceComponents,
    enrichment: PlaceEnrichment,
) -> HistoricalPlaceProposal | None:
    # The original historical label is the documentary evidence.  A
    # normalized name may corroborate it, but must never be merged into its
    # token set: doing so previously hid divergent named localities.
    historical = _components(enrichment.original_name)
    normalized = (
        _components(enrichment.normalized_name)
        if enrichment.normalized_name
        else None
    )

    if source.full_key == historical.full_key:
        locality_matches = True
        full_label_matches = True
    else:
        locality_matches = source.locality_key == historical.locality_key
        full_label_matches = False

    district_code_matches = _district_code_matches(source, historical)
    if not locality_matches and not district_code_matches:
        return None

    historical_countries = {
        components.country
        for components in (historical, normalized)
        if components and components.country
    }
    if source.country and historical_countries and source.country not in historical_countries:
        return None

    if _has_conflicting_arrondissement_code(source, historical):
        return None

    if _has_conflicting_district_number(source, historical):
        return None

    reasons: list[HistoricalMatchReason] = []
    warnings: list[HistoricalMatchWarning] = []
    score = 0

    if full_label_matches:
        score += 55
        reasons.append(HistoricalMatchReason.NORMALIZED_FULL_LABEL_MATCH)
    else:
        score += 45
        reasons.append(HistoricalMatchReason.LOCALITY_MATCH)

    if source.starts_with_uncertainty_marker:
        warnings.append(HistoricalMatchWarning.LEADING_UNCERTAINTY_MARKER)

    if source.country and source.country in historical_countries:
        score += 12
        reasons.append(HistoricalMatchReason.COUNTRY_MATCH)

    shared_codes = source.codes & historical.codes
    if shared_codes:
        score += 20
        reasons.append(HistoricalMatchReason.CODE_MATCH)
    elif source.codes and historical.codes:
        warnings.append(HistoricalMatchWarning.CODE_MISMATCH)

    if district_code_matches:
        score += 15
        reasons.append(HistoricalMatchReason.DISTRICT_NUMBER_MATCHES_CODE_SUFFIX)

    shared_administrative_tokens = (
        source.administrative_tokens & historical.administrative_tokens
    )
    if len(shared_administrative_tokens) >= 2:
        score += 12
        reasons.append(HistoricalMatchReason.ADMINISTRATIVE_COMPONENTS_MATCH)
    elif source.administrative_tokens and historical.administrative_tokens:
        warnings.append(HistoricalMatchWarning.ADMINISTRATIVE_VARIANT)

    if source.secondary_toponyms != historical.secondary_toponyms:
        warnings.append(
            HistoricalMatchWarning.SECONDARY_TOPONYMS_DIFFER
            if source.secondary_toponyms and historical.secondary_toponyms
            else HistoricalMatchWarning.SECONDARY_TOPONYMS_NOT_DOCUMENTED
        )

    if normalized and _normalized_name_introduces_secondary_difference(
        source, historical, normalized
    ):
        warnings.append(HistoricalMatchWarning.NORMALIZED_SECONDARY_TOPONYMS_DIFFER)

    coordinate_reuse_reliability = CoordinateReuseReliability.HIGH_CONFIDENCE
    if enrichment.status is PlaceEnrichmentStatus.VALIDATED:
        reasons.append(HistoricalMatchReason.HISTORICAL_ENRICHMENT_VALIDATED)
    else:
        warnings.append(HistoricalMatchWarning.HISTORICAL_ENRICHMENT_NOT_VALIDATED)
        coordinate_reuse_reliability = CoordinateReuseReliability.UNAVAILABLE

    if enrichment.latitude is not None and enrichment.longitude is not None:
        reasons.append(HistoricalMatchReason.HISTORICAL_COORDINATES_AVAILABLE)
    else:
        warnings.append(HistoricalMatchWarning.HISTORICAL_COORDINATES_MISSING)
        coordinate_reuse_reliability = CoordinateReuseReliability.UNAVAILABLE

    if (
        coordinate_reuse_reliability
        is CoordinateReuseReliability.HIGH_CONFIDENCE
        and any(
            warning in warnings
            for warning in (
                HistoricalMatchWarning.CODE_MISMATCH,
                HistoricalMatchWarning.SECONDARY_TOPONYMS_DIFFER,
                HistoricalMatchWarning.NORMALIZED_SECONDARY_TOPONYMS_DIFFER,
            )
        )
        and not shared_codes
    ):
        # A difference is evidence to inspect, not proof that the historical
        # coordinates are wrong.  Keep the proposal, but require a human
        # decision before reusing them.
        coordinate_reuse_reliability = CoordinateReuseReliability.REVIEW

    if (
        not full_label_matches
        and HistoricalMatchReason.COUNTRY_MATCH not in reasons
        and HistoricalMatchReason.CODE_MATCH not in reasons
        and HistoricalMatchReason.DISTRICT_NUMBER_MATCHES_CODE_SUFFIX not in reasons
        and HistoricalMatchReason.ADMINISTRATIVE_COMPONENTS_MATCH not in reasons
    ):
        warnings.append(HistoricalMatchWarning.LOCALITY_ONLY_MATCH)

    classification = HistoricalMatchClassification.STRONG_MATCH
    if (
        score < 55
        or coordinate_reuse_reliability is not CoordinateReuseReliability.HIGH_CONFIDENCE
        or HistoricalMatchWarning.CODE_MISMATCH in warnings
        or HistoricalMatchWarning.HISTORICAL_ENRICHMENT_NOT_VALIDATED in warnings
        or HistoricalMatchWarning.HISTORICAL_COORDINATES_MISSING in warnings
        or HistoricalMatchWarning.LOCALITY_ONLY_MATCH in warnings
    ):
        classification = HistoricalMatchClassification.REVIEW

    return HistoricalPlaceProposal(
        source_original_name=source_original_name,
        historical_original_name=enrichment.original_name,
        historical_status=enrichment.status,
        historical_normalized_name=enrichment.normalized_name,
        latitude=enrichment.latitude,
        longitude=enrichment.longitude,
        score=score,
        classification=classification,
        coordinate_reuse_reliability=coordinate_reuse_reliability,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
    )


def _has_competing_matches(proposals: list[HistoricalPlaceProposal]) -> bool:
    if len(proposals) < 2:
        return False

    first, second = proposals[:2]
    if first.score - second.score > 8:
        return False
    return (first.latitude, first.longitude) != (second.latitude, second.longitude)


def _with_warning(
    proposal: HistoricalPlaceProposal,
    warning: HistoricalMatchWarning,
    classification: HistoricalMatchClassification,
) -> HistoricalPlaceProposal:
    warnings = proposal.warnings
    if warning not in warnings:
        warnings = (*warnings, warning)
    return HistoricalPlaceProposal(
        source_original_name=proposal.source_original_name,
        historical_original_name=proposal.historical_original_name,
        historical_status=proposal.historical_status,
        historical_normalized_name=proposal.historical_normalized_name,
        latitude=proposal.latitude,
        longitude=proposal.longitude,
        score=proposal.score,
        classification=classification,
        coordinate_reuse_reliability=proposal.coordinate_reuse_reliability,
        reasons=proposal.reasons,
        warnings=warnings,
    )


def _components(label: str) -> _PlaceComponents:
    stripped = label.strip()
    starts_with_uncertainty_marker = stripped.startswith("?")
    if starts_with_uncertainty_marker:
        stripped = stripped[1:].lstrip()

    normalized_label = _comparison_key(stripped)
    first_component = stripped.split(",", maxsplit=1)[0]
    locality_without_parentheses = re.sub(r"\([^)]*\)", "", first_component)
    locality_tokens = _tokens(locality_without_parentheses)
    ordinal_numbers = frozenset(
        int(token)
        for token in locality_tokens
        if token.isdecimal()
    )
    locality_key = " ".join(
        token for token in locality_tokens if not token.isdecimal()
    )
    all_tokens = set(_tokens(stripped))
    codes = frozenset(re.findall(r"(?<!\d)\d{5}(?!\d)", stripped))
    country = _country(all_tokens)
    administrative_tokens = frozenset(
        token
        for token in all_tokens
        if token not in set(locality_tokens)
        and token not in codes
        and not token.isdecimal()
        and token not in {"france", "pologne", "poland"}
    )
    secondary_toponyms = frozenset(
        token
        for token in administrative_tokens
        # Short regional abbreviations (SK, MZ, LD, …) are metadata, not a
        # newly introduced locality.  They can corroborate a country but must
        # not manufacture a toponymic difference.
        if token not in _ADMINISTRATIVE_WORDS and len(token) > 2
    )
    return _PlaceComponents(
        full_key=normalized_label,
        locality_key=locality_key,
        country=country,
        codes=codes,
        administrative_tokens=administrative_tokens,
        secondary_toponyms=secondary_toponyms,
        ordinal_numbers=ordinal_numbers,
        starts_with_uncertainty_marker=starts_with_uncertainty_marker,
    )


_ADMINISTRATIVE_WORDS = frozenset({"de", "d", "district", "gouvernement", "powiat"})


def _normalized_name_introduces_secondary_difference(
    source: _PlaceComponents,
    historical: _PlaceComponents,
    normalized: _PlaceComponents,
) -> bool:
    """Detect named secondary toponyms added by normalization, conservatively.

    Omitting old administrative detail is common and not itself a conflict.
    Introducing a new named locality (for example Pawłów beside Bodzentyn) is
    useful evidence for review, without asserting that historical geography is
    contradictory.
    """

    if not normalized.secondary_toponyms:
        return False
    documented_toponyms = source.secondary_toponyms | historical.secondary_toponyms
    return bool(normalized.secondary_toponyms - documented_toponyms)


def _district_code_matches(
    source: _PlaceComponents,
    historical: _PlaceComponents,
) -> bool:
    return bool(
        historical.ordinal_numbers
        and any(
            int(code[-2:]) in historical.ordinal_numbers
            for code in source.codes
        )
    )


def _has_conflicting_district_number(
    source: _PlaceComponents,
    historical: _PlaceComponents,
) -> bool:
    if not historical.ordinal_numbers or not source.codes:
        return False
    return not _district_code_matches(source, historical)


def _has_conflicting_arrondissement_code(
    source: _PlaceComponents,
    historical: _PlaceComponents,
) -> bool:
    source_districts = {
        district
        for code in source.codes
        if (district := _french_arrondissement_code(code)) is not None
    }
    historical_districts = {
        district
        for code in historical.codes
        if (district := _french_arrondissement_code(code)) is not None
    }
    return bool(
        source_districts
        and historical_districts
        and source_districts.isdisjoint(historical_districts)
    )


def _french_arrondissement_code(code: str) -> tuple[str, int] | None:
    if code.startswith("69") and code[2] == "0":
        district = int(code[-2:])
        return ("LYON", district) if 1 <= district <= 9 else None
    if code.startswith("751"):
        district = int(code[-2:])
        return ("PARIS", district) if 1 <= district <= 20 else None
    return None


def _country(tokens: set[str]) -> str | None:
    if "france" in tokens:
        return "FRANCE"
    if "pologne" in tokens or "poland" in tokens:
        return "POLAND"
    return None


def _comparison_key(value: str) -> str:
    return " ".join(_tokens(value))


def _tokens(value: str) -> list[str]:
    transliterated = value.translate(str.maketrans({"Ł": "L", "ł": "l"}))
    decomposed = unicodedata.normalize("NFKD", transliterated)
    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return re.findall(r"[a-z0-9]+", without_accents.casefold())

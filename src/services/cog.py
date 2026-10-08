"""Deterministic, read-only resolution against a bundled Insee COG vintage."""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path


COG_VINTAGE = "2026"
_FIVE_DIGIT_CODE = re.compile(r"(?<!\d)(\d{5})(?!\d)")
_ARM_NAME = re.compile(
    r"^(paris|lyon|marseille)\s+(\d{1,2})(?:er|e|eme|ème)?(?:\s+arrondissement)?$"
)


class CogClassification(str, Enum):
    MATCHED = "MATCHED"
    REVIEW = "REVIEW"
    AMBIGUOUS = "AMBIGUOUS"
    NO_MATCH = "NO_MATCH"


class SourceCodeKind(str, Enum):
    COG_CONFIRMED = "COG_CONFIRMED"
    HISTORICAL_COG_CONFIRMED = "HISTORICAL_COG_CONFIRMED"
    UNCONFIRMED_FIVE_DIGIT = "UNCONFIRMED_FIVE_DIGIT"
    ABSENT = "ABSENT"


class CogMatchMethod(str, Enum):
    CURRENT_CODE_AND_NAME = "CURRENT_CODE_AND_NAME"
    HISTORICAL_CODE_AND_NAME = "HISTORICAL_CODE_AND_NAME"
    CODE_AND_EMBEDDED_COMMUNE = "CODE_AND_EMBEDDED_COMMUNE"
    CODE_NAME_CONFLICT = "CODE_NAME_CONFLICT"
    CODE_NOT_FOUND = "CODE_NOT_FOUND"
    NO_SOURCE_CODE = "NO_SOURCE_CODE"


class CogReason(str, Enum):
    SOURCE_COUNTRY_FRANCE = "SOURCE_COUNTRY_FRANCE"
    CURRENT_CODE_NAME_MATCH = "CURRENT_CODE_NAME_MATCH"
    HISTORICAL_CODE_NAME_MATCH = "HISTORICAL_CODE_NAME_MATCH"
    MUNICIPAL_ARRONDISSEMENT_MATCH = "MUNICIPAL_ARRONDISSEMENT_MATCH"
    EMBEDDED_COMMUNE_MATCH = "EMBEDDED_COMMUNE_MATCH"


class CogWarning(str, Enum):
    HISTORICAL_DETAIL_PRESERVED = "HISTORICAL_DETAIL_PRESERVED"
    LEADING_UNCERTAINTY_MARKER = "LEADING_UNCERTAINTY_MARKER"
    CODE_DOES_NOT_MATCH_SOURCE_NAME = "CODE_DOES_NOT_MATCH_SOURCE_NAME"
    CODE_NOT_IN_COG = "CODE_NOT_IN_COG"
    POSTCODE_NOT_INFERRED = "POSTCODE_NOT_INFERRED"


@dataclass(frozen=True)
class CogCandidate:
    code: str
    type: str
    vintage: str
    commune: str
    department_code: str | None
    department: str | None
    region_code: str | None
    region: str | None
    historical_name: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None


@dataclass(frozen=True)
class CogResolution:
    original_name: str
    source_code: str | None
    source_code_kind: SourceCodeKind
    candidate: CogCandidate | None
    method: CogMatchMethod
    classification: CogClassification
    reasons: tuple[CogReason, ...]
    warnings: tuple[CogWarning, ...]


class CogRepository:
    """Indexes a committed COG snapshot without consulting the network."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self.current_by_code = _rows_by("COM", directory / "communes.csv")
        self.historical_by_code = _rows_by(
            "COM", directory / "communes_depuis_1943.csv"
        )
        self.departments = _single_rows_by("DEP", directory / "departements.csv")
        self.regions = _single_rows_by("REG", directory / "regions.csv")

    @classmethod
    @lru_cache(maxsize=1)
    def bundled(cls) -> "CogRepository":
        return cls(Path(__file__).resolve().parents[2] / "resources" / "cog" / COG_VINTAGE)


class CogResolver:
    def __init__(self, repository: CogRepository) -> None:
        self._repository = repository

    @classmethod
    @lru_cache(maxsize=1)
    def bundled(cls) -> "CogResolver":
        return cls(CogRepository.bundled())

    def resolve(self, original_name: str) -> CogResolution:
        source_code = _source_code(original_name)
        warnings: list[CogWarning] = []
        if original_name.lstrip().startswith("?"):
            warnings.append(CogWarning.LEADING_UNCERTAINTY_MARKER)
        if source_code is None:
            return CogResolution(
                original_name, None, SourceCodeKind.ABSENT, None,
                CogMatchMethod.NO_SOURCE_CODE, CogClassification.NO_MATCH,
                (CogReason.SOURCE_COUNTRY_FRANCE,), tuple(warnings),
            )

        current_rows = self._repository.current_by_code.get(source_code, [])
        historical_rows = self._repository.historical_by_code.get(source_code, [])
        matching_current = [row for row in current_rows if _matches_source(row, original_name)]
        matching_historical = [row for row in historical_rows if _matches_source(row, original_name)]
        # A currently delegated commune can retain its old name in the current
        # file.  The historical record is more explicit about the period and
        # avoids presenting that historical name as the current commune.
        if len(matching_historical) == 1 and (
            not matching_current
            or all(row["TYPECOM"] in {"COMA", "COMD"} for row in matching_current)
        ):
            row = matching_historical[0]
            return CogResolution(
                original_name, source_code, SourceCodeKind.HISTORICAL_COG_CONFIRMED,
                self._candidate_for_historical(row), CogMatchMethod.HISTORICAL_CODE_AND_NAME,
                CogClassification.MATCHED,
                (CogReason.SOURCE_COUNTRY_FRANCE, CogReason.HISTORICAL_CODE_NAME_MATCH),
                tuple(warnings),
            )
        if len(matching_current) == 1:
            row = matching_current[0]
            candidate = self._candidate(row)
            reasons = [CogReason.SOURCE_COUNTRY_FRANCE, CogReason.CURRENT_CODE_NAME_MATCH]
            method = CogMatchMethod.CURRENT_CODE_AND_NAME
            if row["TYPECOM"] == "ARM":
                reasons.append(CogReason.MUNICIPAL_ARRONDISSEMENT_MATCH)
            return CogResolution(
                original_name, source_code, SourceCodeKind.COG_CONFIRMED,
                candidate, method, CogClassification.MATCHED,
                tuple(reasons), tuple(warnings),
            )
        if len(matching_current) > 1:
            return CogResolution(
                original_name, source_code, SourceCodeKind.UNCONFIRMED_FIVE_DIGIT,
                None, CogMatchMethod.CODE_NAME_CONFLICT, CogClassification.AMBIGUOUS,
                (CogReason.SOURCE_COUNTRY_FRANCE,), tuple(warnings),
            )

        embedded_matches = [row for row in current_rows if _is_embedded_commune(row, original_name)]
        if len(embedded_matches) == 1:
            row = embedded_matches[0]
            warnings.append(CogWarning.HISTORICAL_DETAIL_PRESERVED)
            return CogResolution(
                original_name, source_code, SourceCodeKind.COG_CONFIRMED,
                self._candidate(row), CogMatchMethod.CODE_AND_EMBEDDED_COMMUNE,
                CogClassification.MATCHED,
                (CogReason.SOURCE_COUNTRY_FRANCE, CogReason.EMBEDDED_COMMUNE_MATCH),
                tuple(warnings),
            )

        if len(matching_historical) == 1:
            row = matching_historical[0]
            candidate = self._candidate_for_historical(row)
            return CogResolution(
                original_name, source_code, SourceCodeKind.HISTORICAL_COG_CONFIRMED,
                candidate, CogMatchMethod.HISTORICAL_CODE_AND_NAME,
                CogClassification.MATCHED,
                (CogReason.SOURCE_COUNTRY_FRANCE, CogReason.HISTORICAL_CODE_NAME_MATCH),
                tuple(warnings),
            )

        if current_rows or historical_rows:
            warnings.extend((
                CogWarning.CODE_DOES_NOT_MATCH_SOURCE_NAME,
                CogWarning.POSTCODE_NOT_INFERRED,
            ))
            candidate = self._candidate(_administrative_row(current_rows)) if current_rows else None
            return CogResolution(
                original_name, source_code, SourceCodeKind.UNCONFIRMED_FIVE_DIGIT,
                candidate, CogMatchMethod.CODE_NAME_CONFLICT, CogClassification.REVIEW,
                (CogReason.SOURCE_COUNTRY_FRANCE,), tuple(warnings),
            )

        warnings.extend((CogWarning.CODE_NOT_IN_COG, CogWarning.POSTCODE_NOT_INFERRED))
        return CogResolution(
            original_name, source_code, SourceCodeKind.UNCONFIRMED_FIVE_DIGIT,
            None, CogMatchMethod.CODE_NOT_FOUND, CogClassification.NO_MATCH,
            (CogReason.SOURCE_COUNTRY_FRANCE,), tuple(warnings),
        )

    def _candidate(self, row: dict[str, str]) -> CogCandidate:
        administrative_row = _administrative_row(
            self._repository.current_by_code.get(row.get("COMPARENT") or row["COM"], [row])
        )
        department_code = administrative_row.get("DEP") or None
        department = self._repository.departments.get(department_code or "", {}).get("NCCENR")
        region_code = administrative_row.get("REG") or None
        region = self._repository.regions.get(region_code or "", {}).get("NCCENR")
        return CogCandidate(
            code=row["COM"], type=row["TYPECOM"], vintage=COG_VINTAGE,
            commune=row["NCCENR"], department_code=department_code,
            department=department, region_code=region_code, region=region,
        )

    def _candidate_for_historical(self, row: dict[str, str]) -> CogCandidate:
        current = self._repository.current_by_code.get(row["COM"], [])
        candidate = self._candidate(_administrative_row(current)) if current else CogCandidate(
            code=row["COM"], type=row["TYPECOM"], vintage=COG_VINTAGE,
            commune=row["NCCENR"], department_code=None, department=None,
            region_code=None, region=None,
        )
        return CogCandidate(
            code=row["COM"], type=row["TYPECOM"], vintage=COG_VINTAGE,
            commune=candidate.commune, department_code=candidate.department_code,
            department=candidate.department, region_code=candidate.region_code,
            region=candidate.region, historical_name=row["NCCENR"],
            valid_from=row.get("DATE_DEBUT") or None,
            valid_to=row.get("DATE_FIN") or None,
        )


def _rows_by(key: str, path: Path) -> dict[str, list[dict[str, str]]]:
    rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            rows[row[key]].append(row)
    return dict(rows)


def _single_rows_by(key: str, path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return {row[key]: row for row in csv.DictReader(file)}


def _source_code(original_name: str) -> str | None:
    match = _FIVE_DIGIT_CODE.search(original_name)
    return match.group(1) if match else None


def _matches_source(row: dict[str, str], original_name: str) -> bool:
    source = _primary_locality(original_name)
    if row["TYPECOM"] == "ARM":
        return _arm_key(source) == _arm_key(row["NCCENR"])
    return _name_key(source) == _name_key(row["NCCENR"])


def _is_embedded_commune(row: dict[str, str], original_name: str) -> bool:
    return _name_key(row["NCCENR"]) in _name_key(_before_source_code(original_name))


def _primary_locality(original_name: str) -> str:
    return original_name.lstrip().lstrip("?").strip().split(",", maxsplit=1)[0]


def _before_source_code(original_name: str) -> str:
    match = _FIVE_DIGIT_CODE.search(original_name)
    return original_name[:match.start()] if match else original_name


def _arm_key(value: str) -> tuple[str, int] | None:
    match = _ARM_NAME.match(_name_key(value))
    return (match.group(1), int(match.group(2))) if match else None


def _name_key(value: str) -> str:
    transliterated = value.translate(str.maketrans({"Ł": "L", "ł": "l"}))
    decomposed = unicodedata.normalize("NFKD", transliterated)
    tokens = re.findall(
        r"[a-z0-9]+",
        "".join(character for character in decomposed if not unicodedata.combining(character)).casefold(),
    )
    if tokens and tokens[0] in {"l", "la", "le", "les"}:
        tokens = tokens[1:]
    return " ".join(tokens)


def _administrative_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return next((row for row in rows if row["TYPECOM"] == "COM"), rows[0])

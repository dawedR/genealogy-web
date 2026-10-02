"""Local portrait resolution, deliberately separate from GEDCOM data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import quote

from src.domain.models import Sex


class PortraitKind(str, Enum):
    PERSON = "PERSON"
    FALLBACK_MALE = "FALLBACK_MALE"
    FALLBACK_FEMALE = "FALLBACK_FEMALE"
    FALLBACK_UNKNOWN = "FALLBACK_UNKNOWN"


@dataclass(frozen=True)
class PortraitReference:
    url: str
    kind: PortraitKind


class PortraitResolver:
    """Resolve public portrait URLs from a local, user-owned registry.

    Portrait files and their registry never belong to the GEDCOM import. Invalid
    registry data is treated as an absent portrait so that it cannot prevent a
    tree from rendering.
    """

    _ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg"}

    def __init__(
        self,
        registry_path: Path,
        portraits_root: Path,
        portraits_url_prefix: str = "/portraits",
        fallback_url_prefix: str = "/static/portraits",
    ) -> None:
        self.registry_path = registry_path
        self.portraits_root = portraits_root
        self.portraits_url_prefix = portraits_url_prefix.rstrip("/")
        self.fallback_url_prefix = fallback_url_prefix.rstrip("/")

    def resolve(
        self,
        person_id: str | None,
        sex: Sex | None,
    ) -> PortraitReference:
        filename = self._registered_filename(person_id)
        if filename is not None and self._is_safe_existing_portrait(filename):
            return PortraitReference(
                url=f"{self.portraits_url_prefix}/{quote(filename)}",
                kind=PortraitKind.PERSON,
            )
        return self._fallback(sex)

    def _registered_filename(self, person_id: str | None) -> str | None:
        if person_id is None:
            return None
        try:
            registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        if not isinstance(registry, dict):
            return None
        filename = registry.get(person_id)
        return filename if isinstance(filename, str) else None

    def _is_safe_existing_portrait(self, filename: str) -> bool:
        candidate = Path(filename)
        if (
            not filename
            or candidate.name != filename
            or "/" in filename
            or "\\" in filename
            or ".." in filename
            or candidate.suffix.lower() not in self._ALLOWED_SUFFIXES
        ):
            return False
        try:
            root = self.portraits_root.resolve()
            target = (root / candidate).resolve()
            target.relative_to(root)
        except (OSError, ValueError):
            return False
        return target.is_file()

    def _fallback(self, sex: Sex | None) -> PortraitReference:
        if sex is Sex.MALE:
            filename = "fallback-male.svg"
            kind = PortraitKind.FALLBACK_MALE
        elif sex is Sex.FEMALE:
            filename = "fallback-female.svg"
            kind = PortraitKind.FALLBACK_FEMALE
        else:
            filename = "fallback-unknown.svg"
            kind = PortraitKind.FALLBACK_UNKNOWN
        return PortraitReference(
            url=f"{self.fallback_url_prefix}/{filename}",
            kind=kind,
        )

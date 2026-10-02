"""Portrait resolution separate from GEDCOM and tree layout."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import quote

from src.domain.models import Genealogy, Person, Sex


class PortraitKind(str, Enum):
    PERSON_LOCAL = "PERSON_LOCAL"
    PERSON_GENEWEB = "PERSON_GENEWEB"
    FALLBACK_MALE = "FALLBACK_MALE"
    FALLBACK_FEMALE = "FALLBACK_FEMALE"
    FALLBACK_UNKNOWN = "FALLBACK_UNKNOWN"


@dataclass(frozen=True)
class PortraitReference:
    url: str
    kind: PortraitKind


@dataclass(frozen=True)
class ResolvedGenewebPortrait:
    path: Path
    media_type: str


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
        geneweb_portraits_root: Path | None = None,
        geneweb_portraits_url_prefix: str = "/geneweb-portraits",
    ) -> None:
        self.registry_path = registry_path
        self.portraits_root = portraits_root
        self.portraits_url_prefix = portraits_url_prefix.rstrip("/")
        self.fallback_url_prefix = fallback_url_prefix.rstrip("/")
        self.geneweb_portraits_root = geneweb_portraits_root
        self.geneweb_portraits_url_prefix = geneweb_portraits_url_prefix.rstrip("/")
        self._resolved_geneweb_portraits: dict[str, ResolvedGenewebPortrait] = {}

    def resolve(
        self,
        person_id: str | None,
        sex: Sex | None,
        *,
        person: Person | None = None,
        genealogy: Genealogy | None = None,
    ) -> PortraitReference:
        filename = self._registered_filename(person_id)
        if filename is not None and self._is_safe_existing_portrait(filename):
            return PortraitReference(
                url=f"{self.portraits_url_prefix}/{quote(filename)}",
                kind=PortraitKind.PERSON_LOCAL,
            )

        geneweb = self._resolve_geneweb_portrait(person, genealogy)
        if geneweb is not None:
            token = self._register_geneweb_portrait(geneweb)
            return PortraitReference(
                url=f"{self.geneweb_portraits_url_prefix}/{token}",
                kind=PortraitKind.PERSON_GENEWEB,
            )
        return self._fallback(sex)

    def geneweb_portrait(self, token: str) -> ResolvedGenewebPortrait | None:
        portrait = self._resolved_geneweb_portraits.get(token)
        if portrait is None or not self._is_safe_geneweb_portrait(portrait.path):
            return None
        media_type = _image_media_type(portrait.path)
        if media_type != portrait.media_type:
            return None
        return portrait

    def _resolve_geneweb_portrait(
        self,
        person: Person | None,
        genealogy: Genealogy | None,
    ) -> ResolvedGenewebPortrait | None:
        if self.geneweb_portraits_root is None or person is None or genealogy is None:
            return None

        identity = _geneweb_identity(person)
        if identity is None:
            return None
        matching_people = [
            candidate
            for candidate in genealogy.persons.values()
            if _geneweb_identity(candidate) == identity
        ]
        if len(matching_people) != 1 or matching_people[0].id != person.id:
            return None

        candidates: list[ResolvedGenewebPortrait] = []
        try:
            entries = self.geneweb_portraits_root.iterdir()
            for path in entries:
                if not self._is_safe_geneweb_portrait(path):
                    continue
                filename_key = _geneweb_filename_key(path.name)
                if filename_key != (identity[0], 0, identity[1]):
                    continue
                media_type = _image_media_type(path)
                if media_type is not None:
                    candidates.append(
                        ResolvedGenewebPortrait(path=path.resolve(), media_type=media_type)
                    )
        except OSError:
            return None

        return candidates[0] if len(candidates) == 1 else None

    def _register_geneweb_portrait(self, portrait: ResolvedGenewebPortrait) -> str:
        token = hashlib.sha256(str(portrait.path).encode("utf-8")).hexdigest()
        self._resolved_geneweb_portraits[token] = portrait
        return token

    def _is_safe_geneweb_portrait(self, path: Path) -> bool:
        root = self.geneweb_portraits_root
        if root is None or path.suffix.lower() not in self._ALLOWED_SUFFIXES:
            return False
        try:
            resolved_root = root.resolve()
            resolved_path = path.resolve()
            resolved_path.relative_to(resolved_root)
        except (OSError, ValueError):
            return False
        return resolved_path.is_file()
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
            filename = "fallback-male.png"
            kind = PortraitKind.FALLBACK_MALE
        elif sex is Sex.FEMALE:
            filename = "fallback-female.png"
            kind = PortraitKind.FALLBACK_FEMALE
        else:
            filename = "fallback-unknown.svg"
            kind = PortraitKind.FALLBACK_UNKNOWN
        return PortraitReference(
            url=f"{self.fallback_url_prefix}/{filename}",
            kind=kind,
        )

def _geneweb_identity(person: Person) -> tuple[str, str] | None:
    given_name = _normalize_geneweb_key(_first_given_name(person.given_names))
    surname = _normalize_geneweb_key(person.surname)
    if not given_name or not surname:
        return None
    return given_name, surname


def _normalize_geneweb_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character
        for character in decomposed
        if character.isascii() and character.isalnum()
    )


def _first_given_name(value: str) -> str:
    if not value.strip():
        return ""
    return re.split(r"[\s-]+", value.strip(), maxsplit=1)[0]


def _geneweb_filename_key(filename: str) -> tuple[str, int, str] | None:
    match = re.fullmatch(
        r"([^.]+)\.(\d+)\.([^.]+)\.(?:png|jpe?g)",
        filename,
        re.IGNORECASE,
    )
    if match is None:
        return None
    return (
        _normalize_geneweb_key(match.group(1)),
        int(match.group(2)),
        _normalize_geneweb_key(match.group(3)),
    )


def _image_media_type(path: Path) -> str | None:
    try:
        with path.open("rb") as image:
            header = image.read(12)
    except OSError:
        return None
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return None

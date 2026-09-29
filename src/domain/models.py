from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Sex(str, Enum):
    MALE = "M"
    FEMALE = "F"
    UNKNOWN = "U"


@dataclass(frozen=True)
class EventDate:
    """A genealogical date preserving its semantic precision."""

    value: str


@dataclass(frozen=True)
class Place:
    original_name: str


class PlaceEnrichmentStatus(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    AUTOMATIC = "AUTOMATIC"
    AMBIGUOUS = "AMBIGUOUS"
    MANUAL = "MANUAL"
    VALIDATED = "VALIDATED"


@dataclass(frozen=True)
class PlaceEnrichment:
    """Local metadata associated with one exact GEDCOM place label."""

    original_name: str
    normalized_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: PlaceEnrichmentStatus = PlaceEnrichmentStatus.UNRESOLVED
    source: str | None = None
    confidence: float | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")

        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")


@dataclass
class Event:
    type: str
    detail: str | None = None
    date: EventDate | None = None
    place: Place | None = None
    sources: list[str] = field(default_factory=list)

@dataclass
class Person:
    id: str
    given_names: str = ""
    surname: str = ""
    sex: Sex = Sex.UNKNOWN
    occupations: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)

@dataclass
class Family:
    id: str
    partners: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    father_id: str | None = None
    mother_id: str | None = None

@dataclass
class Genealogy:
    persons: dict[str, Person] = field(default_factory=dict)
    families: dict[str, Family] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
    places: list[Place] = field(default_factory=list)

@dataclass(frozen=True)
class IgnoredTag:
    tag: str
    record_id: str | None = None

@dataclass
class ImportReport:
    persons_count: int = 0
    families_count: int = 0
    events_count: int = 0
    places_count: int = 0
    warnings: list[str] = field(default_factory=list)
    ignored_tags: list[IgnoredTag] = field(default_factory=list)
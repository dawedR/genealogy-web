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


@dataclass
class Event:
    type: str
    date: EventDate | None = None
    place: Place | None = None


@dataclass
class Person:
    id: str
    given_names: str = ""
    surname: str = ""
    sex: Sex = Sex.UNKNOWN
    events: list[Event] = field(default_factory=list)


@dataclass
class Family:
    id: str
    partners: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)


@dataclass
class Genealogy:
    persons: dict[str, Person] = field(default_factory=dict)
    families: dict[str, Family] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
    places: list[Place] = field(default_factory=list)


@dataclass
class ImportReport:
    persons_count: int = 0
    families_count: int = 0
    events_count: int = 0
    places_count: int = 0
    warnings: list[str] = field(default_factory=list)
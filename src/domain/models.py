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
class GeographicReference:
    """Immutable provider snapshot retained separately from active place data."""

    provider: str
    provider_id: str
    formatted: str
    latitude: float
    longitude: float
    language: str | None = None
    country: str | None = None
    country_code: str | None = None
    state: str | None = None
    state_code: str | None = None
    county: str | None = None
    county_code: str | None = None
    city: str | None = None
    suburb: str | None = None
    district: str | None = None
    postcode: str | None = None
    result_type: str | None = None
    datasource_name: str | None = None
    datasource_attribution: str | None = None
    datasource_license: str | None = None
    datasource_url: str | None = None
    rank_confidence: float | None = None
    rank_match_type: str | None = None

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise ValueError("geographic reference latitude must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise ValueError("geographic reference longitude must be between -180 and 180")


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
    geographic_reference: GeographicReference | None = None

    def __post_init__(self) -> None:
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")

        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")

        if self.status is PlaceEnrichmentStatus.VALIDATED and (
            self.latitude is None or self.longitude is None
        ):
            raise ValueError(
                "VALIDATED place enrichments require latitude and longitude"
            )

    @property
    def coordinates_overridden(self) -> bool:
        """Whether active coordinates no longer equal the provider snapshot."""

        return (
            self.geographic_reference is not None
            and (
                self.latitude != self.geographic_reference.latitude
                or self.longitude != self.geographic_reference.longitude
            )
        )


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
    partners: list[str | None] = field(default_factory=list)
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

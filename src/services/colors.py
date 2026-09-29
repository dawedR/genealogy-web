from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, pi, radians, sin, sqrt
from typing import Literal

from src.domain.models import PlaceEnrichment, PlaceEnrichmentStatus


EARTH_RADIUS_KM = 6_371.0
DEFAULT_KILOMETERS_PER_OKLAB_UNIT = 12_000.0


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")

        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")


@dataclass(frozen=True)
class ColorConfiguration:
    """Stable parameters for one geographic color palette.

    The V1 scale of 12,000 km per OKLab unit keeps the validated birth
    places around Lyon and Poland in one family while retaining regional
    variation. It is intentionally fixed rather than data-set adaptive.
    """

    reference: GeoPoint
    kilometers_per_oklab_unit: float = DEFAULT_KILOMETERS_PER_OKLAB_UNIT
    lightness: float = 0.72
    base_a: float = 0.035
    base_b: float = -0.02
    neutral_unverified: str = "#D8D8D8"
    neutral_unknown: str = "#EFEFEF"

    def __post_init__(self) -> None:
        if self.kilometers_per_oklab_unit <= 0:
            raise ValueError("kilometers_per_oklab_unit must be positive")

        if not 0 <= self.lightness <= 1:
            raise ValueError("lightness must be between 0 and 1")

        if self.neutral_unverified == self.neutral_unknown:
            raise ValueError("neutral colors must be distinct")


@dataclass(frozen=True)
class ColorResult:
    css: str
    reliable: bool
    kind: Literal[
        "GEOGRAPHIC",
        "UNVERIFIED_PLACE",
        "UNKNOWN_BIRTH",
    ]
    gamut_mapped: bool = False


def haversine_distance_km(first: GeoPoint, second: GeoPoint) -> float:
    """Return the great-circle distance between two geographic points."""

    latitude_delta = radians(second.latitude - first.latitude)
    longitude_delta = radians(
        _wrapped_longitude_delta(second.longitude - first.longitude)
    )
    first_latitude = radians(first.latitude)
    second_latitude = radians(second.latitude)

    value = (
        sin(latitude_delta / 2) ** 2
        + cos(first_latitude)
        * cos(second_latitude)
        * sin(longitude_delta / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * atan2(sqrt(value), sqrt(1 - value))


def project_local_kilometers(
    point: GeoPoint,
    reference: GeoPoint,
) -> tuple[float, float]:
    """Project a point locally as east and north offsets in kilometres.

    This equirectangular projection is centred on the configured reference.
    """

    east = (
        EARTH_RADIUS_KM
        * cos(radians(reference.latitude))
        * radians(_wrapped_longitude_delta(point.longitude - reference.longitude))
    )
    north = EARTH_RADIUS_KM * radians(point.latitude - reference.latitude)
    return east, north


class ColorService:
    """Derive deterministic geographic colors without presentation concerns."""

    def __init__(self, configuration: ColorConfiguration) -> None:
        self._configuration = configuration

    def color_for_coordinates(self, point: GeoPoint) -> ColorResult:
        east, north = project_local_kilometers(
            point,
            self._configuration.reference,
        )
        a = self._configuration.base_a + (
            east / self._configuration.kilometers_per_oklab_unit
        )
        b = self._configuration.base_b - (
            north / self._configuration.kilometers_per_oklab_unit
        )
        red, green, blue, chroma_factor = _oklab_to_gamut_mapped_srgb(
            self._configuration.lightness,
            a,
            b,
        )

        return ColorResult(
            css=_srgb_to_css(red, green, blue),
            reliable=True,
            kind="GEOGRAPHIC",
            gamut_mapped=chroma_factor < 1,
        )

    def color_for_enrichment(
        self,
        enrichment: PlaceEnrichment | None,
    ) -> ColorResult:
        if (
            enrichment is None
            or enrichment.status is not PlaceEnrichmentStatus.VALIDATED
            or enrichment.latitude is None
            or enrichment.longitude is None
        ):
            return ColorResult(
                css=self._configuration.neutral_unverified,
                reliable=False,
                kind="UNVERIFIED_PLACE",
            )

        return self.color_for_coordinates(
            GeoPoint(enrichment.latitude, enrichment.longitude)
        )

    def unknown_birth_color(self) -> ColorResult:
        return ColorResult(
            css=self._configuration.neutral_unknown,
            reliable=False,
            kind="UNKNOWN_BIRTH",
        )


def _wrapped_longitude_delta(delta: float) -> float:
    return (delta + 180) % 360 - 180


def _oklab_to_gamut_mapped_srgb(
    lightness: float,
    a: float,
    b: float,
) -> tuple[float, float, float, float]:
    """Convert OKLab to sRGB, reducing chroma when the gamut requires it.

    Binary search retains the lightness and chromatic direction while finding
    the largest in-gamut chroma.
    """

    red, green, blue = _oklab_to_linear_srgb(lightness, a, b)
    if _is_srgb_in_gamut(red, green, blue):
        return red, green, blue, 1.0

    low = 0.0
    high = 1.0

    for _ in range(48):
        factor = (low + high) / 2
        red, green, blue = _oklab_to_linear_srgb(
            lightness,
            a * factor,
            b * factor,
        )

        if _is_srgb_in_gamut(red, green, blue):
            low = factor
        else:
            high = factor

    red, green, blue = _oklab_to_linear_srgb(
        lightness,
        a * low,
        b * low,
    )
    return red, green, blue, low


def _oklab_to_linear_srgb(
    lightness: float,
    a: float,
    b: float,
) -> tuple[float, float, float]:
    l = lightness + 0.3963377774 * a + 0.2158037573 * b
    m = lightness - 0.1055613458 * a - 0.0638541728 * b
    s = lightness - 0.0894841775 * a - 1.2914855480 * b

    l_cubed = l**3
    m_cubed = m**3
    s_cubed = s**3

    return (
        4.0767416621 * l_cubed
        - 3.3077115913 * m_cubed
        + 0.2309699292 * s_cubed,
        -1.2684380046 * l_cubed
        + 2.6097574011 * m_cubed
        - 0.3413193965 * s_cubed,
        -0.0041960863 * l_cubed
        - 0.7034186147 * m_cubed
        + 1.7076147010 * s_cubed,
    )


def _is_srgb_in_gamut(red: float, green: float, blue: float) -> bool:
    return all(0 <= component <= 1 for component in (red, green, blue))


def _srgb_to_css(red: float, green: float, blue: float) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        round(_linear_to_srgb(red) * 255),
        round(_linear_to_srgb(green) * 255),
        round(_linear_to_srgb(blue) * 255),
    )


def _linear_to_srgb(component: float) -> float:
    if component <= 0.0031308:
        return 12.92 * component

    return 1.055 * component ** (1 / 2.4) - 0.055

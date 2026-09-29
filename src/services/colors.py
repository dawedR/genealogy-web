from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, exp, pi, radians, sin, sqrt
from typing import Literal

from src.domain.models import PlaceEnrichment, PlaceEnrichmentStatus


EARTH_RADIUS_KM = 6_371.0
DEFAULT_REFERENCE_DISTANCE_KM = 1_000.0
DEFAULT_AMPLITUDE_AT_REFERENCE = 0.16
DEFAULT_DISTANCE_EXPONENT = 1.35
DEFAULT_DIRECTIONAL_HUE_OFFSET_DEGREES = 195.0
DEFAULT_DIRECTION_TRANSITION_AMPLITUDE = 0.10
DEFAULT_DIRECTIONAL_TARGET_CHROMA = 0.18
DEFAULT_REGIONAL_AMPLITUDE = 0.12
DEFAULT_REGIONAL_DISTANCE_KM = 125.0
DEFAULT_REGIONAL_EXPONENT = 2.0


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

    Distance controls the chromatic amplitude; the initial bearing controls
    a target hue in OKLCH. These parameters are deliberately fixed for one
    configuration rather than adapted to displayed data.
    """

    reference: GeoPoint
    regional_amplitude: float = DEFAULT_REGIONAL_AMPLITUDE
    regional_distance_km: float = DEFAULT_REGIONAL_DISTANCE_KM
    regional_exponent: float = DEFAULT_REGIONAL_EXPONENT
    reference_distance_km: float = DEFAULT_REFERENCE_DISTANCE_KM
    amplitude_at_reference: float = DEFAULT_AMPLITUDE_AT_REFERENCE
    distance_exponent: float = DEFAULT_DISTANCE_EXPONENT
    directional_hue_offset_degrees: float = DEFAULT_DIRECTIONAL_HUE_OFFSET_DEGREES
    direction_transition_amplitude: float = DEFAULT_DIRECTION_TRANSITION_AMPLITUDE
    directional_target_chroma: float = DEFAULT_DIRECTIONAL_TARGET_CHROMA
    lightness: float = 0.72
    base_a: float = 0.035
    base_b: float = -0.02
    neutral_unverified: str = "#D8D8D8"
    neutral_unknown: str = "#EFEFEF"

    def __post_init__(self) -> None:
        if self.regional_amplitude < 0:
            raise ValueError("regional_amplitude must be non-negative")

        if self.regional_distance_km <= 0:
            raise ValueError("regional_distance_km must be positive")

        if self.regional_exponent <= 0:
            raise ValueError("regional_exponent must be positive")

        if self.reference_distance_km <= 0:
            raise ValueError("reference_distance_km must be positive")

        if self.amplitude_at_reference < 0:
            raise ValueError("amplitude_at_reference must be non-negative")

        if self.distance_exponent <= 0:
            raise ValueError("distance_exponent must be positive")

        if self.direction_transition_amplitude <= 0:
            raise ValueError("direction_transition_amplitude must be positive")

        if self.directional_target_chroma < 0:
            raise ValueError("directional_target_chroma must be non-negative")

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
        distance = haversine_distance_km(
            self._configuration.reference,
            point,
        )
        amplitude = _chromatic_amplitude(distance, self._configuration)
        bearing = _initial_bearing_radians(
            self._configuration.reference,
            point,
        )
        base_chroma = sqrt(
            self._configuration.base_a ** 2
            + self._configuration.base_b ** 2
        )
        base_hue = atan2(
            self._configuration.base_b,
            self._configuration.base_a,
        )
        target_hue = _wrap_hue_radians(
            bearing + radians(self._configuration.directional_hue_offset_degrees)
        )
        transition = 1 - exp(
            -amplitude / self._configuration.direction_transition_amplitude
        )
        hue = _shortest_arc_lerp(base_hue, target_hue, transition)
        chroma = _linear_interpolation(
            base_chroma,
            self._configuration.directional_target_chroma,
            transition,
        )
        a = chroma * cos(hue)
        b = chroma * sin(hue)
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



def _chromatic_amplitude(
    distance_km: float,
    configuration: ColorConfiguration,
) -> float:
    """Scale distance continuously into an OKLab chromatic amplitude."""

    regional_amplitude = configuration.regional_amplitude * (
        1
        - exp(
            -(
                distance_km / configuration.regional_distance_km
            ) ** configuration.regional_exponent
        )
    )
    continental_amplitude = configuration.amplitude_at_reference * (
        distance_km / configuration.reference_distance_km
    ) ** configuration.distance_exponent
    return regional_amplitude + continental_amplitude


def _initial_bearing_radians(
    origin: GeoPoint,
    destination: GeoPoint,
) -> float:
    """Return the initial great-circle bearing from origin to destination."""

    longitude_delta = radians(
        _wrapped_longitude_delta(destination.longitude - origin.longitude)
    )
    origin_latitude = radians(origin.latitude)
    destination_latitude = radians(destination.latitude)
    east = sin(longitude_delta) * cos(destination_latitude)
    north = (
        cos(origin_latitude) * sin(destination_latitude)
        - sin(origin_latitude)
        * cos(destination_latitude)
        * cos(longitude_delta)
    )
    return atan2(east, north)


def _wrap_hue_radians(hue: float) -> float:
    return hue % (2 * pi)


def _shortest_arc_lerp(start: float, target: float, factor: float) -> float:
    """Interpolate hue on the shortest continuous arc of the OKLCH circle."""

    difference = (target - start + pi) % (2 * pi) - pi
    return _wrap_hue_radians(start + factor * difference)


def _linear_interpolation(start: float, target: float, factor: float) -> float:
    return start + factor * (target - start)

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

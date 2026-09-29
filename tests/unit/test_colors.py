import re
from itertools import combinations
from math import asin, atan2, cos, degrees, radians, sin

import pytest

from src.domain.models import PlaceEnrichment, PlaceEnrichmentStatus
from src.services.colors import (
    ColorConfiguration,
    ColorService,
    EARTH_RADIUS_KM,
    GeoPoint,
    _chromatic_amplitude,
    _is_srgb_in_gamut,
    _oklab_to_gamut_mapped_srgb,
    _oklab_to_linear_srgb,
    haversine_distance_km,
    project_local_kilometers,
)


def configuration(**changes):
    values = {
        "reference": GeoPoint(45.7484, 4.8256),
    }
    values.update(changes)
    return ColorConfiguration(**values)


def validated_enrichment(**changes):
    values = {
        "original_name": "Lyon",
        "latitude": 45.7484,
        "longitude": 4.8256,
        "status": PlaceEnrichmentStatus.VALIDATED,
    }
    values.update(changes)
    return PlaceEnrichment(**values)


def test_geo_point_and_configuration_validate_their_inputs():
    with pytest.raises(ValueError, match="latitude"):
        GeoPoint(91, 0)

    with pytest.raises(ValueError, match="non-negative"):
        configuration(regional_amplitude=-0.01)

    with pytest.raises(ValueError, match="regional_distance_km"):
        configuration(regional_distance_km=0)

    with pytest.raises(ValueError, match="regional_exponent"):
        configuration(regional_exponent=0)

    with pytest.raises(ValueError, match="reference_distance_km"):
        configuration(reference_distance_km=0)

    with pytest.raises(ValueError, match="non-negative"):
        configuration(amplitude_at_reference=-0.01)

    with pytest.raises(ValueError, match="positive"):
        configuration(distance_exponent=0)

    with pytest.raises(ValueError, match="direction_transition_amplitude"):
        configuration(direction_transition_amplitude=0)

    with pytest.raises(ValueError, match="non-negative"):
        configuration(directional_target_chroma=-0.01)

    with pytest.raises(ValueError, match="distinct"):
        configuration(neutral_unknown="#D8D8D8")


def test_haversine_distance_is_reusable_and_handles_the_antimeridian():
    paris = GeoPoint(48.8566, 2.3522)
    london = GeoPoint(51.5074, -0.1278)

    assert haversine_distance_km(paris, paris) == 0
    assert haversine_distance_km(paris, london) == pytest.approx(343.6, abs=1)
    assert haversine_distance_km(
        GeoPoint(0, 179.9),
        GeoPoint(0, -179.9),
    ) == pytest.approx(22.2, abs=0.2)


def test_local_projection_uses_east_and_north_offsets_from_reference():
    east, north = project_local_kilometers(
        GeoPoint(45.7484, 4.8256),
        GeoPoint(45.7484, 4.8256),
    )
    projected_east, projected_north = project_local_kilometers(
        GeoPoint(46.7484, 5.8256),
        GeoPoint(45.7484, 4.8256),
    )

    assert east == pytest.approx(0)
    assert north == pytest.approx(0)
    assert projected_east > 0
    assert projected_north > 0


def test_color_is_deterministic_and_reference_is_chromatic():
    service = ColorService(configuration())
    point = GeoPoint(45.7484, 4.8256)

    first = service.color_for_coordinates(point)
    second = service.color_for_coordinates(point)

    assert first == second
    assert first.css == "#B49CB1"
    assert first.reliable is True
    assert first.kind == "GEOGRAPHIC"


def _rgb_channels(css: str) -> tuple[int, int, int]:
    return tuple(int(css[index:index + 2], 16) for index in (1, 3, 5))


def _rgb_distance(first: str, second: str) -> int:
    return sum(
        abs(a - b)
        for a, b in zip(_rgb_channels(first), _rgb_channels(second))
    )


def test_non_linear_amplitude_keeps_local_distances_small_and_grows_far_away():
    palette = configuration()

    amplitudes = {
        distance: _chromatic_amplitude(distance, palette)
        for distance in (5, 10, 25, 50, 200, 600, 1_300)
    }

    assert amplitudes[10] < 0.002
    assert amplitudes[25] < amplitudes[50] < amplitudes[200] < amplitudes[600]
    assert amplitudes[50] > 0.02
    assert amplitudes[1_300] > 2 * amplitudes[200]
    assert amplitudes[1_300] == pytest.approx(0.348, abs=0.001)


def _point_at_distance_and_bearing(
    origin: GeoPoint,
    distance_km: float,
    bearing_degrees: float,
) -> GeoPoint:
    angular_distance = distance_km / EARTH_RADIUS_KM
    bearing = radians(bearing_degrees)
    origin_latitude = radians(origin.latitude)
    origin_longitude = radians(origin.longitude)
    latitude = asin(
        sin(origin_latitude) * cos(angular_distance)
        + cos(origin_latitude) * sin(angular_distance) * cos(bearing)
    )
    longitude = origin_longitude + atan2(
        sin(bearing) * sin(angular_distance) * cos(origin_latitude),
        cos(angular_distance) - sin(origin_latitude) * sin(latitude),
    )
    return GeoPoint(degrees(latitude), (degrees(longitude) + 180) % 360 - 180)


def test_local_places_and_one_region_remain_visually_close():
    service = ColorService(configuration())
    lyon = GeoPoint(45.7484, 4.8256)
    bron = GeoPoint(45.73375, 4.90924)
    noiretable = GeoPoint(45.81711, 3.76611)
    arconsat = GeoPoint(45.88859, 3.71330)

    assert service.color_for_coordinates(bron).css == (
        service.color_for_coordinates(lyon).css
    )
    assert _rgb_distance(
        service.color_for_coordinates(noiretable).css,
        service.color_for_coordinates(arconsat).css,
    ) < 20


def test_french_regions_are_distinct_from_lyon_and_each_other():
    service = ColorService(configuration())
    lyon = GeoPoint(45.7484, 4.8256)
    bellegarde = GeoPoint(46.10737, 5.83078)
    arcens = GeoPoint(44.90067, 4.32796)

    lyon_color = service.color_for_coordinates(lyon).css
    bellegarde_color = service.color_for_coordinates(bellegarde).css
    arcens_color = service.color_for_coordinates(arcens).css

    assert _rgb_distance(lyon_color, bellegarde_color) > 40
    assert _rgb_distance(lyon_color, arcens_color) > 60
    assert _rgb_distance(bellegarde_color, arcens_color) > 80


def test_france_and_poland_are_distinct_while_polish_places_share_one_family():
    service = ColorService(configuration())
    lyon = GeoPoint(45.7484, 4.8256)
    polish_places = [
        GeoPoint(51.76873, 19.45699),
        GeoPoint(50.80008, 20.46222),
        GeoPoint(50.9730556, 21.0488889),
    ]

    lyon_color = service.color_for_coordinates(lyon).css
    polish_colors = [service.color_for_coordinates(place).css for place in polish_places]

    assert _rgb_distance(lyon_color, polish_colors[0]) > 120
    assert all(
        _rgb_distance(first, second) < 30
        for first, second in combinations(polish_colors, 2)
    )


def test_distant_directions_produce_distinct_chromatic_families():
    service = ColorService(configuration())
    distant_points = [
        GeoPoint(54.0, -5.0),
        GeoPoint(40.0, -6.0),
        GeoPoint(37.0, 12.0),
        GeoPoint(51.76873, 19.45699),
    ]
    colors = [service.color_for_coordinates(point).css for point in distant_points]

    assert len(set(colors)) == len(colors)
    assert all(
        _rgb_distance(first, second) > 80
        for first, second in combinations(colors, 2)
    )


def test_bearing_is_continuous_across_zero_degrees():
    service = ColorService(configuration())
    reference = GeoPoint(45.7484, 4.8256)
    west_of_north = _point_at_distance_and_bearing(reference, 1_200, 359)
    east_of_north = _point_at_distance_and_bearing(reference, 1_200, 1)

    assert _rgb_distance(
        service.color_for_coordinates(west_of_north).css,
        service.color_for_coordinates(east_of_north).css,
    ) < 12


def test_color_for_enrichment_uses_only_validated_coordinates():
    service = ColorService(configuration())

    geographic = service.color_for_enrichment(validated_enrichment())
    manual = service.color_for_enrichment(
        validated_enrichment(status=PlaceEnrichmentStatus.MANUAL)
    )
    missing = service.color_for_enrichment(None)
    unknown = service.unknown_birth_color()

    assert geographic.reliable is True
    assert manual == (
        service.color_for_enrichment(
            PlaceEnrichment(
                original_name="Sans coordonnées",
                status=PlaceEnrichmentStatus.MANUAL,
            )
        )
    )
    assert manual.css == "#D8D8D8"
    assert manual.kind == "UNVERIFIED_PLACE"
    assert missing == manual
    assert unknown.css == "#EFEFEF"
    assert unknown.kind == "UNKNOWN_BIRTH"


def test_gamut_mapping_reduces_chroma_without_clamping_rgb():
    raw = _oklab_to_linear_srgb(0.72, 1.0, -1.0)
    red, green, blue, factor = _oklab_to_gamut_mapped_srgb(
        0.72,
        1.0,
        -1.0,
    )

    assert not _is_srgb_in_gamut(*raw)
    assert _is_srgb_in_gamut(red, green, blue)
    assert 0 < factor < 1

    result = ColorService(
        configuration(
            reference_distance_km=1,
            amplitude_at_reference=1,
        )
    ).color_for_coordinates(GeoPoint(46.0, 5.8))

    assert result.gamut_mapped is True
    assert re.fullmatch(r"#[0-9A-F]{6}", result.css)

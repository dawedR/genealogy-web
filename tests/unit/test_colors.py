import re

import pytest

from src.domain.models import PlaceEnrichment, PlaceEnrichmentStatus
from src.services.colors import (
    ColorConfiguration,
    ColorService,
    GeoPoint,
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

    with pytest.raises(ValueError, match="positive"):
        configuration(kilometers_per_oklab_unit=0)

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


def test_nearby_places_receive_nearby_colors():
    service = ColorService(configuration())

    first = service.color_for_coordinates(GeoPoint(46.0, 5.0))
    second = service.color_for_coordinates(GeoPoint(46.02, 5.02))

    first_channels = tuple(int(first.css[index:index + 2], 16) for index in (1, 3, 5))
    second_channels = tuple(int(second.css[index:index + 2], 16) for index in (1, 3, 5))

    assert sum(abs(a - b) for a, b in zip(first_channels, second_channels)) < 12


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
        configuration(kilometers_per_oklab_unit=10)
    ).color_for_coordinates(GeoPoint(46.0, 5.8))

    assert result.gamut_mapped is True
    assert re.fullmatch(r"#[0-9A-F]{6}", result.css)

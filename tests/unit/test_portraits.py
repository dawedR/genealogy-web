import json

import pytest

from src.domain.models import Sex
from src.services.portraits import PortraitKind, PortraitResolver


def make_resolver(tmp_path, registry=None):
    root = tmp_path / "portraits"
    root.mkdir()
    registry_path = tmp_path / "portraits.json"
    if registry is not None:
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return PortraitResolver(registry_path, root), root


@pytest.mark.parametrize(
    ("filename", "expected_url"),
    [
        ("portrait.png", "/portraits/portrait.png"),
        ("portrait.jpg", "/portraits/portrait.jpg"),
        ("portrait.jpeg", "/portraits/portrait.jpeg"),
    ],
)
def test_resolver_returns_existing_personal_png_or_jpeg(tmp_path, filename, expected_url):
    resolver, root = make_resolver(tmp_path, {"@I1@": filename})
    (root / filename).write_bytes(b"portrait")

    reference = resolver.resolve("@I1@", Sex.MALE)

    assert reference.url == expected_url
    assert reference.kind is PortraitKind.PERSON_LOCAL


@pytest.mark.parametrize(
    ("sex", "kind", "filename"),
    [
        (Sex.MALE, PortraitKind.FALLBACK_MALE, "fallback-male.png"),
        (Sex.FEMALE, PortraitKind.FALLBACK_FEMALE, "fallback-female.png"),
        (Sex.UNKNOWN, PortraitKind.FALLBACK_UNKNOWN, "fallback-unknown.svg"),
        (None, PortraitKind.FALLBACK_UNKNOWN, "fallback-unknown.svg"),
    ],
)
def test_resolver_uses_sex_specific_or_unknown_fallback(tmp_path, sex, kind, filename):
    resolver, _ = make_resolver(tmp_path)

    reference = resolver.resolve("@I1@", sex)

    assert reference.kind is kind
    assert reference.url == f"/static/portraits/{filename}"


@pytest.mark.parametrize("filename", ["missing.png", "../secret.jpg", "nested/photo.png", r"nested\photo.png", "/tmp/photo.jpg", "portrait.svg"])
def test_missing_or_unsafe_registry_entry_falls_back(tmp_path, filename):
    resolver, _ = make_resolver(tmp_path, {"@I1@": filename})

    reference = resolver.resolve("@I1@", Sex.FEMALE)

    assert reference.kind is PortraitKind.FALLBACK_FEMALE


def test_missing_registry_and_unknown_occurrence_fall_back(tmp_path):
    resolver, _ = make_resolver(tmp_path)

    reference = resolver.resolve(None, Sex.UNKNOWN)

    assert reference.kind is PortraitKind.FALLBACK_UNKNOWN

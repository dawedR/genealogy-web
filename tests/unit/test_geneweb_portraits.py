from __future__ import annotations

import json

import pytest

from src.domain.models import Genealogy, Person, Sex
from src.services.portraits import PortraitKind, PortraitResolver


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\nminimal"
JPEG_SIGNATURE = b"\xff\xd8\xffminimal"


def make_geneweb_resolver(tmp_path, registry: dict[str, str] | None = None):
    local_root = tmp_path / "local-portraits"
    local_root.mkdir()
    registry_path = tmp_path / "portraits.json"
    if registry is not None:
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
    geneweb_root = tmp_path / "geneweb-portraits"
    geneweb_root.mkdir()
    return (
        PortraitResolver(
            registry_path,
            local_root,
            geneweb_portraits_root=geneweb_root,
        ),
        local_root,
        geneweb_root,
    )


@pytest.mark.parametrize(
    ("person_id", "given_names", "surname", "sex", "filename", "contents", "media_type"),
    [
        (
            "@I88@",
            "Chilek",
            "FITERMAN",
            Sex.MALE,
            "chilek.0.fiterman.jpg",
            JPEG_SIGNATURE,
            "image/jpeg",
        ),
        (
            "@I21@",
            "François",
            "BOSQUET",
            Sex.MALE,
            "francois.0.bosquet.png",
            PNG_SIGNATURE,
            "image/png",
        ),
        (
            "@I36@",
            "Laja",
            "ROZENBLUM",
            Sex.FEMALE,
            "laja.0.rozenblum.png",
            PNG_SIGNATURE,
            "image/png",
        ),
        (
            "@I22@",
            "Maria",
            "NÉRON",
            Sex.FEMALE,
            "maria.0.neron.jpg",
            PNG_SIGNATURE,
            "image/png",
        ),
    ],
)
def test_geneweb_matches_the_observed_active_portrait_keys(
    tmp_path,
    person_id,
    given_names,
    surname,
    sex,
    filename,
    contents,
    media_type,
):
    resolver, _, geneweb_root = make_geneweb_resolver(tmp_path)
    (geneweb_root / filename).write_bytes(contents)
    person = Person(id=person_id, given_names=given_names, surname=surname, sex=sex)
    genealogy = Genealogy(persons={person.id: person})

    reference = resolver.resolve(
        person.id,
        person.sex,
        person=person,
        genealogy=genealogy,
    )

    assert reference.kind is PortraitKind.PERSON_GENEWEB
    token = reference.url.rsplit("/", maxsplit=1)[1]
    resolved = resolver.geneweb_portrait(token)
    assert resolved is not None
    assert resolved.path.name == filename
    assert resolved.media_type == media_type


@pytest.mark.parametrize(
    ("filename", "create_old"),
    [
        (None, False),
        ("francois.1.bosquet.png", False),
        ("francois.0.bosquet.png", True),
    ],
)
def test_geneweb_ignores_missing_nonzero_or_historical_portraits(
    tmp_path,
    filename,
    create_old,
):
    resolver, _, geneweb_root = make_geneweb_resolver(tmp_path)
    person = Person(
        id="@I21@",
        given_names="François",
        surname="BOSQUET",
        sex=Sex.MALE,
    )
    genealogy = Genealogy(persons={person.id: person})
    if filename is not None:
        root = geneweb_root / "old" if create_old else geneweb_root
        root.mkdir(exist_ok=True)
        (root / filename).write_bytes(PNG_SIGNATURE)

    reference = resolver.resolve(
        person.id,
        person.sex,
        person=person,
        genealogy=genealogy,
    )

    assert reference.kind is PortraitKind.FALLBACK_MALE


def test_geneweb_falls_back_for_ambiguous_identity_or_multiple_active_files(tmp_path):
    resolver, _, geneweb_root = make_geneweb_resolver(tmp_path)
    first = Person(
        id="@I17@",
        given_names="Michel Isidore",
        surname="MOREL",
        sex=Sex.MALE,
    )
    second = Person(
        id="@I19@",
        given_names="Michel",
        surname="MOREL",
        sex=Sex.MALE,
    )
    genealogy = Genealogy(persons={first.id: first, second.id: second})
    (geneweb_root / "michel.0.morel.png").write_bytes(PNG_SIGNATURE)

    ambiguous = resolver.resolve(first.id, first.sex, person=first, genealogy=genealogy)

    assert ambiguous.kind is PortraitKind.FALLBACK_MALE

    unique = Person(
        id="@I21@",
        given_names="François",
        surname="BOSQUET",
        sex=Sex.MALE,
    )
    unique_genealogy = Genealogy(persons={unique.id: unique})
    (geneweb_root / "francois.0.bosquet.png").write_bytes(PNG_SIGNATURE)
    (geneweb_root / "francois.0.bosquet.jpg").write_bytes(JPEG_SIGNATURE)

    multiple = resolver.resolve(
        unique.id,
        unique.sex,
        person=unique,
        genealogy=unique_genealogy,
    )

    assert multiple.kind is PortraitKind.FALLBACK_MALE


def test_local_mapping_has_priority_and_missing_geneweb_configuration_is_unchanged(
    tmp_path,
):
    person = Person(
        id="@I21@",
        given_names="François",
        surname="BOSQUET",
        sex=Sex.MALE,
    )
    genealogy = Genealogy(persons={person.id: person})
    resolver, local_root, geneweb_root = make_geneweb_resolver(
        tmp_path,
        {"@I21@": "local.jpg"},
    )
    (local_root / "local.jpg").write_bytes(JPEG_SIGNATURE)
    (geneweb_root / "francois.0.bosquet.png").write_bytes(PNG_SIGNATURE)

    local = resolver.resolve(person.id, person.sex, person=person, genealogy=genealogy)

    assert local.kind is PortraitKind.PERSON_LOCAL
    assert local.url == "/portraits/local.jpg"

    unconfigured = PortraitResolver(tmp_path / "missing.json", tmp_path / "missing-local")
    fallback = unconfigured.resolve(
        person.id,
        person.sex,
        person=person,
        genealogy=genealogy,
    )

    assert fallback.kind is PortraitKind.FALLBACK_MALE

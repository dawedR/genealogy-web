from src.domain.models import (
    Event,
    Family,
    Genealogy,
    Person,
    Place,
    PlaceEnrichment,
    PlaceEnrichmentStatus,
)
from src.services.ancestry_geography import build_ancestry_geography


def _birth(place: str | None) -> list[Event]:
    if place is None:
        return []

    return [Event(type="BIRT", place=Place(original_name=place))]


def test_ancestry_geography_keeps_implex_unknown_positions_and_birth_states():
    genealogy = Genealogy(
        persons={
            "@I1@": Person(id="@I1@", events=_birth(None)),
            "@I2@": Person(id="@I2@", events=_birth("Sans enrichissement")),
            "@I3@": Person(id="@I3@", events=_birth("Manuel")),
            "@I4@": Person(id="@I4@", events=_birth("Validé")),
        },
        families={
            "@F1@": Family(
                id="@F1@",
                children=["@I1@"],
                father_id="@I2@",
                mother_id="@I3@",
            ),
            "@F2@": Family(
                id="@F2@",
                children=["@I2@"],
                father_id="@I4@",
            ),
            "@F3@": Family(
                id="@F3@",
                children=["@I3@"],
                father_id="@I4@",
            ),
        },
    )
    enrichments = {
        "Manuel": PlaceEnrichment(
            original_name="Manuel",
            latitude=45.0,
            longitude=4.0,
            status=PlaceEnrichmentStatus.MANUAL,
        ),
        "Validé": PlaceEnrichment(
            original_name="Validé",
            latitude=46.0,
            longitude=5.0,
            status=PlaceEnrichmentStatus.VALIDATED,
        ),
    }

    occurrences = build_ancestry_geography(
        genealogy,
        "@I1@",
        generations=2,
        enrichments=enrichments,
    )

    assert [
        (
            occurrence.sosa,
            occurrence.person_id,
            occurrence.birth_place_original_name,
            occurrence.enrichment.status if occurrence.enrichment else None,
        )
        for occurrence in occurrences
    ] == [
        (1, "@I1@", None, None),
        (2, "@I2@", "Sans enrichissement", None),
        (3, "@I3@", "Manuel", PlaceEnrichmentStatus.MANUAL),
        (4, "@I4@", "Validé", PlaceEnrichmentStatus.VALIDATED),
        (5, None, None, None),
        (6, "@I4@", "Validé", PlaceEnrichmentStatus.VALIDATED),
        (7, None, None, None),
    ]


def test_ancestry_geography_does_not_substitute_a_death_place_for_birth():
    genealogy = Genealogy(
        persons={
            "@I1@": Person(
                id="@I1@",
                events=[Event(type="DEAT", place=Place(original_name="Lyon"))],
            ),
        }
    )

    occurrence = build_ancestry_geography(
        genealogy,
        "@I1@",
        generations=0,
        enrichments={},
    )[0]

    assert occurrence.birth_place_original_name is None
    assert occurrence.enrichment is None

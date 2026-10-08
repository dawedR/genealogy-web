import pytest

from src.domain.models import AdministrativeReference, AdministrativeReferenceStatus
from src.services.cog import CogResolver
from src.services.place_presentation import (
    PlacePresentationService,
    PresentationSource,
    PresentationWarning,
)


def confirmed(original_name: str, code: str, cog_type: str) -> AdministrativeReference:
    candidate = CogResolver.bundled().lookup(code, cog_type)
    assert candidate is not None
    return AdministrativeReference(
        original_name=original_name,
        source="insee_cog",
        vintage="2026",
        cog_code=candidate.code,
        cog_type=candidate.type,
        commune=candidate.commune,
        department_code=candidate.department_code,
        department=candidate.department,
        region_code=candidate.region_code,
        region=candidate.region,
        historical_name=candidate.historical_name,
        valid_from=candidate.valid_from,
        valid_to=candidate.valid_to,
        match_method="TEST",
        status=AdministrativeReferenceStatus.CONFIRMED,
    )


def test_presents_confirmed_current_commune_without_coordinates():
    original = "Chanéac, 07054, Ardèche, Auvergne-Rhône-Alpes, France"

    presentation = PlacePresentationService(CogResolver.bundled()).present(
        original, administrative_reference=confirmed(original, "07054", "COM")
    )

    assert presentation.full_label == (
        "Chanéac, 07054, Ardèche, Auvergne-Rhône-Alpes, France"
    )
    assert presentation.short_label == "Chanéac"
    assert presentation.generated_from is PresentationSource.ADMINISTRATIVE_REFERENCE
    assert {component.kind for component in presentation.components} >= {
        "COMMUNE", "COG_CODE", "DEPARTMENT", "REGION", "COUNTRY"
    }


def test_presents_manual_cog_choice_without_reusing_postcode():
    original = "Francheville, 69340, Rhône, Auvergne-Rhône-Alpes, France"

    presentation = PlacePresentationService(CogResolver.bundled()).present(
        original, administrative_reference=confirmed(original, "69089", "COM")
    )

    assert presentation.full_label == (
        "Francheville, 69089, Rhône, Auvergne-Rhône-Alpes, France"
    )
    assert "69340" not in presentation.full_label


def test_presents_confirmed_arm_with_its_cog_code():
    original = "Paris 12, 75112, Paris, Île-de-France, France"

    presentation = PlacePresentationService(CogResolver.bundled()).present(
        original, administrative_reference=confirmed(original, "75112", "ARM")
    )

    assert presentation.full_label == (
        "Paris 12e arrondissement, 75112, Paris, Île-de-France, France"
    )
    assert presentation.short_label == "Paris 12e arrondissement"


def test_preserves_historical_commune_without_substituting_current_name():
    original = "Bellegarde-sur-Valserine, 01033, Ain, Auvergne-Rhône-Alpes, France"
    resolution = CogResolver.bundled().resolve(original)
    assert resolution.candidate is not None
    reference = AdministrativeReference(
        original_name=original, source="insee_cog", vintage="2026",
        cog_code=resolution.candidate.code, cog_type=resolution.candidate.type,
        commune=resolution.candidate.commune,
        department_code=resolution.candidate.department_code,
        department=resolution.candidate.department,
        region_code=resolution.candidate.region_code, region=resolution.candidate.region,
        historical_name=resolution.candidate.historical_name,
        valid_from=resolution.candidate.valid_from, valid_to=resolution.candidate.valid_to,
        match_method=resolution.method.value, status=AdministrativeReferenceStatus.CONFIRMED,
    )

    presentation = PlacePresentationService(CogResolver.bundled()).present(
        original, administrative_reference=reference
    )

    assert presentation.full_label == (
        "Bellegarde-sur-Valserine, 01033, Ain, Auvergne-Rhône-Alpes, France"
    )
    assert presentation.short_label == "Bellegarde-sur-Valserine"
    assert any(
        component.kind == "CURRENT_COMMUNE" and component.value == "Valserhône"
        for component in presentation.components
    )


def test_preserves_lieu_dit_in_short_label_with_its_source_commune():
    original = "Bois-Rézolle, Les Salles, 42295, Loire, Auvergne-Rhône-Alpes, France"

    presentation = PlacePresentationService(CogResolver.bundled()).present(
        original, administrative_reference=confirmed(original, "42295", "COM")
    )

    assert presentation.full_label == (
        "Bois-Rézolle – Salles, 42295, Loire, Auvergne-Rhône-Alpes, France"
    )
    assert presentation.short_label == "Bois-Rézolle (Les Salles)"


def test_falls_back_to_exact_gedcom_for_unconfirmed_french_and_polish_places():
    service = PlacePresentationService(CogResolver.bundled())
    lyon = "Lyon, 69003, Rhône, Auvergne-Rhône-Alpes, France"
    dolna_wies = "Dolna Wieś (Bodzentyn), powiat de Kielce, gouvernement de Kielce, Pologne"

    lyon_presentation = service.present(lyon)
    polish_presentation = service.present(dolna_wies)

    assert lyon_presentation.full_label == lyon
    assert lyon_presentation.short_label == "Lyon"
    assert polish_presentation.full_label == dolna_wies
    assert polish_presentation.short_label == "Dolna Wieś (Bodzentyn)"
    assert lyon_presentation.warnings == (
        PresentationWarning.NO_CONFIRMED_ADMINISTRATIVE_REFERENCE,
    )
    assert polish_presentation.warnings == (
        PresentationWarning.NO_STRUCTURED_GEOGRAPHIC_REFERENCE,
    )


def test_review_or_obsolete_reference_is_not_used():
    original = "Chanéac, 07054, Ardèche, Auvergne-Rhône-Alpes, France"
    reference = confirmed(original, "07054", "COM")
    review = AdministrativeReference(**{**reference.__dict__, "status": AdministrativeReferenceStatus.REVIEW})
    obsolete = AdministrativeReference(**{**reference.__dict__, "vintage": "2025"})
    service = PlacePresentationService(CogResolver.bundled())

    assert service.present(original, administrative_reference=review).generated_from is PresentationSource.GEDCOM_FALLBACK
    assert service.present(original, administrative_reference=obsolete).warnings == (
        PresentationWarning.ADMINISTRATIVE_REFERENCE_OBSOLETE,
    )


@pytest.mark.parametrize("original_name, short_label", [
    ("Cervières, 42034, Loire, Auvergne-Rhône-Alpes , France", "Cervières"),
    ("Chęciny, powiat de Kielce, gouvernement de Kielce, Pologne", "Chęciny"),
    ("Suchedniów, powiat de Kielce, gouvernement de Kielce, Pologne", "Suchedniów"),
    ("Odrzywół, powiat d'Opoczno, gouvernement de Radom, Pologne", "Odrzywół"),
])
def test_preserves_real_unconfirmed_or_foreign_labels(original_name, short_label):
    presentation = PlacePresentationService(CogResolver.bundled()).present(original_name)

    assert presentation.full_label == original_name
    assert presentation.short_label == short_label
    assert presentation.generated_from is PresentationSource.GEDCOM_FALLBACK

from src.services.cog import (
    CogClassification,
    CogMatchMethod,
    CogReason,
    CogResolver,
    CogWarning,
    SourceCodeKind,
)


def test_cog_resolves_current_commune_with_department_and_region():
    resolution = CogResolver.bundled().resolve(
        "Chanéac, 07054, Ardèche, Auvergne-Rhône-Alpes, France"
    )

    assert resolution.classification is CogClassification.MATCHED
    assert resolution.source_code_kind is SourceCodeKind.COG_CONFIRMED
    assert resolution.candidate is not None
    assert resolution.candidate.code == "07054"
    assert resolution.candidate.type == "COM"
    assert resolution.candidate.commune == "Chanéac"
    assert resolution.candidate.department == "Ardèche"
    assert resolution.candidate.region == "Auvergne-Rhône-Alpes"


def test_cog_resolves_historical_commune_without_replacing_its_name():
    resolution = CogResolver.bundled().resolve(
        "Bellegarde-sur-Valserine, 01033, Ain, Auvergne-Rhône-Alpes, France"
    )

    assert resolution.classification is CogClassification.MATCHED
    assert resolution.source_code_kind is SourceCodeKind.HISTORICAL_COG_CONFIRMED
    assert resolution.method is CogMatchMethod.HISTORICAL_CODE_AND_NAME
    assert resolution.candidate is not None
    assert resolution.candidate.commune == "Valserhône"
    assert resolution.candidate.historical_name == "Bellegarde-sur-Valserine"
    assert resolution.candidate.valid_to == "2019-01-01"


def test_cog_resolves_municipal_arrondissements_for_paris_lyon_and_marseille():
    resolver = CogResolver.bundled()
    cases = {
        "Paris 12, 75112, Paris, Île-de-France, France": ("75112", "Paris 12e Arrondissement"),
        "Lyon 4e arrondissement, 69384, Rhône, Auvergne-Rhône-Alpes, France": ("69384", "Lyon 4e Arrondissement"),
        "Marseille 1er arrondissement, 13201, Bouches-du-Rhône, Provence-Alpes-Côte d'Azur, France": ("13201", "Marseille 1er Arrondissement"),
    }

    for label, (code, commune) in cases.items():
        resolution = resolver.resolve(label)
        assert resolution.classification is CogClassification.MATCHED
        assert resolution.candidate is not None
        assert resolution.candidate.code == code
        assert resolution.candidate.type == "ARM"
        assert resolution.candidate.commune == commune
        assert CogReason.MUNICIPAL_ARRONDISSEMENT_MATCH in resolution.reasons


def test_cog_keeps_historical_detail_when_a_commune_is_embedded_in_the_label():
    resolution = CogResolver.bundled().resolve(
        "Bois-Rézolle, Les Salles, 42295, Loire, Auvergne-Rhône-Alpes, France"
    )

    assert resolution.classification is CogClassification.MATCHED
    assert resolution.method is CogMatchMethod.CODE_AND_EMBEDDED_COMMUNE
    assert resolution.candidate is not None
    assert resolution.candidate.commune == "Salles"
    assert CogWarning.HISTORICAL_DETAIL_PRESERVED in resolution.warnings


def test_cog_does_not_treat_conflicting_lyon_number_as_an_insee_code():
    resolution = CogResolver.bundled().resolve(
        "Lyon, 69003, Rhône, Auvergne-Rhône-Alpes, France"
    )

    assert resolution.classification is CogClassification.REVIEW
    assert resolution.source_code_kind is SourceCodeKind.UNCONFIRMED_FIVE_DIGIT
    assert resolution.candidate is not None
    assert resolution.candidate.commune == "Albigny-sur-Saône"
    assert CogWarning.CODE_DOES_NOT_MATCH_SOURCE_NAME in resolution.warnings
    assert CogWarning.POSTCODE_NOT_INFERRED in resolution.warnings


def test_cog_does_not_infer_a_postcode_when_no_cog_match_exists():
    resolution = CogResolver.bundled().resolve(
        "Francheville, 69340, Rhône, Auvergne-Rhône-Alpes, France"
    )

    assert resolution.classification is CogClassification.NO_MATCH
    assert resolution.source_code_kind is SourceCodeKind.UNCONFIRMED_FIVE_DIGIT
    assert resolution.candidate is None
    assert CogWarning.CODE_NOT_IN_COG in resolution.warnings


def test_cog_supports_exact_lookup_and_local_search_for_manual_selection():
    resolver = CogResolver.bundled()

    selected = resolver.lookup("69384", "ARM")
    found = resolver.search("Francheville")

    assert selected is not None
    assert selected.commune == "Lyon 4e Arrondissement"
    assert any(candidate.code == "69089" and candidate.type == "COM" for candidate in found)

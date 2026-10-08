from src.domain.models import PlaceEnrichment, PlaceEnrichmentStatus
from src.services.place_reconciliation import (
    CoordinateReuseReliability,
    HistoricalMatchClassification,
    HistoricalMatchReason,
    HistoricalMatchWarning,
    reconcile_historical_places,
)
from src.services.places import PlaceInventoryEntry


def active_place(original_name: str) -> PlaceInventoryEntry:
    return PlaceInventoryEntry(
        original_name=original_name,
        occurrences_count=1,
        persons_count=1,
        event_counts={"BIRT": 1},
    )


def historical(
    original_name: str,
    *,
    status: PlaceEnrichmentStatus = PlaceEnrichmentStatus.VALIDATED,
    normalized_name: str | None = None,
    latitude: float | None = 45.0,
    longitude: float | None = 4.0,
) -> PlaceEnrichment:
    return PlaceEnrichment(
        original_name=original_name,
        normalized_name=normalized_name,
        latitude=latitude,
        longitude=longitude,
        status=status,
    )


def reconciliation_by_source(active_places, enrichments):
    return {
        result.source_original_name: result
        for result in reconcile_historical_places(active_places, enrichments)
    }


def test_historical_reconciliation_matches_real_validated_variants_conservatively():
    active_places = [
        active_place("Arcens, 07012, Ardèche, Auvergne-Rhône-Alpes, France"),
        active_place("Bellegarde-sur-Valserine, 01033, Ain, Auvergne-Rhône-Alpes, France"),
        active_place("Chanéac, 07054, Ardèche, Auvergne-Rhône-Alpes, France"),
        active_place("Chęciny, powiat de Kielce, gouvernement de Kielce, Pologne"),
        active_place("Odrzywół, powiat d'Opoczno, gouvernement de Radom, Pologne"),
        active_place("Suchedniów, powiat de Kielce, gouvernement de Kielce, Pologne"),
        active_place("Szydłowiec, powiat de Końskie, gouvernement de Radom, Pologne"),
        active_place("Łódź, powiat de Łódź, gouvernement de Piotrków, Pologne"),
    ]
    enrichments = {
        "Arcens, 07310, Ardèche, Auvergne-Rhône-Alpes, France": historical(
            "Arcens, 07310, Ardèche, Auvergne-Rhône-Alpes, France"
        ),
        "Bellegarde-sur-Valserine, 01200, Ain, Auvergne-Rhône-Alpes, France": historical(
            "Bellegarde-sur-Valserine, 01200, Ain, Auvergne-Rhône-Alpes, France"
        ),
        "Chanéac, 07310, Ardèche, Auvergne-Rhône-Alpes, France": historical(
            "Chanéac, 07310, Ardèche, Auvergne-Rhône-Alpes, France"
        ),
        "Chęciny": historical("Chęciny", normalized_name="Chęciny, Poland"),
        "Odrzywół, powiat (district) d’Opoczno, Radom, Pologne": historical(
            "Odrzywół, powiat (district) d’Opoczno, Radom, Pologne"
        ),
        "Suchedniów, Kielce, Pologne": historical("Suchedniów, Kielce, Pologne"),
        "Szydłowiec": historical("Szydłowiec", normalized_name="Szydłowiec, Poland"),
        "Łódź, Pologne": historical("Łódź, Pologne"),
    }

    results = reconciliation_by_source(active_places, enrichments)

    for name in (
        "Arcens, 07012, Ardèche, Auvergne-Rhône-Alpes, France",
        "Bellegarde-sur-Valserine, 01033, Ain, Auvergne-Rhône-Alpes, France",
        "Chanéac, 07054, Ardèche, Auvergne-Rhône-Alpes, France",
    ):
        assert results[name].classification is HistoricalMatchClassification.REVIEW
        assert HistoricalMatchWarning.CODE_MISMATCH in results[name].proposals[0].warnings

    for name in (
        "Chęciny, powiat de Kielce, gouvernement de Kielce, Pologne",
        "Odrzywół, powiat d'Opoczno, gouvernement de Radom, Pologne",
        "Suchedniów, powiat de Kielce, gouvernement de Kielce, Pologne",
        "Szydłowiec, powiat de Końskie, gouvernement de Radom, Pologne",
        "Łódź, powiat de Łódź, gouvernement de Piotrków, Pologne",
    ):
        assert results[name].classification is HistoricalMatchClassification.STRONG_MATCH
        assert HistoricalMatchReason.LOCALITY_MATCH in results[name].proposals[0].reasons
        assert HistoricalMatchReason.HISTORICAL_ENRICHMENT_VALIDATED in results[name].proposals[0].reasons


def test_historical_reconciliation_separates_label_similarity_from_coordinate_reuse():
    source_name = (
        "Dolna Wieś (Bodzentyn), powiat de Kielce, gouvernement de Kielce, "
        "Pologne"
    )
    historical_name = "Dolna Wieś, Bodzentyn (Kielce), Pologne"
    result = reconciliation_by_source(
        [active_place(source_name)],
        {
            historical_name: historical(
                historical_name,
                normalized_name=(
                    "Dolna Wieś (Świślina), Pawłów, Świętokrzyskie, Poland"
                ),
                latitude=50.9730556,
                longitude=21.0488889,
            )
        },
    )[source_name]

    proposal = result.proposals[0]
    assert proposal.score == 69
    assert proposal.classification is HistoricalMatchClassification.REVIEW
    assert proposal.coordinate_reuse_reliability is CoordinateReuseReliability.REVIEW
    assert HistoricalMatchWarning.NORMALIZED_SECONDARY_TOPONYMS_DIFFER in proposal.warnings
    assert HistoricalMatchReason.HISTORICAL_ENRICHMENT_VALIDATED in proposal.reasons
    assert HistoricalMatchReason.HISTORICAL_COORDINATES_AVAILABLE in proposal.reasons


def test_historical_reconciliation_reports_missing_secondary_toponyms_without_claiming_conflict():
    source_name = "Chęciny, powiat de Kielce, gouvernement de Kielce, Pologne"
    proposal = reconciliation_by_source(
        [active_place(source_name)],
        {"Chęciny": historical("Chęciny", normalized_name="Chęciny, SK, Poland")},
    )[source_name].proposals[0]

    assert proposal.classification is HistoricalMatchClassification.STRONG_MATCH
    assert proposal.coordinate_reuse_reliability is CoordinateReuseReliability.HIGH_CONFIDENCE
    assert HistoricalMatchWarning.SECONDARY_TOPONYMS_NOT_DOCUMENTED in proposal.warnings


def test_historical_reconciliation_marks_uncertain_and_manual_variants_for_review():
    active_places = [
        active_place("Écully, 69081, Rhône, Auvergne-Rhône-Alpes, France"),
        active_place("? Écully, 69081, Rhône, Auvergne-Rhône-Alpes, France"),
        active_place("Les Salles, 42295, Loire, Auvergne-Rhône-Alpes, France"),
        active_place("Noirétable, 42159, Loire, Auvergne-Rhône-Alpes, France"),
    ]
    enrichments = {
        "Ecully": historical(
            "Ecully",
            status=PlaceEnrichmentStatus.MANUAL,
            latitude=None,
            longitude=None,
        ),
        "Les Salles, 42295, Loire, Rhône-Alpes, France": historical(
            "Les Salles, 42295, Loire, Rhône-Alpes, France",
            status=PlaceEnrichmentStatus.MANUAL,
        ),
        "Noirétable, 42159, Loire, Rhône-Alpes, France": historical(
            "Noirétable, 42159, Loire, Rhône-Alpes, France"
        ),
    }

    results = reconciliation_by_source(active_places, enrichments)

    assert results["Écully, 69081, Rhône, Auvergne-Rhône-Alpes, France"].classification is HistoricalMatchClassification.REVIEW
    assert HistoricalMatchWarning.LOCALITY_ONLY_MATCH in results[
        "Écully, 69081, Rhône, Auvergne-Rhône-Alpes, France"
    ].proposals[0].warnings
    uncertain = results["? Écully, 69081, Rhône, Auvergne-Rhône-Alpes, France"]
    assert uncertain.classification is HistoricalMatchClassification.REVIEW
    assert HistoricalMatchWarning.LEADING_UNCERTAINTY_MARKER in uncertain.proposals[0].warnings
    assert results["Les Salles, 42295, Loire, Auvergne-Rhône-Alpes, France"].classification is HistoricalMatchClassification.REVIEW
    assert results["Noirétable, 42159, Loire, Auvergne-Rhône-Alpes, France"].classification is HistoricalMatchClassification.STRONG_MATCH


def test_historical_reconciliation_does_not_merge_lyon_arrondissements():
    source = active_place("? Lyon, 69004, Rhône, Auvergne-Rhône-Alpes, France")
    enrichments = {
        "Lyon 4 ?": historical(
            "Lyon 4 ?",
            status=PlaceEnrichmentStatus.MANUAL,
            normalized_name="4th Arrondissement, 69004 Lyon, France",
        ),
        "Lyon, 69002, Rhône, Auvergne-Rhône-Alpes, France": historical(
            "Lyon, 69002, Rhône, Auvergne-Rhône-Alpes, France"
        ),
        "Lyon 3": historical("Lyon 3", normalized_name="3rd Arrondissement, 69003 Lyon, France"),
    }

    result = reconciliation_by_source([source], enrichments)[source.original_name]

    assert result.classification is HistoricalMatchClassification.REVIEW
    assert [proposal.historical_original_name for proposal in result.proposals] == ["Lyon 4 ?"]
    assert HistoricalMatchReason.DISTRICT_NUMBER_MATCHES_CODE_SUFFIX in result.proposals[0].reasons


def test_historical_reconciliation_marks_equally_plausible_coordinates_ambiguous():
    source = active_place("Wysokie, Pologne")
    enrichments = {
        "Wysokie (A), Pologne": historical(
            "Wysokie (A), Pologne", latitude=50.0, longitude=20.0
        ),
        "Wysokie (B), Pologne": historical(
            "Wysokie (B), Pologne", latitude=51.0, longitude=21.0
        ),
    }

    result = reconciliation_by_source([source], enrichments)[source.original_name]

    assert result.classification is HistoricalMatchClassification.AMBIGUOUS
    assert len(result.proposals) == 2
    assert all(
        proposal.classification is HistoricalMatchClassification.AMBIGUOUS
        for proposal in result.proposals
    )
    assert all(
        HistoricalMatchWarning.COMPETING_HISTORICAL_MATCHES in proposal.warnings
        for proposal in result.proposals
    )


def test_historical_reconciliation_reports_no_match_and_ignores_exact_active_enrichments():
    active_places = [active_place("Inconnu, France"), active_place("Exact, France")]
    enrichments = {
        "Exact, France": historical("Exact, France"),
        "Autre, France": historical("Autre, France"),
    }

    results = reconciliation_by_source(active_places, enrichments)

    assert list(results) == ["Inconnu, France"]
    assert results["Inconnu, France"].classification is HistoricalMatchClassification.NO_MATCH
    assert results["Inconnu, France"].proposals == ()

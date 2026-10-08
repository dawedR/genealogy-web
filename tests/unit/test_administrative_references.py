import json

from src.domain.models import AdministrativeReference, AdministrativeReferenceStatus
from src.storage.administrative_references import JsonAdministrativeReferenceStore


def reference(**changes) -> AdministrativeReference:
    values = {
        "original_name": "Chanéac, 07054, Ardèche, Auvergne-Rhône-Alpes, France",
        "source": "insee_cog",
        "vintage": "2026",
        "cog_code": "07054",
        "cog_type": "COM",
        "commune": "Chanéac",
        "department_code": "07",
        "department": "Ardèche",
        "region_code": "84",
        "region": "Auvergne-Rhône-Alpes",
        "historical_name": None,
        "valid_from": None,
        "valid_to": None,
        "match_method": "CURRENT_CODE_AND_NAME",
        "status": AdministrativeReferenceStatus.CONFIRMED,
        "human_note": None,
    }
    values.update(changes)
    return AdministrativeReference(**values)


def test_json_store_is_empty_when_absent_and_round_trips_human_decision(tmp_path):
    path = tmp_path / "administrative_references.json"
    store = JsonAdministrativeReferenceStore(path)
    assert store.get_all() == {}

    saved = reference(status=AdministrativeReferenceStatus.REVIEW, human_note="Vérifier l'acte")
    store.save(saved)

    assert JsonAdministrativeReferenceStore(path).get(saved.original_name) == saved
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["version"] == 1
    assert document["references"][saved.original_name]["human_note"] == "Vérifier l'acte"


def test_store_removes_only_requested_exact_original_label(tmp_path):
    store = JsonAdministrativeReferenceStore(tmp_path / "administrative_references.json")
    first = reference()
    second = reference(original_name="Chaneac, France")
    store.save(first)
    store.save(second)

    store.delete(first.original_name)

    assert store.get(first.original_name) is None
    assert store.get(second.original_name) == second

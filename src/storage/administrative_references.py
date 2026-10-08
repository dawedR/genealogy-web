from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from src.domain.models import AdministrativeReference, AdministrativeReferenceStatus


class AdministrativeReferenceStore(Protocol):
    """Persistence boundary for human COG attachment decisions."""

    def get(self, original_name: str) -> AdministrativeReference | None: ...

    def get_all(self) -> dict[str, AdministrativeReference]: ...

    def save(self, reference: AdministrativeReference) -> None: ...

    def delete(self, original_name: str) -> None: ...


class InMemoryAdministrativeReferenceStore:
    def __init__(self) -> None:
        self._references: dict[str, AdministrativeReference] = {}

    def get(self, original_name: str) -> AdministrativeReference | None:
        return self._references.get(original_name)

    def get_all(self) -> dict[str, AdministrativeReference]:
        return dict(self._references)

    def save(self, reference: AdministrativeReference) -> None:
        self._references[reference.original_name] = reference

    def delete(self, original_name: str) -> None:
        self._references.pop(original_name, None)


class JsonAdministrativeReferenceStore:
    """Versioned JSON store with atomic replacement writes."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def get(self, original_name: str) -> AdministrativeReference | None:
        return self.get_all().get(original_name)

    def get_all(self) -> dict[str, AdministrativeReference]:
        if not self._path.exists():
            return {}
        with self._path.open(encoding="utf-8") as file:
            document = json.load(file)
        if document.get("version") != 1 or not isinstance(document.get("references"), Mapping):
            raise ValueError("Invalid administrative references document")
        references: dict[str, AdministrativeReference] = {}
        for original_name, payload in document["references"].items():
            if not isinstance(original_name, str) or not isinstance(payload, Mapping):
                raise ValueError("Invalid administrative reference entry")
            reference = _deserialize(payload)
            if reference.original_name != original_name:
                raise ValueError("Administrative reference key does not match original_name")
            references[original_name] = reference
        return references

    def save(self, reference: AdministrativeReference) -> None:
        references = self.get_all()
        references[reference.original_name] = reference
        self._write(references)

    def delete(self, original_name: str) -> None:
        references = self.get_all()
        if original_name in references:
            del references[original_name]
            self._write(references)

    def _write(self, references: Mapping[str, AdministrativeReference]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "version": 1,
            "references": {
                name: _serialize(reference)
                for name, reference in sorted(references.items())
            },
        }
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self._path.parent,
                prefix=f".{self._path.name}.", suffix=".tmp", delete=False,
            ) as file:
                temporary = Path(file.name)
                json.dump(document, file, ensure_ascii=False, indent=2, sort_keys=True)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self._path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()


def _serialize(reference: AdministrativeReference) -> dict[str, object]:
    return {
        "original_name": reference.original_name,
        "source": reference.source,
        "vintage": reference.vintage,
        "cog_code": reference.cog_code,
        "cog_type": reference.cog_type,
        "commune": reference.commune,
        "department_code": reference.department_code,
        "department": reference.department,
        "region_code": reference.region_code,
        "region": reference.region,
        "historical_name": reference.historical_name,
        "valid_from": reference.valid_from,
        "valid_to": reference.valid_to,
        "match_method": reference.match_method,
        "status": reference.status.value,
        "human_note": reference.human_note,
    }


def _deserialize(payload: Mapping[str, object]) -> AdministrativeReference:
    def required(name: str) -> str:
        value = payload.get(name)
        if not isinstance(value, str):
            raise ValueError(f"Invalid administrative reference {name}")
        return value

    def optional(name: str) -> str | None:
        value = payload.get(name)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"Invalid administrative reference {name}")
        return value

    return AdministrativeReference(
        original_name=required("original_name"), source=required("source"),
        vintage=required("vintage"), cog_code=required("cog_code"),
        cog_type=required("cog_type"), commune=required("commune"),
        department_code=optional("department_code"), department=optional("department"),
        region_code=optional("region_code"), region=optional("region"),
        historical_name=optional("historical_name"), valid_from=optional("valid_from"),
        valid_to=optional("valid_to"), match_method=required("match_method"),
        status=AdministrativeReferenceStatus(required("status")),
        human_note=optional("human_note"),
    )

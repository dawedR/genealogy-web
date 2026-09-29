from __future__ import annotations

from dataclasses import dataclass

from src.domain.models import Event, Genealogy


@dataclass(frozen=True)
class PlaceInventoryEntry:
    """Usage statistics for one exact GEDCOM place label."""

    original_name: str
    occurrences_count: int
    persons_count: int
    event_counts: dict[str, int]


@dataclass
class _PlaceAccumulator:
    occurrences_count: int
    person_ids: set[str]
    event_counts: dict[str, int]


def inventory_places(
    genealogy: Genealogy,
) -> list[PlaceInventoryEntry]:
    """Inventory event places without normalizing their GEDCOM labels.

    An individual event concerns its owner. A family event concerns its
    known partners, never its children. Each Event object is counted at most
    once, even if malformed input references that same object repeatedly.
    """

    accumulators: dict[str, _PlaceAccumulator] = {}
    seen_event_ids: set[int] = set()

    for person in genealogy.persons.values():
        for event in person.events:
            _record_event(
                event,
                {person.id},
                accumulators,
                seen_event_ids,
            )

    for family in genealogy.families.values():
        partner_ids = {
            partner_id
            for partner_id in family.partners
            if partner_id in genealogy.persons
        }

        for event in family.events:
            _record_event(
                event,
                partner_ids,
                accumulators,
                seen_event_ids,
            )

    entries = [
        PlaceInventoryEntry(
            original_name=original_name,
            occurrences_count=accumulator.occurrences_count,
            persons_count=len(accumulator.person_ids),
            event_counts=dict(sorted(accumulator.event_counts.items())),
        )
        for original_name, accumulator in accumulators.items()
    ]

    return sorted(
        entries,
        key=lambda entry: (
            -entry.occurrences_count,
            entry.original_name.casefold(),
            entry.original_name,
        ),
    )


def _record_event(
    event: Event,
    person_ids: set[str],
    accumulators: dict[str, _PlaceAccumulator],
    seen_event_ids: set[int],
) -> None:
    if event.place is None or id(event) in seen_event_ids:
        return

    seen_event_ids.add(id(event))

    original_name = event.place.original_name
    accumulator = accumulators.setdefault(
        original_name,
        _PlaceAccumulator(
            occurrences_count=0,
            person_ids=set(),
            event_counts={},
        ),
    )

    accumulator.occurrences_count += 1
    accumulator.person_ids.update(person_ids)
    accumulator.event_counts[event.type] = (
        accumulator.event_counts.get(event.type, 0) + 1
    )

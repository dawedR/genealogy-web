from src.domain.models import Event, Family, Genealogy, Person, Place
from src.services.places import PlaceInventoryEntry, inventory_places


def place(name: str) -> Place:
    return Place(original_name=name)


def test_inventory_counts_individual_and_family_events():
    jean = Person(
        id="@I1@",
        events=[
            Event(type="BIRT", place=place("Écully, France")),
            Event(type="DEAT", place=place("Lyon, France")),
        ],
    )
    marie = Person(
        id="@I2@",
        events=[
            Event(type="BIRT", place=place("Écully, France")),
        ],
    )
    child = Person(id="@I3@")
    family = Family(
        id="@F1@",
        partners=["@I1@", "@I2@", "@UNKNOWN@", "@I1@"],
        children=["@I3@"],
        events=[
            Event(type="MARR", place=place("Écully, France")),
            Event(type="EVEN", place=place("Écully, France")),
        ],
    )

    entries = inventory_places(
        Genealogy(
            persons={
                jean.id: jean,
                marie.id: marie,
                child.id: child,
            },
            families={family.id: family},
        )
    )

    # Family events count once each; their child and missing partner
    # do not inflate the set of concerned people.
    assert entries == [
        PlaceInventoryEntry(
            original_name="Écully, France",
            occurrences_count=4,
            persons_count=2,
            event_counts={"BIRT": 2, "EVEN": 1, "MARR": 1},
        ),
        PlaceInventoryEntry(
            original_name="Lyon, France",
            occurrences_count=1,
            persons_count=1,
            event_counts={"DEAT": 1},
        ),
    ]


def test_inventory_uses_exact_labels_and_counts_one_event_once():
    shared_event = Event(type="BIRT", place=place("Łódź, Pologne"))
    person = Person(
        id="@I1@",
        events=[shared_event, shared_event],
    )
    other = Person(
        id="@I2@",
        events=[Event(type="BAPM", place=place("Lodz, Pologne"))],
    )

    entries = inventory_places(
        Genealogy(persons={person.id: person, other.id: other})
    )

    assert [entry.original_name for entry in entries] == [
        "Lodz, Pologne",
        "Łódź, Pologne",
    ]
    assert entries[0].occurrences_count == 1
    assert entries[0].event_counts == {"BAPM": 1}
    assert entries[1].occurrences_count == 1
    assert entries[1].event_counts == {"BIRT": 1}


def test_inventory_does_not_use_deduplicated_genealogy_places():
    genealogy = Genealogy(
        places=[Place(original_name="Lieu sans événement")]
    )

    assert inventory_places(genealogy) == []

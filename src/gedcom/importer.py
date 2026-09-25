from __future__ import annotations

from pathlib import Path

from ged4py.parser import GedcomReader

from src.domain.models import (
    Event,
    EventDate,
    Family,
    Genealogy,
    IgnoredTag,
    ImportReport,
    Person,
    Place,
    Sex,
)


def import_gedcom(path: str | Path) -> tuple[Genealogy, ImportReport]:
    """Import a GEDCOM file into the domain model."""

    genealogy = Genealogy()
    ignored_tags: list[IgnoredTag] = []

    with GedcomReader(str(path)) as parser:
        for record in parser.records0():
            if record.tag == "INDI":
                person = _import_person(record)
                genealogy.persons[person.id] = person

                for sub_record in record.sub_records:
                    if sub_record.tag.startswith("_"):
                        ignored_tags.append(
                            IgnoredTag(
                                tag=sub_record.tag,
                                record_id=record.xref_id,
                            )
                        )

            elif record.tag == "FAM":
                family = _import_family(record)
                genealogy.families[family.id] = family

    for person in genealogy.persons.values():
        genealogy.events.extend(person.events)

    for family in genealogy.families.values():
        genealogy.events.extend(family.events)

    places_by_name: dict[str, Place] = {}

    for event in genealogy.events:
        if event.place is not None:
            places_by_name.setdefault(
                event.place.original_name,
                event.place,
            )

    genealogy.places = list(places_by_name.values())
    
    report = ImportReport(
        persons_count=len(genealogy.persons),
        families_count=len(genealogy.families),
        events_count=len(genealogy.events),
        places_count=len(genealogy.places),
        ignored_tags=ignored_tags,
    )

    return genealogy, report


def _import_person(record) -> Person:
    given_names, surname = _name(record)

    person = Person(
        id=record.xref_id,
        given_names=given_names,
        surname=surname,
        sex=_parse_sex(_value(record, "SEX")),
    )

    for occupation in record.sub_tags("OCCU"):
        if occupation.value:
            person.occupations.append(str(occupation.value))

    for tag in ("BIRT", "BAPM", "NATU", "DEAT", "BURI", "CREM"):
        event_record = record.sub_tag(tag)

        if event_record is not None:
            person.events.append(_import_event(event_record, tag))

    return person

def _import_family(record) -> Family:
    family = Family(id=record.xref_id)

    husband = record.sub_tag("HUSB")
    wife = record.sub_tag("WIFE")

    if husband is not None:
        family.partners.append(husband.xref_id)

    if wife is not None:
        family.partners.append(wife.xref_id)

    for child in record.sub_tags("CHIL"):
        family.children.append(child.xref_id)

    for tag in ("MARR", "DIV", "EVEN"):
        event_record = record.sub_tag(tag)

        if event_record is not None:
            family.events.append(_import_event(event_record, tag))

    return family


def _import_event(record, event_type: str) -> Event:
    date_value = _value(record, "DATE")
    place_value = _value(record, "PLAC")
    detail = _value(record, "TYPE")

    return Event(
        type=event_type,
        detail=detail,
        date=EventDate(value=date_value) if date_value else None,
        place=Place(original_name=place_value) if place_value else None,
    )

def _value(record, tag: str) -> str | None:
    sub_record = record.sub_tag(tag)

    if sub_record is None or sub_record.value is None:
        return None

    return str(sub_record.value)


def _name(record) -> tuple[str, str]:
    name_record = record.sub_tag("NAME")

    if name_record is None or name_record.value is None:
        return "", ""

    value = name_record.value

    if isinstance(value, tuple):
        given_names = value[0] if len(value) > 0 else ""
        surname = value[1] if len(value) > 1 else ""

        return (
            str(given_names or "").strip(),
            str(surname or "").strip(),
        )

    return str(value).strip(), ""


def _parse_sex(value: str | None) -> Sex:
    if value == "M":
        return Sex.MALE

    if value == "F":
        return Sex.FEMALE

    return Sex.UNKNOWN
"""Presentation-only content for combined-tree person cards."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.domain.models import Genealogy, Sex
from src.services.combined_tree import TreePersonOccurrence
from src.services.portraits import PortraitReference, PortraitResolver
from src.services.search import get_birth_date, get_death_date


_MONTHS = {
    "JAN": "JAN",
    "FEB": "FEV",
    "MAR": "MAR",
    "APR": "AVR",
    "MAY": "MAI",
    "JUN": "JUIN",
    "JUL": "JUIL",
    "AUG": "AOUT",
    "SEP": "SEP",
    "OCT": "OCT",
    "NOV": "NOV",
    "DEC": "DEC",
}

_APPROXIMATE_DATE_MARKERS = {
    "ABOUT": "~",
    "ABT": "~",
    "BEFORE": "<",
    "BEF": "<",
    "AFTER": ">",
    "AFT": ">",
}


@dataclass(frozen=True)
class TreePersonCard:
    occurrence_id: str
    person_id: str | None
    is_unknown: bool
    sex: Sex | None
    given_names: str | None
    display_given_name: str | None
    surname: str | None
    display_surname: str | None
    birth_date: str | None
    display_birth_date: str | None
    death_date: str | None
    display_death_date: str | None
    portrait: PortraitReference


def build_tree_person_card(
    occurrence: TreePersonOccurrence,
    genealogy: Genealogy,
    portraits: PortraitResolver,
) -> TreePersonCard:
    person = (
        genealogy.persons.get(occurrence.person_id)
        if occurrence.person_id is not None
        else None
    )
    if person is None:
        return TreePersonCard(
            occurrence_id=occurrence.id,
            person_id=occurrence.person_id,
            is_unknown=True,
            sex=None,
            given_names=None,
            display_given_name=None,
            surname=None,
            display_surname=None,
            birth_date=None,
            display_birth_date=None,
            death_date=None,
            display_death_date=None,
            portrait=portraits.resolve(None, Sex.UNKNOWN),
        )

    birth_date = get_birth_date(person)
    death_date = get_death_date(person)
    return TreePersonCard(
        occurrence_id=occurrence.id,
        person_id=person.id,
        is_unknown=False,
        sex=person.sex,
        given_names=person.given_names or None,
        display_given_name=person.given_names or None,
        surname=person.surname or None,
        display_surname=person.surname.upper() or None,
        birth_date=birth_date,
        display_birth_date=format_tree_date(birth_date),
        death_date=death_date,
        display_death_date=format_tree_date(death_date),
        portrait=portraits.resolve(
            person.id,
            person.sex,
            person=person,
            genealogy=genealogy,
        ),
    )


def format_tree_date(value: str | None) -> str | None:
    """Format a GEDCOM date for tree cards without changing its source value."""
    if value is None:
        return None
    display = re.sub(r"\b0(\d)\b", r"\1", value)
    display = re.sub(
        r"\b([A-Z]{3})\b",
        lambda match: _MONTHS.get(match.group(1), match.group(1)),
        display,
    )
    return re.sub(
        r"^(ABOUT|ABT|BEFORE|BEF|AFTER|AFT)(\s+)",
        lambda match: _APPROXIMATE_DATE_MARKERS[match.group(1)] + match.group(2),
        display,
    )

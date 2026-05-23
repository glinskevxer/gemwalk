"""The cover faults where the rest of the paperwork can see them."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.model.fault import Damage
from gemwalk.report.annual import annual_report
from gemwalk.service.office import Office
from gemwalk.service.review import review
from gemwalk.store.book import Book
from tests.support import SITE, furnish

FOUND = dt.date(2025, 5, 13)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def a_fault(office: Office, kind: Damage = Damage.SETTLEMENT) -> str:
    return office.surface.find_fault(
        "A-03", kind, "grid 14-J", extent=120.0, on=FOUND, found_by="T. W."
    ).label


def cover_words(office: Office) -> str:
    section = annual_report(office, SITE, 2025).find("what the cover produced")
    assert section is not None
    return "\n".join(section.lines())


def test_a_year_with_a_sound_cover_says_so(office: Office) -> None:
    assert "nothing was found wrong with the cover" in cover_words(office)


def test_a_fault_is_counted_in_the_year(office: Office) -> None:
    a_fault(office)
    assert "1 faults found on the cover, 0 fixed" in cover_words(office)


def test_a_fault_fixed_late_is_counted_as_late(office: Office) -> None:
    label = a_fault(office)
    office.surface.fix_fault(label, dt.date(2025, 7, 1))
    body = cover_words(office)
    assert "1 fixed" in body
    assert "1 of those after the date" in body


def test_a_fault_fixed_in_time_is_not_counted_as_late(office: Office) -> None:
    label = a_fault(office)
    office.surface.fix_fault(label, dt.date(2025, 5, 20))
    assert "0 of those after the date" in cover_words(office)


def test_a_walk_that_missed_legs_is_odd_in_the_review(office: Office) -> None:
    office.surface.lay_pattern("A-03", legs=2, metres=400.0)
    walk = office.surface.open_walk(
        SITE,
        FOUND,
        monitor="T. W.",
        instrument="TVA-1",
        background=2.0,
        wind_mean=3.4,
        wind_gust=7.1,
    ).label
    office.surface.cross(walk, "A-03-L01")
    office.surface.finish_walk(walk, FOUND)
    said = "\n".join(str(finding) for finding in review(office, SITE))
    assert "finished having missed 1 legs in A-03" in said


def test_a_whole_walk_is_not_odd(office: Office) -> None:
    legs = office.surface.lay_pattern("A-03", legs=2, metres=400.0)
    walk = office.surface.open_walk(
        SITE,
        FOUND,
        monitor="T. W.",
        instrument="TVA-1",
        background=2.0,
        wind_mean=3.4,
        wind_gust=7.1,
    ).label
    for leg in legs:
        office.surface.cross(walk, leg.label)
    office.surface.finish_walk(walk, FOUND)
    assert review(office, SITE) == []

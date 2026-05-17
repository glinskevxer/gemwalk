"""Cover faults through the surface desk."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Quarter
from gemwalk.model.fault import Damage
from gemwalk.report.compliance import compliance_report
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, furnish

FOUND = dt.date(2025, 5, 13)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def a_fault(
    office: Office,
    kind: Damage = Damage.SETTLEMENT,
    extent: float = 120.0,
    station: str = "grid 14-J",
    on: dt.date = FOUND,
) -> str:
    return office.surface.find_fault(
        "A-03", kind, station, extent=extent, on=on, found_by="T. Wierzbicki"
    ).label


def test_a_fault_takes_the_label_of_its_year(office: Office) -> None:
    assert a_fault(office) == "CF-2025-001"


def test_an_ordinary_fault_gets_the_long_window(office: Office) -> None:
    label = a_fault(office)
    assert office.surface.faults.get(label).due == dt.date(2025, 6, 12)


def test_exposed_refuse_gets_the_short_one(office: Office) -> None:
    label = a_fault(office, Damage.EXPOSED, extent=2.0)
    assert office.surface.faults.get(label).due == dt.date(2025, 5, 23)


def test_a_site_with_a_sound_cover_has_nothing_open(office: Office) -> None:
    assert office.surface.open_faults(SITE, FOUND) == []
    assert office.surface.late_faults(SITE, FOUND) == []


def test_the_least_time_left_comes_first(office: Office) -> None:
    slow = a_fault(office)
    quick = a_fault(office, Damage.CRACK, extent=2.0, station="grid 21-C")
    assert [f.label for f in office.surface.open_faults(SITE, FOUND)] == [quick, slow]


def test_a_fault_past_its_window_is_late(office: Office) -> None:
    a_fault(office, Damage.CRACK, extent=2.0)
    assert office.surface.late_faults(SITE, dt.date(2025, 5, 23)) == []
    assert len(office.surface.late_faults(SITE, dt.date(2025, 5, 24))) == 1


def test_a_fixed_fault_leaves_the_board(office: Office) -> None:
    label = a_fault(office)
    office.surface.fix_fault(label, dt.date(2025, 5, 20), "regraded and seeded")
    assert office.surface.open_faults(SITE, dt.date(2025, 5, 21)) == []
    assert office.surface.faults.get(label).note == "regraded and seeded"


def test_the_history_of_one_place_comes_back_oldest_first(office: Office) -> None:
    first = a_fault(office)
    second = a_fault(office, on=dt.date(2025, 8, 6))
    assert [f.label for f in office.surface.faults_at(SITE, "grid 14-J")] == [first, second]


def test_a_place_nothing_was_found_at_has_no_history(office: Office) -> None:
    assert office.surface.faults_at(SITE, "grid 99-Z") == []


def test_the_compliance_report_carries_the_cover(office: Office) -> None:
    a_fault(office, Damage.EXPOSED, extent=2.0)
    section = compliance_report(office, SITE, Quarter(2025, 2)).find("the cover itself")
    assert section is not None
    body = "\n".join(section.lines())
    assert "1 faults open on the cover" in body
    assert "exposed refuse" in body


def test_a_sound_cover_says_so_in_the_report(office: Office) -> None:
    section = compliance_report(office, SITE, Quarter(2025, 2)).find("the cover itself")
    assert section is not None
    assert "nothing is wrong with the cover" in "\n".join(section.lines())

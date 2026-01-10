"""Coverage read through the wellfield desk."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, furnish

APRIL = dt.date(2025, 4, 30)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def test_a_device_takes_the_radius_its_area_was_designed_around(office: Office) -> None:
    office.wellfield.set_radius("A-03", 200.0)
    made = office.wellfield.drill(
        SITE,
        "A-03",
        station="N 20+00",
        total_depth=90.0,
        screen_top=20.0,
        screen_bottom=84.0,
        on=dt.date(2025, 4, 2),
    )
    assert made.influence == pytest.approx(200.0)


def test_a_device_can_be_given_a_radius_of_its_own(office: Office) -> None:
    made = office.wellfield.drill(
        SITE,
        "A-03",
        station="N 20+00",
        total_depth=90.0,
        screen_top=20.0,
        screen_bottom=84.0,
        on=dt.date(2025, 4, 2),
        influence=150.0,
    )
    assert made.influence == pytest.approx(150.0)


def test_the_areas_of_a_site_are_read_in_label_order(office: Office) -> None:
    reads = office.wellfield.coverage_at(SITE)
    assert [read.area for read in reads] == ["A-03", "A-04"]


def test_an_area_with_two_devices_in_it_counts_two(office: Office) -> None:
    read = office.wellfield.coverage_of("A-03")
    assert len(read.devices) == 2
    assert read.wanted > 2


def test_a_wider_design_radius_wants_fewer_devices(office: Office) -> None:
    narrow = office.wellfield.coverage_of("A-03").wanted
    office.wellfield.set_radius("A-03", 250.0)
    assert office.wellfield.coverage_of("A-03").wanted < narrow


def test_an_area_short_of_devices_is_listed_with_its_deadline(office: Office) -> None:
    short = office.wellfield.shortfalls(SITE, APRIL)
    assert [s.coverage.area for s in short] == ["A-03", "A-04"]
    assert short[0].due == dt.date(2024, 4, 15)
    assert short[0].overdue


def test_an_area_not_yet_past_its_deadline_is_short_and_not_overdue(office: Office) -> None:
    short = office.wellfield.shortfalls(SITE, dt.date(2024, 1, 1))
    assert all(not s.overdue for s in short)


def test_an_area_with_enough_devices_is_not_listed(office: Office) -> None:
    office.wellfield.set_radius("A-03", 400.0)
    short = office.wellfield.shortfalls(SITE, APRIL)
    assert [s.coverage.area for s in short] == ["A-04"]


def test_the_shortfall_prints_the_sentence_the_report_uses(office: Office) -> None:
    short = office.wellfield.shortfalls(SITE, APRIL)[0]
    assert "more overdue since" in str(short)
    assert "A-03" in str(short)


def test_the_monthly_report_carries_the_shortfall(office: Office) -> None:
    from gemwalk.clock import Month
    from gemwalk.report.monthly import monthly_report

    section = monthly_report(office, SITE, Month(2025, 4)).find("the site")
    assert section is not None
    assert any("more overdue since" in line for line in section.body)

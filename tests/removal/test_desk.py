"""The removal case read through the site desk."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.nmoc import Inputs, rate
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import furnish

ASKED = dt.date(2025, 6, 30)


OLD = "OLDFIELD"


@pytest.fixture
def office(book: Book) -> Office:
    made = furnish(Office(book))
    made.sites.open_site(
        OLD,
        "Oldfield Landfill",
        subpart="Cf",
        permit="MSW-0904-11",
        zone="America/Chicago",
        design_capacity=4_100_000.0,
        opened_on=dt.date(1985, 4, 1),
    )
    made.sites.add_area("C-01", OLD, "the whole hill", acres=22.0, first_waste=dt.date(1986, 5, 1))
    made.sites.stop_filling("C-01", dt.date(2004, 12, 1))
    made.sites.close_area("C-01", dt.date(2005, 6, 1))
    return made


def a_sample(day: dt.date, ppmv: float) -> tuple[dt.date, object]:
    return day, rate(Inputs(acceptance=180_000.0, age=40.0).measure_concentration(ppmv))


def test_a_site_still_open_cannot_turn_anything_off(office: Office) -> None:
    read = office.sites.removal_case(OLD, ASKED, [])
    assert not read.is_allowed
    assert "still taking waste" in read.missing[0]


def test_a_closed_site_with_no_samples_is_short_of_them(office: Office) -> None:
    office.sites.close_site(OLD, dt.date(2005, 6, 30))
    read = office.sites.removal_case(OLD, ASKED, [])
    assert read.long_enough
    assert not read.enough_tests
    assert any("samples on file" in said for said in read.missing)


def test_a_closed_site_with_three_good_samples_may_turn_off(office: Office) -> None:
    office.sites.close_site(OLD, dt.date(2005, 6, 30))
    samples = [
        a_sample(dt.date(2024, 1, 1), 50.0),
        a_sample(dt.date(2024, 5, 1), 45.0),
        a_sample(dt.date(2024, 9, 1), 40.0),
    ]
    read = office.sites.removal_case(OLD, ASKED, samples)  # type: ignore[arg-type]
    assert read.is_allowed
    assert "may be turned off" in str(read)


def test_a_sample_over_the_threshold_stops_it(office: Office) -> None:
    office.sites.close_site(OLD, dt.date(2005, 6, 30))
    samples = [
        a_sample(dt.date(2024, 1, 1), 50.0),
        a_sample(dt.date(2024, 5, 1), 900.0),
        a_sample(dt.date(2024, 9, 1), 40.0),
    ]
    read = office.sites.removal_case(OLD, ASKED, samples)  # type: ignore[arg-type]
    assert not read.all_under


def test_the_case_uses_the_day_the_site_actually_closed(office: Office) -> None:
    office.sites.close_site(OLD, dt.date(2020, 6, 30))
    read = office.sites.removal_case(OLD, ASKED, [])
    assert read.years_closed == pytest.approx(5.0, abs=0.1)
    assert not read.long_enough

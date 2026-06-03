"""The plant report, which reads a period rather than a day."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.model.plant import ControlKind
from gemwalk.report.plant import plant_report
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, ZONE, furnish

FIRST = read_moment("2025-06-11 00:00", ZONE)
LAST = read_moment("2025-06-14 00:00", ZONE)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def words(office: Office, heading: str) -> str:
    section = plant_report(office, SITE, FIRST, LAST).find(heading)
    assert section is not None
    return "\n".join(section.lines())


def log(office: Office, hour: int, temperature: float) -> None:
    office.plant.log(
        "CD-01",
        read_moment(f"2025-06-11 {hour:02d}:00", ZONE),
        running=True,
        flow=1_180.0,
        methane=49.2,
        temperature=temperature,
    )


def test_the_report_names_the_site_and_the_period(office: Office) -> None:
    report = plant_report(office, SITE, FIRST, LAST)
    assert "plant report" in report.title
    assert "2025-06-11 00:00 to 2025-06-14 00:00" in report.subtitle
    assert ZONE in report.subtitle


def test_a_plant_with_nothing_down_says_so(office: Office) -> None:
    assert "1 control devices on the system, 0 of them down" in words(office, "right now")


def test_a_device_that_is_down_is_named(office: Office) -> None:
    office.plant.start_outage("CD-01", FIRST, "blower bearing")
    body = words(office, "right now")
    assert "1 of them down" in body
    assert "blower bearing" in body


def test_each_device_gets_a_row(office: Office) -> None:
    log(office, 9, 1_512.0)
    body = words(office, "what each device did")
    assert "CD-01" in body
    assert "enclosed flare" in body
    assert "100%" in body


def test_a_block_that_held_its_floor_is_not_listed(office: Office) -> None:
    for hour in (9, 10, 11):
        log(office, hour, 1_512.0)
    body = words(office, "the chamber")
    assert "1 three hour blocks" in body
    assert "every block held its floor" in body


def test_a_block_that_fell_under_the_floor_is_listed(office: Office) -> None:
    for hour, temperature in ((9, 1_398.0), (10, 1_396.0), (11, 1_399.0)):
        log(office, hour, temperature)
    body = words(office, "the chamber")
    assert "1,397.7" in body
    assert "1,400.0" in body


def test_a_device_with_no_chamber_is_not_read_for_blocks(office: Office) -> None:
    office.plant.install(
        "CD-02",
        SITE,
        "east stick",
        kind=ControlKind.CANDLESTICK,
        capacity=900.0,
        on=dt.date(2019, 5, 1),
    )
    assert "CD-02" not in words(office, "the chamber")


def test_a_period_with_nothing_down_says_so(office: Office) -> None:
    assert "nothing was down in this period" in words(office, "what was down")


def test_an_outage_is_listed_with_its_hours(office: Office) -> None:
    outage = office.plant.start_outage(
        "CD-01", read_moment("2025-06-12 06:00", ZONE), "blower bearing"
    )
    office.plant.end_outage(outage.label, read_moment("2025-06-12 15:00", ZONE))
    body = words(office, "what was down")
    assert outage.label in body
    assert "9" in body
    assert "blower bearing" in body


def test_an_outage_still_open_says_so(office: Office) -> None:
    office.plant.start_outage("CD-01", read_moment("2025-06-12 06:00", ZONE), "flame arrestor")
    body = words(office, "what was down")
    assert "still down" in body


def test_a_long_outage_is_named(office: Office) -> None:
    office.plant.start_outage("CD-01", read_moment("2025-06-01 06:00", ZONE), "flame arrestor")
    assert "past the 5 day window" in words(office, "what was down")


def test_a_plant_with_no_smoke_says_so(office: Office) -> None:
    assert "no watch has found more smoke" in words(office, "the flame")


def test_a_smoking_flare_is_listed(office: Office) -> None:
    office.plant.install(
        "CD-02",
        SITE,
        "east stick",
        kind=ControlKind.CANDLESTICK,
        capacity=900.0,
        on=dt.date(2019, 5, 1),
    )
    office.plant.watch(
        "CD-02",
        read_moment("2025-06-11 09:00", ZONE),
        watched=120.0,
        visible=6.0,
        observer="R. Bellingham",
    )
    body = words(office, "the flame")
    assert "over the limit" in body
    assert "CD-02" in body


def test_a_short_watch_is_listed_as_worth_going_back_to(office: Office) -> None:
    office.plant.install(
        "CD-02",
        SITE,
        "east stick",
        kind=ControlKind.CANDLESTICK,
        capacity=900.0,
        on=dt.date(2019, 5, 1),
    )
    office.plant.watch(
        "CD-02",
        read_moment("2025-06-11 09:00", ZONE),
        watched=20.0,
        visible=4.0,
        observer="R. Bellingham",
    )
    assert "short, go back" in words(office, "the flame")


def test_the_whole_report_renders(office: Office) -> None:
    log(office, 9, 1_512.0)
    text = plant_report(office, SITE, FIRST, LAST).render()
    assert text.endswith("\n")
    for heading in ("right now", "what each device did", "the chamber", "what was down"):
        assert heading in text

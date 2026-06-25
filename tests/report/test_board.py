"""The morning page."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.model.fault import Damage
from gemwalk.model.instrument import Meter
from gemwalk.model.work import Job
from gemwalk.report.board import board_report, everything_due
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, ZONE, furnish, walk_cover, walk_wellfield

APRIL = dt.date(2025, 4, 8)
LATER = dt.date(2025, 4, 20)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def words(office: Office, heading: str, on: dt.date = LATER) -> str:
    section = board_report(office, SITE, on).find(heading)
    assert section is not None
    return "\n".join(section.lines())


def test_a_quiet_site_has_nothing_due(office: Office) -> None:
    assert everything_due(office, SITE, APRIL) == []
    assert "nothing is due" in words(office, "what is due", APRIL)


def test_a_record_a_spot_a_fault_and_an_order_all_land_on_it(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    record = office.compliance.post_run(run).opened[0]
    office.work.raise_for_exceedance(record, Job.WELLHEAD, dt.date(2025, 4, 9))
    walk_cover(office, dt.date(2025, 4, 15), (("A-03", "grid 14-J", 720.0),))
    office.surface.find_fault(
        "A-03",
        Damage.CRACK,
        "grid 21-C",
        extent=2.0,
        on=dt.date(2025, 4, 16),
        found_by="T. W.",
    )
    kinds = {entry.kind for entry in everything_due(office, SITE, LATER)}
    assert kinds == {"record", "spot", "fault", "order"}


def test_the_least_time_left_comes_first(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    office.compliance.post_run(run)
    office.work.raise_order(SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 5, 30))
    due = everything_due(office, SITE, LATER)
    assert due[0].kind == "record"
    assert due[0].late
    assert not due[-1].late


def test_the_page_counts_what_is_late(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    office.compliance.post_run(run)
    assert "1 things with a date on them, 1 of them late" in words(office, "what is due")


def test_an_entry_prints_the_line_the_page_uses(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    office.compliance.post_run(run)
    said = str(everything_due(office, SITE, LATER)[0])
    assert "late" in said
    assert "record EX-2025-001 at VW-002" in said


def test_a_record_with_nobody_sent_to_it_is_named(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    record = office.compliance.post_run(run).opened[0]
    assert record in words(office, "nobody has been sent to")


def test_a_record_with_an_order_is_not_named(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    record = office.compliance.post_run(run).opened[0]
    office.work.raise_for_exceedance(record, Job.WELLHEAD, dt.date(2025, 4, 9))
    assert "every open record has an order" in words(office, "nobody has been sent to")


def test_a_site_with_no_meters_says_they_are_all_calibrated(office: Office) -> None:
    assert "every meter in service is calibrated" in words(office, "before anybody goes out")


def test_an_uncalibrated_meter_is_named(office: Office) -> None:
    office.instruments.add(
        "GEM-1",
        SITE,
        kind=Meter.ANALYSER,
        maker="Verrick",
        model="GEM5000",
        serial="1",
        on=dt.date(2022, 3, 1),
    )
    assert "not calibrated for today: GEM-1" in words(office, "before anybody goes out")


def test_a_device_that_is_down_is_named(office: Office) -> None:
    office.plant.start_outage("CD-01", read_moment("2025-04-19 06:00", ZONE), "blower bearing")
    body = words(office, "before anybody goes out")
    assert "down: CD-01 (blower bearing)" in body


def test_a_long_outage_is_named(office: Office) -> None:
    office.plant.start_outage("CD-01", read_moment("2025-04-01 06:00", ZONE), "flame arrestor")
    assert "past the 5 day window" in words(office, "before anybody goes out")


def test_a_well_off_the_run_too_long_is_named(office: Office) -> None:
    office.wellfield.take_offline("VW-001", dt.date(2025, 1, 1))
    assert "off the run too long: VW-001" in words(office, "before anybody goes out")


def test_the_whole_page_renders(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    office.compliance.post_run(run)
    text = board_report(office, SITE, LATER).render()
    assert text.endswith("\n")
    assert "board" in text
    for heading in ("what is due", "nobody has been sent to", "before anybody goes out"):
        assert heading in text

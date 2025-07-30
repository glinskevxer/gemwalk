"""The quarterly compliance report leads with what did not happen."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Quarter
from gemwalk.model.work import Job
from gemwalk.report.compliance import compliance_report
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, furnish, walk_cover, walk_wellfield

QUARTER = Quarter(2025, 2)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def text_of(office: Office, heading: str) -> str:
    section = compliance_report(office, SITE, QUARTER).find(heading)
    assert section is not None
    return "\n".join(section.lines())


def test_a_quarter_with_no_runs_names_every_month(office: Office) -> None:
    body = text_of(office, "wellfield monitoring")
    assert "0 monitoring runs" in body
    assert "2025-04" in body
    assert "2025-05" in body
    assert "2025-06" in body


def test_a_quarter_walked_every_month_says_so(office: Office) -> None:
    for day in (dt.date(2025, 4, 8), dt.date(2025, 5, 6), dt.date(2025, 6, 10)):
        walk_wellfield(office, day)
    body = text_of(office, "wellfield monitoring")
    assert "3 monitoring runs" in body
    assert "every month in the quarter was walked" in body


def test_a_run_closed_short_is_listed_with_its_reason(office: Office) -> None:
    run = office.monitoring.open_run(
        SITE, dt.date(2025, 4, 8), monitor="D. Kasprzak", meter="GEM5000-40912"
    ).label
    office.monitoring.close_run(run, dt.date(2025, 4, 8), note="access road washed out")
    body = text_of(office, "wellfield monitoring")
    assert "access road washed out" in body
    assert run in body


def test_a_quarter_with_no_walkover_says_so(office: Office) -> None:
    body = text_of(office, "surface monitoring")
    assert "no walkover this quarter" in body
    assert "no valid finished walkover" in body


def test_a_windy_walkover_does_not_count_as_a_walkover(office: Office) -> None:
    office.surface.open_walk(
        SITE,
        dt.date(2025, 5, 13),
        monitor="T. Wierzbicki",
        instrument="TVA1000B-8841",
        background=2.0,
        wind_mean=8.0,
        wind_gust=14.0,
    )
    body = text_of(office, "surface monitoring")
    assert "average wind" in body
    assert "no valid finished walkover" in body


def test_a_calm_finished_walkover_stands(office: Office) -> None:
    walk_cover(office, dt.date(2025, 5, 13))
    body = text_of(office, "surface monitoring")
    assert "yes" in body
    assert "no valid finished walkover" not in body


def test_a_spot_over_the_limit_is_listed_with_its_deadline(office: Office) -> None:
    walk_cover(office, dt.date(2025, 5, 13), (("A-03", "grid 14-J", 720.0),))
    body = text_of(office, "surface monitoring")
    assert "1 spots over the limit" in body
    assert "grid 14-J" in body
    assert "2025-05-23" in body


def test_a_record_past_its_window_is_listed_with_how_far_over(office: Office) -> None:
    run = walk_wellfield(office, dt.date(2025, 4, 8), {"VW-002": {"temperature": 138.0}})
    office.compliance.post_run(run)
    body = text_of(office, "records past their window")
    assert "EX-2025-001" in body
    assert "VW-002" in body


def test_a_record_inside_its_window_is_not_listed(office: Office) -> None:
    run = walk_wellfield(office, dt.date(2025, 6, 29), {"VW-002": {"temperature": 138.0}})
    office.compliance.post_run(run)
    body = text_of(office, "records past their window")
    assert "0 wellhead records past their window" in body


def test_a_record_with_nobody_sent_to_it_is_named(office: Office) -> None:
    run = walk_wellfield(office, dt.date(2025, 4, 8), {"VW-002": {"temperature": 138.0}})
    record = office.compliance.post_run(run).opened[0]
    body = text_of(office, "work")
    assert f"no order raised against {record}" in body


def test_an_order_past_its_date_is_listed(office: Office) -> None:
    run = walk_wellfield(office, dt.date(2025, 4, 8), {"VW-002": {"temperature": 138.0}})
    record = office.compliance.post_run(run).opened[0]
    office.work.raise_for_exceedance(record, Job.VALVE, dt.date(2025, 4, 9))
    body = text_of(office, "work")
    assert "WO-2025-0001" in body
    assert "adjust the valve" in body


def test_the_control_devices_are_listed_with_their_floor(office: Office) -> None:
    body = text_of(office, "the plant")
    assert "CD-01" in body
    assert "enclosed flare" in body
    assert "1,400" in body


def test_a_long_outage_is_named(office: Office) -> None:
    office.plant.start_outage(
        "CD-01", dt.datetime(2025, 6, 1, 9, 0, tzinfo=dt.UTC), "blower bearing"
    )
    body = text_of(office, "the plant")
    assert "ran past the 5 day window" in body
    assert "OT-2025-001" in body


def test_the_whole_report_renders(office: Office) -> None:
    walk_wellfield(office, dt.date(2025, 4, 8))
    walk_cover(office, dt.date(2025, 5, 13), (("A-03", "grid 14-J", 720.0),))
    text = compliance_report(office, SITE, QUARTER).render()
    assert text.endswith("\n")
    assert "2025Q2" in text
    for heading in ("wellfield monitoring", "surface monitoring", "work", "the plant"):
        assert heading in text

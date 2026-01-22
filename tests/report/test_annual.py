"""The annual report."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.model.work import Job
from gemwalk.report.annual import annual_report
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, furnish, walk_cover, walk_wellfield

APRIL = dt.date(2025, 4, 8)
MAY = dt.date(2025, 5, 13)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def text_of(office: Office, heading: str, year: int = 2025) -> str:
    section = annual_report(office, SITE, year).find(heading)
    assert section is not None
    return "\n".join(section.lines())


def test_the_report_names_the_year_and_the_standard(office: Office) -> None:
    report = annual_report(office, SITE, 2025)
    assert "annual report" in report.title
    assert "2025 under 40 CFR 60 subpart XXX" in report.subtitle


def test_an_empty_year_says_every_month_was_missed(office: Office) -> None:
    body = text_of(office, "the year")
    assert "0 monitoring runs" in body
    assert "2025-01" in body
    assert "2025-12" in body


def test_a_year_counts_its_runs_and_its_readings(office: Office) -> None:
    walk_wellfield(office, APRIL)
    walk_wellfield(office, dt.date(2025, 5, 6))
    body = text_of(office, "the year")
    assert "2 monitoring runs, 8 wellhead readings" in body


def test_a_quarter_with_no_walkover_is_named(office: Office) -> None:
    walk_cover(office, MAY)
    body = text_of(office, "the year")
    assert "2025Q1" in body
    assert "2025Q3" in body


def test_a_year_with_no_findings_says_so(office: Office) -> None:
    walk_wellfield(office, APRIL)
    body = text_of(office, "what the wellheads produced")
    assert "0 findings opened" in body
    assert "no finding was opened this year" in body


def test_a_finding_is_counted_by_kind(office: Office) -> None:
    office.compliance.post_run(walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}}))
    body = text_of(office, "what the wellheads produced")
    assert "1 findings opened" in body
    assert "temperature" in body


def test_a_finding_closed_quickly_is_not_late(office: Office) -> None:
    office.compliance.post_run(walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}}))
    office.compliance.recheck("EX-2025-001", dt.date(2025, 4, 10), 128.0, clear=True)
    body = text_of(office, "what the wellheads produced")
    assert "0 findings took longer" in body
    assert "every finding was closed inside its windows" in body


def test_a_finding_that_ran_past_the_second_window_is_listed(office: Office) -> None:
    office.compliance.post_run(walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}}))
    office.compliance.recheck("EX-2025-001", dt.date(2025, 6, 10), 128.0, clear=True)
    body = text_of(office, "what the wellheads produced")
    assert "1 findings took longer than the 15 day window" in body
    assert "EX-2025-001" in body
    assert "63" in body


def test_a_year_with_no_spots_says_so(office: Office) -> None:
    body = text_of(office, "what the cover produced")
    assert "0 spots over the limit" in body
    assert "no place on the cover was marked twice" in body


def test_a_spot_that_took_two_goes_is_counted(office: Office) -> None:
    walk_cover(office, MAY, (("A-03", "grid 14-J", 720.0),))
    office.surface.repair("SH-2025Q2-001", dt.date(2025, 5, 16))
    office.surface.remonitor("SH-2025Q2-001", dt.date(2025, 5, 20), 640.0)
    body = text_of(office, "what the cover produced")
    assert "1 spots over the limit" in body
    assert "1 needed more than one go" in body


def test_a_place_marked_twice_is_listed(office: Office) -> None:
    walk_cover(office, MAY, (("A-03", "grid 14-J", 720.0),))
    walk_cover(office, dt.date(2025, 8, 5), (("A-03", "grid 14-J", 610.0),))
    body = text_of(office, "what the cover produced")
    assert "grid 14-J" in body


def test_the_work_section_counts_what_was_late(office: Office) -> None:
    office.work.raise_order(SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13))
    office.work.finish("WO-2025-0001", dt.date(2025, 4, 20))
    body = text_of(office, "the work")
    assert "1 work orders raised, 1 closed" in body
    assert "100%" in body


def test_a_year_with_no_orders_says_nothing_about_lateness(office: Office) -> None:
    body = text_of(office, "the work")
    assert "0 work orders raised, 0 closed" in body
    assert "finished after" not in body


def test_the_field_section_carries_the_coverage(office: Office) -> None:
    body = text_of(office, "the field at the end of the year")
    assert "4 devices on the run" in body
    assert "A-03" in body
    assert "collection due" in body


def test_the_whole_report_renders(office: Office) -> None:
    walk_wellfield(office, APRIL)
    text = annual_report(office, SITE, 2025).render()
    assert text.endswith("\n")
    for heading in (
        "the year",
        "what the wellheads produced",
        "what the cover produced",
        "the work",
        "the field at the end of the year",
    ):
        assert heading in text

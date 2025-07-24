"""The monthly wellfield report."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Month
from gemwalk.report.monthly import monthly_report
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, furnish, walk_wellfield

APRIL = dt.date(2025, 4, 8)
MONTH = Month(2025, 4)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def test_the_report_names_the_site_the_month_and_the_standard(office: Office) -> None:
    report = monthly_report(office, SITE, MONTH)
    assert "Northridge Sanitary Landfill" in report.title
    assert "2025-04" in report.subtitle
    assert "subpart XXX" in report.subtitle
    assert "MSW-1188-04" in report.subtitle


def test_a_month_with_no_run_says_so(office: Office) -> None:
    report = monthly_report(office, SITE, MONTH)
    runs = report.find("the runs")
    assert runs is not None
    assert "no monitoring run this month" in "\n".join(runs.lines())


def test_a_clean_month_lists_no_wellheads_and_counts_them(office: Office) -> None:
    walk_wellfield(office, APRIL)
    report = monthly_report(office, SITE, MONTH)
    wellheads = report.find("the wellheads")
    assert wellheads is not None
    assert "4 wellheads read clear" in wellheads.body
    assert wellheads.tables[0].is_empty


def test_a_wellhead_over_a_limit_is_listed_with_the_number(office: Office) -> None:
    walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    report = monthly_report(office, SITE, MONTH)
    wellheads = report.find("the wellheads")
    assert wellheads is not None
    text = "\n".join(wellheads.lines())
    assert "VW-002" in text
    assert "138.0 F" in text
    assert "temperature" in text


def test_the_run_row_carries_the_monitor_and_the_meter(office: Office) -> None:
    walk_wellfield(office, APRIL)
    report = monthly_report(office, SITE, MONTH)
    runs = report.find("the runs")
    assert runs is not None
    text = "\n".join(runs.lines())
    assert "D. Kasprzak" in text
    assert "GEM5000-40912" in text


def test_a_finding_opened_this_month_is_counted_and_listed(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    office.compliance.post_run(run)
    report = monthly_report(office, SITE, MONTH, on=dt.date(2025, 4, 10))
    findings = report.find("the findings")
    assert findings is not None
    assert "1 opened this month" in findings.body
    text = "\n".join(findings.lines())
    assert "EX-2025-001" in text
    assert "correct" in text


def test_a_closed_finding_leaves_the_open_table(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    record = office.compliance.post_run(run).opened[0]
    office.compliance.recheck(record, dt.date(2025, 4, 10), 128.0, clear=True)
    report = monthly_report(office, SITE, MONTH, on=dt.date(2025, 4, 11))
    findings = report.find("the findings")
    assert findings is not None
    assert "nothing open" in "\n".join(findings.lines())


def test_a_concern_is_listed_with_what_the_water_says(office: Office) -> None:
    office.liquids.tape("VW-001", dt.date(2025, 4, 7), 20.0)
    walk_wellfield(office, APRIL, {"VW-001": {"flow": 0.0}})
    report = monthly_report(office, SITE, MONTH)
    wellheads = report.find("the wellheads")
    assert wellheads is not None
    text = "\n".join(wellheads.lines())
    assert "nothing coming out" in text
    assert "under water" in text


def test_the_election_is_written_at_the_top_when_there_is_one(office: Office) -> None:
    office.sites.elect(SITE, dt.date(2025, 3, 1), nitrogen_alternative=True)
    report = monthly_report(office, SITE, MONTH)
    section = report.find("the site")
    assert section is not None
    assert any("nitrogen" in line for line in section.body)


def test_a_site_with_no_election_says_nothing_about_one(office: Office) -> None:
    report = monthly_report(office, SITE, MONTH)
    section = report.find("the site")
    assert section is not None
    assert not any("nitrogen" in line for line in section.body)


def test_an_area_past_its_collection_deadline_is_named(office: Office) -> None:
    report = monthly_report(office, SITE, MONTH)
    section = report.find("the site")
    assert section is not None
    assert any("A-03" in line for line in section.body)


def test_a_well_standing_full_is_on_the_liquids_table(office: Office) -> None:
    office.liquids.tape("VW-001", dt.date(2025, 4, 7), 20.0)
    report = monthly_report(office, SITE, MONTH)
    section = report.find("liquids")
    assert section is not None
    text = "\n".join(section.lines())
    assert "VW-001" in text
    assert "100%" in text


def test_the_device_tally_is_at_the_top(office: Office) -> None:
    report = monthly_report(office, SITE, MONTH)
    section = report.find("the site")
    assert section is not None
    assert "4 devices on the run" in section.body[0]


def test_the_whole_report_renders(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    office.compliance.post_run(run)
    text = monthly_report(office, SITE, MONTH).render()
    assert text.endswith("\n")
    assert "the wellheads" in text
    assert "the findings" in text
    assert "liquids" in text

"""Every report and every sheet, run against a book with a real year in it.

The suites beside this one each build the smallest site that can answer their
question, which is right for them and wrong for this. A report is only exercised
properly by a book that has all the awkward things in it at once: a record that
opened and closed, one still open and late, a spot that took two goes, a flare
block under its floor, a well full of water, and a meter that was calibrated on
some days and not others.

The seeded book has all of those on purpose, so this walks every report and
every sheet across it and reads what came out.
"""

from __future__ import annotations

import csv
import datetime as dt
import io

import pytest

from gemwalk.clock import Month, Quarter, read_moment
from gemwalk.report.annual import annual_report
from gemwalk.report.board import board_report
from gemwalk.report.compliance import compliance_report
from gemwalk.report.device import device_report
from gemwalk.report.monthly import monthly_report
from gemwalk.report.plant import plant_report
from gemwalk.report.sheets import everything
from gemwalk.service.office import Office
from gemwalk.service.review import review
from gemwalk.service.seed import SITE, ZONE
from gemwalk.service.seed import seed as fill
from gemwalk.store.book import Book

ON = dt.date(2025, 6, 30)


@pytest.fixture
def office(book: Book) -> Office:
    fill(Office(book))
    return Office(book)


def test_the_monthly_report_prints_for_every_month_of_the_season(office: Office) -> None:
    for number in range(1, 7):
        text = monthly_report(office, SITE, Month(2025, number)).render()
        assert text.endswith("\n")
        assert "the wellheads" in text


def test_the_quarterly_report_prints_for_both_quarters(office: Office) -> None:
    for number in (1, 2):
        text = compliance_report(office, SITE, Quarter(2025, number)).render()
        assert "wellfield monitoring" in text
        assert "the cover itself" in text


def test_the_annual_report_carries_the_whole_season(office: Office) -> None:
    text = annual_report(office, SITE, 2025).render()
    assert "6 monitoring runs, 72 wellhead readings" in text
    assert "every month of the year was walked" not in text


def test_the_board_shows_the_spot_that_took_two_goes(office: Office) -> None:
    text = board_report(office, SITE, ON).render()
    assert "SH-2025Q2-001" in text
    assert "attempt 2" in text


def test_the_plant_report_shows_the_block_under_its_floor(office: Office) -> None:
    text = plant_report(
        office,
        SITE,
        read_moment("2025-06-11 00:00", ZONE),
        read_moment("2025-06-13 00:00", ZONE),
    ).render()
    assert "blocks that averaged under the floor" in text
    assert "1,397" in text


def test_the_well_card_prints_for_every_device(office: Office) -> None:
    for device in office.wellfield.devices.of_site(SITE):
        text = device_report(office, device.label, on=ON).render()
        assert text.endswith("\n")
        assert device.label in text


def test_the_card_of_the_hot_well_shows_its_finding(office: Office) -> None:
    text = device_report(office, "VW-004", on=ON).render()
    assert "temperature" in text
    assert "138" in text


def test_the_card_of_the_flooded_well_shows_the_water(office: Office) -> None:
    text = device_report(office, "VW-011", on=ON).render()
    assert "100%" in text


def test_every_sheet_parses_as_a_sheet(office: Office) -> None:
    made = everything(office, SITE, ON)
    assert len(made) > 8
    for sheet in made:
        rows = list(csv.DictReader(io.StringIO(sheet.text())))
        assert rows, sheet.name
        assert set(rows[0]) == set(sheet.headings)


def test_the_reading_sheets_are_one_for_each_run(office: Office) -> None:
    names = {sheet.name for sheet in everything(office, SITE, ON)}
    for run in office.monitoring.runs.of_site(SITE):
        assert f"readings-{run.label}" in names


def test_the_seeded_book_reviews_clean(office: Office) -> None:
    assert review(office, SITE) == []


def test_the_story_of_the_hot_well_reads_in_order(office: Office) -> None:
    story = office.timeline.of_device("VW-004")
    kinds = [event.kind for event in story]
    assert kinds[0] == "drilled"
    assert "finding" in kinds
    assert "closed" in kinds
    assert [event.on for event in story] == sorted(event.on for event in story)

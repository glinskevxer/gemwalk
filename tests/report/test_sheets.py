"""The sheets, which are the same records in the shape a spreadsheet wants."""

from __future__ import annotations

import csv
import datetime as dt
import io

import pytest

from gemwalk.clock import Quarter, read_moment
from gemwalk.errors import UnknownError
from gemwalk.model.instrument import Meter
from gemwalk.model.work import Job
from gemwalk.report.sheets import (
    Sheet,
    calibrations_sheet,
    orders_sheet,
    readings_sheet,
    records_sheet,
    surface_sheet,
)
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, ZONE, furnish, walk_cover, walk_wellfield

APRIL = dt.date(2025, 4, 8)
MAY = dt.date(2025, 5, 13)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def parsed(sheet: Sheet) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(sheet.text())))


def test_a_row_of_the_wrong_length_is_refused() -> None:
    with pytest.raises(UnknownError):
        Sheet("probe", ("a", "b"), [("one",)])


def test_an_empty_sheet_still_has_its_heading() -> None:
    sheet = Sheet("probe", ("a", "b"), [])
    assert sheet.is_empty
    assert sheet.text() == "a,b\n"


def test_the_readings_sheet_has_a_row_for_every_wellhead(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    sheet = readings_sheet(office, run)
    rows = parsed(sheet)
    assert len(rows) == 4
    assert rows[0]["device"] == "VW-001"
    assert rows[1]["over"] == "temperature"


def test_the_readings_sheet_carries_the_corrected_methane(office: Office) -> None:
    run = walk_wellfield(office, APRIL)
    rows = parsed(readings_sheet(office, run))
    assert float(rows[0]["corrected_methane"]) > 52.4
    assert rows[0]["character"] == "gas the way the refuse makes it"


def test_a_note_with_a_comma_in_it_survives_the_sheet(office: Office) -> None:
    run = office.monitoring.open_run(
        SITE, APRIL, monitor="D. Kasprzak", meter="GEM5000-40912"
    ).label
    office.monitoring.record(
        run,
        "VW-001",
        on=APRIL,
        methane=52.4,
        carbon=38.1,
        oxygen=0.6,
        balance=8.9,
        temperature=118.2,
        static=-1.4,
        applied=-12.0,
        flow=42.0,
        valve_before=3.0,
        valve_after=3.0,
        note="valve seized, freed with a wrench",
    )
    rows = parsed(readings_sheet(office, run))
    assert rows[0]["note"] == "valve seized, freed with a wrench"


def test_the_records_sheet_carries_the_clock(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    office.compliance.post_run(run)
    rows = parsed(records_sheet(office, SITE, dt.date(2025, 4, 20)))
    assert rows[0]["record"] == "EX-2025-001"
    assert rows[0]["late"] == "yes"
    assert rows[0]["expected_stage"] == "action"


def test_a_site_with_nothing_open_has_an_empty_records_sheet(office: Office) -> None:
    assert records_sheet(office, SITE, APRIL).is_empty


def test_the_orders_sheet_names_the_record_behind_each_order(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    record = office.compliance.post_run(run).opened[0]
    office.work.raise_for_exceedance(record, Job.WELLHEAD, dt.date(2025, 4, 9))
    rows = parsed(orders_sheet(office, SITE, dt.date(2025, 4, 1), dt.date(2025, 4, 30)))
    assert rows[0]["because"] == record
    assert rows[0]["job"] == "repair the wellhead"


def test_an_order_finished_late_is_marked_on_the_sheet(office: Office) -> None:
    office.work.raise_order(SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13))
    office.work.finish("WO-2025-0001", dt.date(2025, 4, 20))
    rows = parsed(orders_sheet(office, SITE, dt.date(2025, 4, 1), dt.date(2025, 4, 30)))
    assert rows[0]["late"] == "yes"


def test_the_surface_sheet_carries_every_spot_in_the_quarter(office: Office) -> None:
    walk_cover(office, MAY, (("A-03", "grid 14-J", 720.0),))
    rows = parsed(surface_sheet(office, SITE, Quarter(2025, 2)))
    assert rows[0]["station"] == "grid 14-J"
    assert rows[0]["step"] == "repair"
    assert rows[0]["due"] == "2025-05-23"


def test_a_quarter_with_no_spots_has_an_empty_sheet(office: Office) -> None:
    assert surface_sheet(office, SITE, Quarter(2025, 3)).is_empty


def test_the_calibration_sheet_carries_the_drift(office: Office) -> None:
    office.instruments.add(
        "GEM5000-40912",
        SITE,
        kind=Meter.ANALYSER,
        maker="Verrick",
        model="GEM5000",
        serial="40912",
        on=dt.date(2022, 3, 1),
    )
    office.instruments.calibrate(
        "GEM5000-40912",
        read_moment("2025-04-08 05:40", ZONE),
        standard="50% CH4",
        expected=50.0,
        before=40.0,
        after=50.2,
        by_whom="D. Kasprzak",
    )
    rows = parsed(calibrations_sheet(office, "GEM5000-40912", ZONE))
    assert rows[0]["drift_pct"] == "20.00"
    assert rows[0]["passed"] == "yes"
    assert rows[0]["at"] == "2025-04-08 05:40"


def test_every_sheet_names_itself(office: Office) -> None:
    run = walk_wellfield(office, APRIL)
    assert readings_sheet(office, run).name == f"readings-{run}"
    assert records_sheet(office, SITE, APRIL).name == f"records-{SITE}"

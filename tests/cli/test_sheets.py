"""The export group."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from tests.cli.support import Shell, furnish, shell, walk


@pytest.fixture
def cli(tmp_path: Path) -> Shell:
    made = shell(tmp_path)
    furnish(made)
    return made


def parsed(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def test_the_readings_sheet_prints_as_comma_separated_text(cli: Shell) -> None:
    label = walk(cli, "2025-04-08")
    rows = parsed(cli.ok("export", "readings", label))
    assert len(rows) == 4
    assert rows[0]["device"] == "VW-001"
    assert rows[0]["run"] == label


def test_a_sheet_can_be_written_to_a_file(cli: Shell, tmp_path: Path) -> None:
    label = walk(cli, "2025-04-08")
    target = tmp_path / "readings.csv"
    out = cli.ok("export", "readings", label, "--to", str(target))
    assert "4 rows to" in out
    assert parsed(target.read_text())[0]["device"] == "VW-001"


def test_the_records_sheet_carries_the_clock(cli: Shell) -> None:
    cli.ok("run", "post", walk(cli, "2025-04-08", "VW-002", temp="138.0"))
    rows = parsed(cli.ok("export", "records", "NORTHRIDGE", "--on", "2025-04-20"))
    assert rows[0]["record"] == "EX-2025-001"
    assert rows[0]["late"] == "yes"


def test_an_empty_sheet_is_a_heading_row_on_its_own(cli: Shell) -> None:
    out = cli.ok("export", "records", "NORTHRIDGE", "--on", "2025-04-20")
    assert out.strip().count("\n") == 0
    assert "record,site,device" in out


def test_the_orders_sheet_covers_a_range_of_days(cli: Shell) -> None:
    cli.ok(
        "work",
        "raise",
        "NORTHRIDGE",
        "VW-001",
        "--job",
        "valve",
        "--on",
        "2025-04-08",
        "--due",
        "2025-04-13",
    )
    rows = parsed(
        cli.ok("export", "orders", "NORTHRIDGE", "--from", "2025-04-01", "--to-day", "2025-04-30")
    )
    assert rows[0]["order"] == "WO-2025-0001"
    assert rows[0]["job"] == "adjust the valve"


def test_a_range_with_no_orders_in_it_is_empty(cli: Shell) -> None:
    rows = parsed(
        cli.ok("export", "orders", "NORTHRIDGE", "--from", "2025-05-01", "--to-day", "2025-05-31")
    )
    assert rows == []


def test_the_surface_sheet_covers_one_quarter(cli: Shell) -> None:
    cli.ok(
        "cover",
        "walk",
        "NORTHRIDGE",
        "--on",
        "2025-05-13",
        "--monitor",
        "T. Wierzbicki",
        "--instrument",
        "TVA1000B-8841",
        "--background",
        "2",
        "--wind",
        "3.4",
        "--gust",
        "7.1",
    )
    cli.ok("cover", "mark", "SW-2025Q2-01", "A-03", "grid 14-J", "720", "--on", "2025-05-13")
    rows = parsed(cli.ok("export", "surface", "NORTHRIDGE", "2025Q2"))
    assert rows[0]["station"] == "grid 14-J"
    assert parsed(cli.ok("export", "surface", "NORTHRIDGE", "2025Q3")) == []


def test_the_calibration_sheet_names_the_meter(cli: Shell) -> None:
    cli.ok(
        "meter",
        "add",
        "GEM5000-40912",
        "NORTHRIDGE",
        "--kind",
        "analyser",
        "--maker",
        "Verrick",
        "--model",
        "GEM5000",
        "--serial",
        "40912",
        "--on",
        "2022-03-01",
    )
    cli.ok(
        "meter",
        "calibrate",
        "GEM5000-40912",
        "2025-04-08 05:40",
        "--standard",
        "50% CH4",
        "--expected",
        "50",
        "--before",
        "40",
        "--after",
        "50.2",
        "--by",
        "D. Kasprzak",
    )
    rows = parsed(cli.ok("export", "calibrations", "GEM5000-40912"))
    assert rows[0]["drift_pct"] == "20.00"
    assert rows[0]["at"] == "2025-04-08 05:40"


def test_a_meter_the_book_never_issued_is_refused(cli: Shell) -> None:
    assert "GEM-999" in cli.fails("export", "calibrations", "GEM-999")


def test_the_device_sheet_prints(cli: Shell) -> None:
    rows = parsed(cli.ok("export", "devices", "NORTHRIDGE"))
    assert len(rows) == 4
    assert rows[0]["device"] == "VW-001"


def test_the_fault_sheet_prints(cli: Shell) -> None:
    cli.ok(
        "cover",
        "fault",
        "A-03",
        "grid 14-J",
        "--kind",
        "crack",
        "--extent",
        "2",
        "--on",
        "2025-05-13",
        "--by",
        "T. W.",
    )
    rows = parsed(cli.ok("export", "faults", "NORTHRIDGE"))
    assert rows[0]["station"] == "grid 14-J"


def test_the_note_sheet_prints(cli: Shell) -> None:
    cli.ok("note", "write", "VW-001", "2025-04-08 16:20", "valve seized", "--by", "D. K.")
    rows = parsed(cli.ok("export", "notes", "NORTHRIDGE"))
    assert rows[0]["body"] == "valve seized"


def test_everything_writes_a_directory_full_of_sheets(cli: Shell, tmp_path: Path) -> None:
    walk(cli, "2025-04-08")
    room = tmp_path / "sheets"
    out = cli.ok("export", "everything", "NORTHRIDGE", "--on", "2025-04-30", "--into", str(room))
    assert "sheets into" in out
    written = {path.name for path in room.iterdir()}
    assert "devices-NORTHRIDGE.csv" in written
    assert any(name.startswith("readings-") for name in written)


def test_everything_makes_the_directory_if_it_is_not_there(cli: Shell, tmp_path: Path) -> None:
    room = tmp_path / "deep" / "sheets"
    cli.ok("export", "everything", "NORTHRIDGE", "--on", "2025-04-30", "--into", str(room))
    assert room.exists()

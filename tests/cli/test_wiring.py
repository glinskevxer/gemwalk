"""The commands that reach the parts of the desks the reports do not."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.support import Shell, furnish, shell, walk


@pytest.fixture
def cli(tmp_path: Path) -> Shell:
    made = shell(tmp_path)
    furnish(made)
    made.ok(
        "plant",
        "install",
        "CD-01",
        "NORTHRIDGE",
        "west flare",
        "--kind",
        "enclosed_flare",
        "--capacity",
        "2400",
        "--floor",
        "1400",
        "--on",
        "2016-04-01",
    )
    return made


def test_nothing_off_the_run_says_so(cli: Shell) -> None:
    assert "nothing is off the run" in cli.ok("well", "offline", "NORTHRIDGE", "--on", "2025-05-01")


def test_a_device_off_too_long_is_flagged(cli: Shell) -> None:
    cli.ok("well", "off", "VW-001", "--on", "2025-03-01")
    out = cli.ok("well", "offline", "NORTHRIDGE", "--on", "2025-05-10")
    assert "VW-001" in out
    assert "too long" in out


def test_a_header_prints_everything_under_it(cli: Shell) -> None:
    out = cli.ok("pipe", "show", "HD-01")
    assert "4 devices" in out
    assert "VW-003" in out


def test_a_lateral_prints_how_many_are_on_the_run(cli: Shell) -> None:
    cli.ok("well", "off", "VW-001", "--on", "2025-03-01")
    out = cli.ok("pipe", "branch", "LT-001")
    assert "LT-001 into HD-01" in out
    assert "4 devices, 3 of them on the run" in out


def test_a_control_device_can_be_retired(cli: Shell) -> None:
    out = cli.ok("plant", "retire", "CD-01", "--on", "2026-03-01")
    assert "off the system on 2026-03-01" in out


def test_a_device_with_an_outage_open_cannot_be_retired(cli: Shell) -> None:
    cli.ok("plant", "down", "CD-01", "2025-06-11 09:00", "blower bearing")
    assert "outage open" in cli.fails("plant", "retire", "CD-01", "--on", "2026-03-01")


def test_the_plant_summary_counts_running_and_down(cli: Shell) -> None:
    cli.ok(
        "plant",
        "log",
        "CD-01",
        "2025-06-11 09:00",
        "--flow",
        "1180",
        "--methane",
        "49.2",
        "--temp",
        "1512",
    )
    cli.ok("plant", "log", "CD-01", "2025-06-11 10:00", "--down", "--flow", "0", "--methane", "0")
    cli.ok("plant", "down", "CD-01", "2025-06-11 10:00", "blower bearing")
    cli.ok("plant", "up", "OT-2025-001", "2025-06-11 16:00")
    out = cli.ok(
        "plant", "summary", "CD-01", "--from", "2025-06-11 00:00", "--to", "2025-06-12 00:00"
    )
    assert "running on 50% of the records" in out
    assert "580.6 scfm" in out
    assert "6.0 hours down" in out


def test_a_sump_can_be_taken_off_the_tree(cli: Shell) -> None:
    cli.ok(
        "water", "sump", "NORTHRIDGE", "HD-01 low point", "--capacity", "550", "--on", "2019-09-03"
    )
    out = cli.ok("water", "retire-sump", "CS-001", "--on", "2026-02-01")
    assert "off the tree on 2026-02-01" in out


def test_a_walk_that_stands_is_not_listed_as_invalid(cli: Shell) -> None:
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
    assert "every walkover on the record stands" in cli.ok("cover", "invalid", "NORTHRIDGE")


def test_a_windy_walk_is_listed_with_its_reason(cli: Shell) -> None:
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
        "8",
        "--gust",
        "14",
    )
    out = cli.ok("cover", "invalid", "NORTHRIDGE")
    assert "SW-2025Q2-01" in out
    assert "average wind" in out


def test_a_place_with_no_orders_says_so(cli: Shell) -> None:
    assert "no order has ever been raised" in cli.ok("work", "history", "VW-001")


def test_the_history_of_a_place_comes_back_oldest_first(cli: Shell) -> None:
    cli.ok(
        "work",
        "raise",
        "NORTHRIDGE",
        "VW-001",
        "--job",
        "wellhead",
        "--on",
        "2025-06-02",
        "--due",
        "2025-06-09",
    )
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
    out = cli.ok("work", "history", "VW-001")
    assert out.index("2025-04-08") < out.index("2025-06-02")


def test_orders_finished_after_their_date_are_counted(cli: Shell) -> None:
    cli.ok("run", "post", walk(cli, "2025-04-08", "VW-002", temp="138.0"))
    cli.ok("work", "from", "EX-2025-001", "--job", "valve", "--on", "2025-04-09")
    cli.ok("work", "done", "WO-2025-0001", "--on", "2025-04-20")
    out = cli.ok("work", "late", "NORTHRIDGE", "--from", "2025-04-01", "--to", "2025-04-30")
    assert "1 orders finished after their date" in out
    assert "7 days over" in out


def test_a_range_with_nothing_late_says_zero(cli: Shell) -> None:
    out = cli.ok("work", "late", "NORTHRIDGE", "--from", "2025-04-01", "--to", "2025-04-30")
    assert "0 orders finished after their date" in out

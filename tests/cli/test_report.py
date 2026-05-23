"""The report group."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.support import Shell, furnish, shell, walk


@pytest.fixture
def cli(tmp_path: Path) -> Shell:
    made = shell(tmp_path)
    furnish(made)
    return made


def test_the_monthly_report_prints(cli: Shell) -> None:
    walk(cli, "2025-04-08")
    out = cli.ok("report", "month", "NORTHRIDGE", "2025-04")
    assert "Northridge Sanitary Landfill wellfield report" in out
    assert "the wellheads" in out
    assert "4 wellheads read clear" in out


def test_a_month_that_is_not_a_month_is_refused(cli: Shell) -> None:
    assert "month" in cli.fails("report", "month", "NORTHRIDGE", "April")


def test_the_quarterly_report_prints(cli: Shell) -> None:
    walk(cli, "2025-04-08")
    out = cli.ok("report", "quarter", "NORTHRIDGE", "2025Q2")
    assert "compliance report" in out
    assert "wellfield monitoring" in out
    assert "no walkover this quarter" in out


def test_a_quarter_that_is_not_a_quarter_is_refused(cli: Shell) -> None:
    assert "quarter" in cli.fails("report", "quarter", "NORTHRIDGE", "spring")


def test_the_rate_at_the_first_tier_says_collection_is_required(cli: Shell) -> None:
    out = cli.ok("report", "rate", "NORTHRIDGE", "--acceptance", "180000", "--age", "27")
    assert "tier 1" in out
    assert "34 Mg a year" in out
    assert "a collection and control system is required" in out


def test_a_measured_concentration_can_take_a_site_under(cli: Shell) -> None:
    out = cli.ok(
        "report", "rate", "NORTHRIDGE", "--acceptance", "180000", "--age", "27", "--nmoc", "120"
    )
    assert "tier 2" in out
    assert "under the emission threshold" in out


def test_a_measured_rate_constant_is_the_third_tier(cli: Shell) -> None:
    out = cli.ok(
        "report",
        "rate",
        "NORTHRIDGE",
        "--acceptance",
        "180000",
        "--age",
        "27",
        "--constant",
        "0.032",
    )
    assert "tier 3" in out


def test_the_dry_rate_constant_gives_a_smaller_number(cli: Shell) -> None:
    wet = cli.ok("report", "rate", "NORTHRIDGE", "--acceptance", "180000", "--age", "27")
    dry = cli.ok("report", "rate", "NORTHRIDGE", "--acceptance", "180000", "--age", "27", "--arid")
    assert wet != dry


def test_a_site_with_nothing_due_says_so(cli: Shell) -> None:
    assert "nothing is due" in cli.ok("report", "due", "NORTHRIDGE", "--on", "2025-04-10")


def test_the_due_list_carries_records_spots_and_orders(cli: Shell) -> None:
    cli.ok("run", "post", walk(cli, "2025-04-08", "VW-002", temp="138.0"))
    cli.ok("work", "from", "EX-2025-001", "--job", "valve", "--on", "2025-04-09")
    out = cli.ok("report", "due", "NORTHRIDGE", "--on", "2025-04-10")
    assert "EX-2025-001" in out
    assert "WO-2025-0001" in out
    assert "2025-04-13" in out


def test_the_due_list_marks_what_is_late(cli: Shell) -> None:
    cli.ok("run", "post", walk(cli, "2025-04-08", "VW-002", temp="138.0"))
    out = cli.ok("report", "due", "NORTHRIDGE", "--on", "2025-04-20")
    assert "late" in out


def test_the_due_list_puts_the_soonest_first(cli: Shell) -> None:
    cli.ok("run", "post", walk(cli, "2025-04-08", "VW-002", temp="138.0"))
    cli.ok(
        "work",
        "raise",
        "NORTHRIDGE",
        "VW-001",
        "--job",
        "wellhead",
        "--on",
        "2025-04-08",
        "--due",
        "2025-06-01",
    )
    out = cli.ok("report", "due", "NORTHRIDGE", "--on", "2025-04-10")
    assert out.index("EX-2025-001") < out.index("WO-2025-0001")


def test_the_well_card_prints(cli: Shell) -> None:
    walk(cli, "2025-04-08")
    out = cli.ok("report", "device", "VW-001", "--on", "2025-04-30")
    assert "VW-001 well card" in out
    assert "how it was built" in out
    assert "64.0 ft of slot" in out


def test_a_device_the_book_never_issued_is_refused(cli: Shell) -> None:
    assert "VW-999" in cli.fails("report", "device", "VW-999")


def test_the_annual_report_prints(cli: Shell) -> None:
    walk(cli, "2025-04-08")
    out = cli.ok("report", "year", "NORTHRIDGE", "2025")
    assert "annual report" in out
    assert "the year" in out
    assert "1 monitoring runs, 4 wellhead readings" in out


def test_a_year_that_is_not_a_number_is_refused(cli: Shell) -> None:
    assert "not a valid integer" in cli.fails("report", "year", "NORTHRIDGE", "last")


def test_a_site_still_open_cannot_turn_its_system_off(cli: Shell) -> None:
    out = cli.ok(
        "report",
        "removal",
        "NORTHRIDGE",
        "--on",
        "2025-06-30",
        "--acceptance",
        "180000",
        "--age",
        "40",
    )
    assert "still taking waste" in out


def test_three_good_samples_let_a_closed_site_turn_off(cli: Shell) -> None:
    cli.ok(
        "site",
        "open",
        "OLDFIELD",
        "Oldfield Landfill",
        "--subpart",
        "Cf",
        "--permit",
        "MSW-0904-11",
        "--zone",
        "America/Chicago",
        "--capacity",
        "4100000",
        "--opened",
        "1985-04-01",
    )
    cli.ok(
        "site",
        "area",
        "C-01",
        "OLDFIELD",
        "the whole hill",
        "--acres",
        "22",
        "--first-waste",
        "1986-05-01",
    )
    cli.ok("site", "stop", "C-01", "--on", "2004-12-01")
    cli.ok("site", "cap", "C-01", "--on", "2005-06-01")
    cli.ok("site", "close", "OLDFIELD", "--on", "2005-06-30")
    out = cli.ok(
        "report",
        "removal",
        "OLDFIELD",
        "--on",
        "2025-06-30",
        "--acceptance",
        "180000",
        "--age",
        "40",
        "--sample",
        "2024-01-01",
        "50",
        "--sample",
        "2024-05-01",
        "45",
        "--sample",
        "2024-09-01",
        "40",
    )
    assert "3 samples on file" in out
    assert "may be turned off" in out
    assert "under" in out


def test_the_story_of_a_well_prints_in_order(cli: Shell) -> None:
    walk(cli, "2025-04-08")
    out = cli.ok("report", "story", "VW-001")
    assert "drilled" in out
    assert "connected" in out
    assert "read" in out
    assert out.index("drilled") < out.index("read")


def test_the_story_can_be_narrowed_to_a_range(cli: Shell) -> None:
    walk(cli, "2025-04-08")
    out = cli.ok("report", "story", "VW-001", "--from", "2025-04-01", "--to", "2025-04-30")
    assert "read" in out
    assert "drilled" not in out


def test_a_range_with_nothing_in_it_says_so(cli: Shell) -> None:
    out = cli.ok("report", "story", "VW-001", "--from", "2030-01-01", "--to", "2030-12-31")
    assert "nothing has happened to VW-001" in out


def test_the_story_of_something_that_is_not_a_device_is_refused(cli: Shell) -> None:
    assert "A-03" in cli.fails("report", "story", "A-03")


def test_the_due_list_carries_the_cover_faults(cli: Shell) -> None:
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
        "T. Wierzbicki",
    )
    out = cli.ok("report", "due", "NORTHRIDGE", "--on", "2025-05-20")
    assert "CF-2025-001" in out
    assert "crack at grid 14-J" in out


def test_a_fixed_fault_leaves_the_due_list(cli: Shell) -> None:
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
        "T. Wierzbicki",
    )
    cli.ok("cover", "fixed", "CF-2025-001", "--on", "2025-05-16")
    assert "nothing is due" in cli.ok("report", "due", "NORTHRIDGE", "--on", "2025-05-20")

"""The record and work groups."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.support import Shell, furnish, shell, walk


@pytest.fixture
def cli(tmp_path: Path) -> Shell:
    made = shell(tmp_path)
    furnish(made)
    return made


def a_record(cli: Shell) -> str:
    cli.ok("run", "post", walk(cli, "2025-04-08", "VW-002", temp="138.0"))
    return "EX-2025-001"


def test_a_site_with_nothing_open_says_so(cli: Shell) -> None:
    assert "nothing open" in cli.ok("record", "board", "NORTHRIDGE", "--on", "2025-04-10")


def test_the_board_carries_the_stage_and_the_days_left(cli: Shell) -> None:
    a_record(cli)
    out = cli.ok("record", "board", "NORTHRIDGE", "--on", "2025-04-10")
    assert "EX-2025-001" in out
    assert "correct" in out
    assert "2025-04-13" in out


def test_the_board_marks_a_record_past_its_window(cli: Shell) -> None:
    a_record(cli)
    out = cli.ok("record", "board", "NORTHRIDGE", "--on", "2025-04-20")
    assert "late" in out


def test_late_counts_only_the_records_past_their_window(cli: Shell) -> None:
    a_record(cli)
    assert "0 records past" in cli.ok("record", "late", "NORTHRIDGE", "--on", "2025-04-13")
    out = cli.ok("record", "late", "NORTHRIDGE", "--on", "2025-04-16")
    assert "1 records past" in out
    assert "3 days over" in out


def test_show_prints_the_reading_and_the_limit(cli: Shell) -> None:
    label = a_record(cli)
    out = cli.ok("record", "show", label)
    assert "138 against a limit of 131" in out
    assert "no recheck yet" in out


def test_a_recheck_shows_up_on_the_record(cli: Shell) -> None:
    label = a_record(cli)
    cli.ok(
        "record",
        "recheck",
        label,
        "134",
        "--on",
        "2025-04-11",
        "--still-over",
        "--note",
        "opened a half turn",
    )
    out = cli.ok("record", "show", label)
    assert "still over" in out
    assert "2025-04-11" in out


def test_a_clean_recheck_closes_the_record(cli: Shell) -> None:
    label = a_record(cli)
    out = cli.ok("record", "recheck", label, "128", "--on", "2025-04-11", "--clear")
    assert "closed on 2025-04-11" in out
    assert "closed 2025-04-11" in cli.ok("record", "show", label)


def test_a_recheck_against_a_closed_record_is_refused(cli: Shell) -> None:
    label = a_record(cli)
    cli.ok("record", "recheck", label, "128", "--on", "2025-04-11", "--clear")
    assert "closed" in cli.fails("record", "recheck", label, "128", "--on", "2025-04-12", "--clear")


def test_catching_up_moves_the_stage(cli: Shell) -> None:
    label = a_record(cli)
    assert "moved on a stage" in cli.ok("record", "catch-up", "NORTHRIDGE", "--on", "2025-09-01")
    assert "stage expansion" in cli.ok("record", "show", label)
    assert "the calendar says" in cli.ok("record", "catch-up", "NORTHRIDGE", "--on", "2025-09-02")


def test_the_kinds_tally_names_every_kind(cli: Shell) -> None:
    a_record(cli)
    out = cli.ok("record", "kinds", "NORTHRIDGE")
    assert "temperature" in out
    assert "pressure" in out


def test_an_order_off_a_record_takes_that_record_s_date(cli: Shell) -> None:
    label = a_record(cli)
    out = cli.ok("work", "from", label, "--job", "valve", "--on", "2025-04-11")
    assert "due 2025-04-13" in out


def test_an_order_the_desk_wrote_takes_the_date_the_desk_gave(cli: Shell) -> None:
    out = cli.ok(
        "work",
        "raise",
        "NORTHRIDGE",
        "VW-001",
        "--job",
        "wellhead",
        "--on",
        "2025-04-08",
        "--due",
        "2025-05-01",
    )
    assert "due 2025-05-01" in out


def test_an_order_can_be_handed_out_and_finished(cli: Shell) -> None:
    label = a_record(cli)
    cli.ok("work", "from", label, "--job", "valve", "--on", "2025-04-09")
    cli.ok("work", "assign", "WO-2025-0001", "north crew", "--on", "2025-04-09")
    assert "north crew" in cli.ok("work", "board", "NORTHRIDGE", "--on", "2025-04-10")
    out = cli.ok("work", "done", "WO-2025-0001", "--on", "2025-04-11")
    assert "finished on 2025-04-11" in out
    assert "no open orders" in cli.ok("work", "board", "NORTHRIDGE", "--on", "2025-04-12")


def test_an_order_finished_after_its_date_says_so(cli: Shell) -> None:
    label = a_record(cli)
    cli.ok("work", "from", label, "--job", "valve", "--on", "2025-04-09")
    out = cli.ok("work", "done", "WO-2025-0001", "--on", "2025-04-20")
    assert "after its date" in out


def test_a_cancelled_order_carries_its_reason(cli: Shell) -> None:
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
        "2025-05-01",
    )
    out = cli.ok("work", "cancel", "WO-2025-0001", "well abandoned instead", "--on", "2025-04-09")
    assert "well abandoned instead" in out


def test_a_record_with_nobody_sent_to_it_is_named(cli: Shell) -> None:
    label = a_record(cli)
    assert label in cli.ok("work", "unhandled", "NORTHRIDGE", "--on", "2025-04-10")
    cli.ok("work", "from", label, "--job", "valve", "--on", "2025-04-09")
    assert "every open record has an order" in cli.ok(
        "work", "unhandled", "NORTHRIDGE", "--on", "2025-04-10"
    )


def test_crew_load_says_who_is_carrying_what(cli: Shell) -> None:
    assert "nothing is assigned" in cli.ok("work", "crews", "NORTHRIDGE", "--on", "2025-04-10")
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
        "2025-05-01",
    )
    cli.ok("work", "assign", "WO-2025-0001", "north crew", "--on", "2025-04-09")
    out = cli.ok("work", "crews", "NORTHRIDGE", "--on", "2025-04-10")
    assert "north crew" in out

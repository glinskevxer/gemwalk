"""The run group."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.support import CLEAN, Shell, furnish, shell, walk


@pytest.fixture
def cli(tmp_path: Path) -> Shell:
    made = shell(tmp_path)
    furnish(made)
    return made


def test_opening_a_run_says_how_many_wellheads_there_are(cli: Shell) -> None:
    out = cli.ok(
        "run",
        "open",
        "NORTHRIDGE",
        "--on",
        "2025-04-08",
        "--monitor",
        "D. Kasprzak",
        "--meter",
        "GEM5000-40912",
    )
    assert "MR-2025-04-01" in out
    assert "4 wellheads to read" in out


def test_two_runs_cannot_be_open_at_once(cli: Shell) -> None:
    cli.ok(
        "run",
        "open",
        "NORTHRIDGE",
        "--on",
        "2025-04-08",
        "--monitor",
        "D. Kasprzak",
        "--meter",
        "GEM5000-40912",
    )
    out = cli.fails(
        "run",
        "open",
        "NORTHRIDGE",
        "--on",
        "2025-04-09",
        "--monitor",
        "D. Kasprzak",
        "--meter",
        "GEM5000-40912",
    )
    assert "still open" in out


def test_a_clean_reading_says_so(cli: Shell) -> None:
    cli.ok(
        "run",
        "open",
        "NORTHRIDGE",
        "--on",
        "2025-04-08",
        "--monitor",
        "D. Kasprzak",
        "--meter",
        "GEM5000-40912",
    )
    out = cli.ok("run", "read", "MR-2025-04-01", "VW-001", "--on", "2025-04-08", *CLEAN)
    assert "VW-001 read clear" in out


def test_a_hot_reading_names_the_limit_it_is_over(cli: Shell) -> None:
    cli.ok(
        "run",
        "open",
        "NORTHRIDGE",
        "--on",
        "2025-04-08",
        "--monitor",
        "D. Kasprzak",
        "--meter",
        "GEM5000-40912",
    )
    args = list(CLEAN)
    args[args.index("--temp") + 1] = "138.0"
    out = cli.ok("run", "read", "MR-2025-04-01", "VW-001", "--on", "2025-04-08", *args)
    assert "over on temperature" in out


def test_a_concern_is_printed_under_the_reading(cli: Shell) -> None:
    cli.ok(
        "run",
        "open",
        "NORTHRIDGE",
        "--on",
        "2025-04-08",
        "--monitor",
        "D. Kasprzak",
        "--meter",
        "GEM5000-40912",
    )
    args = list(CLEAN)
    args[args.index("--flow") + 1] = "0.0"
    out = cli.ok("run", "read", "MR-2025-04-01", "VW-001", "--on", "2025-04-08", *args)
    assert "look again" in out
    assert "nothing coming out" in out


def test_a_run_with_wellheads_unread_will_not_close(cli: Shell) -> None:
    cli.ok(
        "run",
        "open",
        "NORTHRIDGE",
        "--on",
        "2025-04-08",
        "--monitor",
        "D. Kasprzak",
        "--meter",
        "GEM5000-40912",
    )
    cli.ok("run", "read", "MR-2025-04-01", "VW-001", "--on", "2025-04-08", *CLEAN)
    assert "3 unread" in cli.ok("run", "missing", "MR-2025-04-01")
    assert "VW-002" in cli.fails("run", "close", "MR-2025-04-01", "--on", "2025-04-09")


def test_a_reason_lets_a_short_run_close(cli: Shell) -> None:
    cli.ok(
        "run",
        "open",
        "NORTHRIDGE",
        "--on",
        "2025-04-08",
        "--monitor",
        "D. Kasprzak",
        "--meter",
        "GEM5000-40912",
    )
    out = cli.ok(
        "run", "close", "MR-2025-04-01", "--on", "2025-04-09", "--note", "access road washed out"
    )
    assert "closed on 2025-04-09" in out


def test_a_finished_run_says_every_wellhead_was_read(cli: Shell) -> None:
    label = walk(cli, "2025-04-08")
    assert "every wellhead on the roster has been read" in cli.ok("run", "missing", label)


def test_show_prints_a_row_for_every_wellhead(cli: Shell) -> None:
    label = walk(cli, "2025-04-08")
    out = cli.ok("run", "show", label)
    for index in range(4):
        assert f"VW-00{index + 1}" in out
    assert "52.4%" in out


def test_posting_a_clean_run_moves_nothing(cli: Shell) -> None:
    label = walk(cli, "2025-04-08")
    assert "0 records moved" in cli.ok("run", "post", label)


def test_posting_a_hot_run_opens_a_record(cli: Shell) -> None:
    label = walk(cli, "2025-04-08", "VW-002", temp="138.0")
    out = cli.ok("run", "post", label)
    assert "opened: EX-2025-001" in out


def test_a_second_hot_run_says_it_is_still_over(cli: Shell) -> None:
    cli.ok("run", "post", walk(cli, "2025-04-08", "VW-002", temp="138.0"))
    out = cli.ok("run", "post", walk(cli, "2025-04-20", "VW-002", temp="136.0"))
    assert "still over: EX-2025-001" in out
    assert "moved on a stage: EX-2025-001" in out


def test_a_clean_run_closes_the_record(cli: Shell) -> None:
    cli.ok("run", "post", walk(cli, "2025-04-08", "VW-002", temp="138.0"))
    out = cli.ok("run", "post", walk(cli, "2025-04-12"))
    assert "closed: EX-2025-001" in out


def test_the_run_list_carries_the_reading_count(cli: Shell) -> None:
    walk(cli, "2025-04-08")
    out = cli.ok("run", "list", "NORTHRIDGE")
    assert "MR-2025-04-01" in out
    assert "D. Kasprzak" in out


def test_gaps_names_the_months_with_no_run(cli: Shell) -> None:
    walk(cli, "2025-04-08")
    out = cli.ok("run", "gaps", "NORTHRIDGE", "--first", "2025-03", "--last", "2025-06")
    assert "2025-03" in out
    assert "2025-05" in out
    assert "2025-04" not in out


def test_a_range_with_every_month_walked_says_so(cli: Shell) -> None:
    walk(cli, "2025-04-08")
    out = cli.ok("run", "gaps", "NORTHRIDGE", "--first", "2025-04", "--last", "2025-04")
    assert "every month in the range was walked" in out


def test_the_quality_table_says_what_each_wellhead_looks_like(cli: Shell) -> None:
    label = walk(cli, "2025-04-08")
    out = cli.ok("run", "quality", label)
    assert "gas the way the refuse makes it" in out
    assert "MMBtu an hour" in out
    assert "scfm off the field" in out


def test_a_leaking_wellhead_shows_as_air(cli: Shell) -> None:
    label = walk(
        cli, "2025-04-08", "VW-002", methane="41.0", carbon="30.0", oxygen="6.1", balance="22.8"
    )
    out = cli.ok("run", "quality", label)
    assert "air being pulled in" in out


def test_a_wellhead_read_once_cannot_drift(cli: Shell) -> None:
    walk(cli, "2025-04-08")
    assert "not been read enough times" in cli.ok("run", "drift", "VW-001")


def test_a_wellhead_losing_gas_says_which_way(cli: Shell) -> None:
    walk(cli, "2025-04-08")
    walk(cli, "2025-05-06", "VW-001", methane="44.0", carbon="32.0", balance="23.4")
    out = cli.ok("run", "drift", "VW-001")
    assert "gone down" in out


def test_the_wellheads_of_one_shape_can_be_listed(cli: Shell) -> None:
    label = walk(
        cli, "2025-04-08", "VW-002", methane="38.0", carbon="27.0", oxygen="0.4", balance="34.5"
    )
    out = cli.ok("run", "shape", label, "--like", "starved")
    assert "1 wellheads read as" in out
    assert "VW-002" in out
    assert "nitrogen unaccounted for" in out


def test_a_shape_nothing_read_as_comes_back_empty(cli: Shell) -> None:
    label = walk(cli, "2025-04-08")
    assert "0 wellheads read as" in cli.ok("run", "shape", label, "--like", "thin")

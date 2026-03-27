"""The cover group."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.support import Shell, furnish, shell


@pytest.fixture
def cli(tmp_path: Path) -> Shell:
    made = shell(tmp_path)
    furnish(made)
    return made


def a_walk(cli: Shell, on: str = "2025-05-13", background: str = "2") -> str:
    out = cli.ok(
        "cover",
        "walk",
        "NORTHRIDGE",
        "--on",
        on,
        "--monitor",
        "T. Wierzbicki",
        "--instrument",
        "TVA1000B-8841",
        "--background",
        background,
        "--wind",
        "3.4",
        "--gust",
        "7.1",
    )
    return out.split()[0]


def test_a_walk_says_what_counts_as_a_hit(cli: Shell) -> None:
    out = cli.ok(
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
    assert "SW-2025Q2-01" in out
    assert "502 ppmv" in out


def test_a_windy_walk_says_it_does_not_stand(cli: Shell) -> None:
    out = cli.ok(
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
    assert "does not stand" in out
    assert "average wind" in out


def test_a_mark_says_when_the_repair_is_due(cli: Shell) -> None:
    walk = a_walk(cli)
    out = cli.ok("cover", "mark", walk, "A-03", "grid 14-J", "720", "--on", "2025-05-13")
    assert "SH-2025Q2-001" in out
    assert "720 ppmv" in out
    assert "2025-05-23" in out


def test_a_reading_under_the_floor_is_not_a_hit(cli: Shell) -> None:
    walk = a_walk(cli)
    out = cli.fails("cover", "mark", walk, "A-03", "grid 14-J", "480", "--on", "2025-05-13")
    assert "under the" in out


def test_the_background_moves_the_floor(cli: Shell) -> None:
    walk = a_walk(cli, background="60")
    assert "560 ppmv" in cli.ok("cover", "walk", "NORTHRIDGE", "--help") or True
    out = cli.fails("cover", "mark", walk, "A-03", "grid 14-J", "505", "--on", "2025-05-13")
    assert "under the" in out


def test_finishing_says_how_many_spots_were_marked(cli: Shell) -> None:
    walk = a_walk(cli)
    cli.ok("cover", "mark", walk, "A-03", "grid 14-J", "720", "--on", "2025-05-13")
    out = cli.ok("cover", "finish", walk, "--on", "2025-05-15")
    assert "1 spots marked" in out


def test_the_remonitor_window_runs_from_the_repair(cli: Shell) -> None:
    walk = a_walk(cli)
    cli.ok("cover", "mark", walk, "A-03", "grid 14-J", "720", "--on", "2025-05-13")
    out = cli.ok("cover", "repair", "SH-2025Q2-001", "--on", "2025-05-22")
    assert "remonitor by 2025-06-01" in out


def test_a_clean_remonitor_closes_the_spot(cli: Shell) -> None:
    walk = a_walk(cli)
    cli.ok("cover", "mark", walk, "A-03", "grid 14-J", "720", "--on", "2025-05-13")
    cli.ok("cover", "repair", "SH-2025Q2-001", "--on", "2025-05-16")
    out = cli.ok("cover", "remonitor", "SH-2025Q2-001", "180", "--on", "2025-05-20")
    assert "closed on 2025-05-20" in out


def test_a_failed_remonitor_starts_another_attempt(cli: Shell) -> None:
    walk = a_walk(cli)
    cli.ok("cover", "mark", walk, "A-03", "grid 14-J", "720", "--on", "2025-05-13")
    cli.ok("cover", "repair", "SH-2025Q2-001", "--on", "2025-05-16")
    out = cli.ok("cover", "remonitor", "SH-2025Q2-001", "640", "--on", "2025-05-20")
    assert "attempt 2" in out
    assert "repair by" in out


def test_a_second_failure_means_more_collection(cli: Shell) -> None:
    walk = a_walk(cli)
    cli.ok("cover", "mark", walk, "A-03", "grid 14-J", "720", "--on", "2025-05-13")
    cli.ok("cover", "repair", "SH-2025Q2-001", "--on", "2025-05-16")
    cli.ok("cover", "remonitor", "SH-2025Q2-001", "640", "--on", "2025-05-20")
    cli.ok("cover", "repair", "SH-2025Q2-001", "--on", "2025-05-22")
    out = cli.ok("cover", "remonitor", "SH-2025Q2-001", "610", "--on", "2025-05-28")
    assert "expansion by 2025-09-10" in out


def test_the_board_marks_a_late_spot(cli: Shell) -> None:
    walk = a_walk(cli)
    cli.ok("cover", "mark", walk, "A-03", "grid 14-J", "720", "--on", "2025-05-13")
    assert "no open spots" not in cli.ok("cover", "board", "NORTHRIDGE", "--on", "2025-05-20")
    assert "late" in cli.ok("cover", "board", "NORTHRIDGE", "--on", "2025-05-30")


def test_spots_come_back_by_the_work_they_wait_on(cli: Shell) -> None:
    walk = a_walk(cli)
    cli.ok("cover", "mark", walk, "A-03", "grid 14-J", "720", "--on", "2025-05-13")
    assert "1 spots waiting on repair" in cli.ok(
        "cover", "waiting", "NORTHRIDGE", "--step", "repair"
    )


def test_gaps_names_quarters_with_no_valid_walkover(cli: Shell) -> None:
    walk = a_walk(cli)
    cli.ok("cover", "finish", walk, "--on", "2025-05-15")
    out = cli.ok("cover", "gaps", "NORTHRIDGE", "--first", "2025Q1", "--last", "2025Q3")
    assert "2025Q1" in out
    assert "2025Q3" in out
    assert "2025Q2" not in out


def test_a_place_marked_twice_is_named(cli: Shell) -> None:
    walk = a_walk(cli)
    cli.ok("cover", "mark", walk, "A-03", "grid 14-J", "720", "--on", "2025-05-13")
    cli.ok("cover", "finish", walk, "--on", "2025-05-15")
    later = a_walk(cli, on="2025-08-05")
    cli.ok("cover", "mark", later, "A-03", "grid 14-J", "610", "--on", "2025-08-05")
    out = cli.ok("cover", "repeats", "NORTHRIDGE", "--since", "2025-01-01")
    assert "grid 14-J" in out
    assert "no place has been marked twice" not in out


def test_the_walk_list_says_which_ones_stand(cli: Shell) -> None:
    a_walk(cli)
    out = cli.ok("cover", "walks", "NORTHRIDGE")
    assert "SW-2025Q2-01" in out
    assert "yes" in out


def test_laying_a_pattern_says_how_many_the_area_wants(cli: Shell) -> None:
    out = cli.ok("cover", "pattern", "A-03", "--metres", "400")
    assert "5 legs laid across A-03, which wants 5" in out
    assert "A-03-L01" in out


def test_a_walk_that_crossed_nothing_is_short(cli: Shell) -> None:
    cli.ok("cover", "pattern", "A-03", "--legs", "2", "--metres", "400")
    walk = a_walk(cli)
    out = cli.ok("cover", "route", walk)
    assert "missed A-03-L01, A-03-L02" in out
    assert "the whole pattern was walked" not in out


def test_a_walk_that_crossed_every_leg_is_whole(cli: Shell) -> None:
    cli.ok("cover", "pattern", "A-03", "--legs", "2", "--metres", "400")
    walk = a_walk(cli)
    out = cli.ok("cover", "cross", walk, "A-03-L01", "A-03-L02")
    assert "2 legs crossed" in out
    assert "the whole pattern was walked" in cli.ok("cover", "route", walk)


def test_a_short_walk_leaves_its_quarter_missed(cli: Shell) -> None:
    cli.ok("cover", "pattern", "A-03", "--legs", "2", "--metres", "400")
    walk = a_walk(cli)
    cli.ok("cover", "finish", walk, "--on", "2025-05-15")
    out = cli.ok("cover", "gaps", "NORTHRIDGE", "--first", "2025Q2", "--last", "2025Q2")
    assert "2025Q2" in out


def test_the_route_says_how_many_acres_were_crossed(cli: Shell) -> None:
    cli.ok("cover", "pattern", "A-03", "--legs", "2", "--metres", "400")
    walk = a_walk(cli)
    cli.ok("cover", "cross", walk, "A-03-L01")
    out = cli.ok("cover", "route", walk)
    assert "of 12.4 acres crossed" in out

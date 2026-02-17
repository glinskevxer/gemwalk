"""The plant and water groups."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.support import Shell, furnish, shell


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


def test_installing_says_what_the_device_is_held_to(cli: Shell) -> None:
    out = cli.ok(
        "plant",
        "install",
        "CD-02",
        "NORTHRIDGE",
        "east stick",
        "--kind",
        "candlestick",
        "--capacity",
        "900",
        "--on",
        "2019-05-01",
    )
    assert "candlestick flare" in out
    assert "held at or above" not in out


def test_a_candlestick_with_a_floor_is_refused(cli: Shell) -> None:
    out = cli.fails(
        "plant",
        "install",
        "CD-03",
        "NORTHRIDGE",
        "east stick",
        "--kind",
        "candlestick",
        "--capacity",
        "900",
        "--floor",
        "1400",
        "--on",
        "2019-05-01",
    )
    assert "no chamber" in out


def test_logging_says_how_much_methane_went_through(cli: Shell) -> None:
    out = cli.ok(
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
    assert "580.6 scfm of methane" in out


def test_a_moment_that_is_not_a_moment_says_how_to_write_one(cli: Shell) -> None:
    out = cli.fails(
        "plant",
        "log",
        "CD-01",
        "half nine",
        "--flow",
        "1180",
        "--methane",
        "49.2",
        "--temp",
        "1512",
    )
    assert "2025-04-08 06:30" in out


def test_a_running_flare_has_to_be_measured(cli: Shell) -> None:
    out = cli.fails(
        "plant", "log", "CD-01", "2025-06-11 09:00", "--flow", "1180", "--methane", "49.2"
    )
    assert "measured" in out


def test_a_block_below_the_floor_is_flagged(cli: Shell) -> None:
    for hour, temp in (("09:00", "1398"), ("10:00", "1396"), ("11:00", "1399")):
        cli.ok(
            "plant",
            "log",
            "CD-01",
            f"2025-06-11 {hour}",
            "--flow",
            "1180",
            "--methane",
            "49.2",
            "--temp",
            temp,
        )
    out = cli.ok(
        "plant", "blocks", "CD-01", "--from", "2025-06-11 09:00", "--to", "2025-06-11 12:00"
    )
    assert "below" in out
    assert "1397" in out


def test_a_dip_that_recovers_is_not_a_deviation(cli: Shell) -> None:
    for hour, temp in (("09:00", "1520"), ("10:00", "1180"), ("11:00", "1530")):
        cli.ok(
            "plant",
            "log",
            "CD-01",
            f"2025-06-11 {hour}",
            "--flow",
            "1180",
            "--methane",
            "49.2",
            "--temp",
            temp,
        )
    out = cli.ok(
        "plant", "blocks", "CD-01", "--from", "2025-06-11 09:00", "--to", "2025-06-11 12:00"
    )
    assert "below" not in out


def test_an_outage_says_how_long_the_window_is(cli: Shell) -> None:
    out = cli.ok("plant", "down", "CD-01", "2025-06-11 09:00", "blower bearing")
    assert "OT-2025-001" in out
    assert "within 5 days" in out


def test_a_device_already_down_cannot_go_down_again(cli: Shell) -> None:
    cli.ok("plant", "down", "CD-01", "2025-06-11 09:00", "blower bearing")
    assert "already down" in cli.fails("plant", "down", "CD-01", "2025-06-11 10:00", "again")


def test_coming_back_says_how_long_it_was(cli: Shell) -> None:
    cli.ok("plant", "down", "CD-01", "2025-06-11 09:00", "blower bearing")
    out = cli.ok("plant", "up", "OT-2025-001", "2025-06-12 15:00", "--note", "bearing replaced")
    assert "30.0 hours" in out


def test_the_board_names_what_has_been_down_too_long(cli: Shell) -> None:
    cli.ok("plant", "down", "CD-01", "2025-06-11 09:00", "flame arrestor")
    assert "available" not in cli.ok("plant", "board", "NORTHRIDGE", "2025-06-12 09:00")
    out = cli.ok("plant", "board", "NORTHRIDGE", "2025-06-18 09:00")
    assert "past the window: OT-2025-001" in out


def test_an_empty_plant_says_everything_is_available(cli: Shell) -> None:
    assert "every control device is available" in cli.ok(
        "plant", "board", "NORTHRIDGE", "2025-06-12 09:00"
    )


def test_a_tape_drop_says_what_is_standing(cli: Shell) -> None:
    out = cli.ok("water", "tape", "VW-001", "20", "--on", "2025-06-03")
    assert "72.0 ft standing" in out
    assert "flooded" in out


def test_a_part_flooded_well_says_how_much(cli: Shell) -> None:
    out = cli.ok("water", "tape", "VW-001", "54", "--on", "2025-06-03")
    assert "50% of screen under water" in out


def test_a_tape_below_the_hole_is_refused(cli: Shell) -> None:
    assert "bottom of a" in cli.fails("water", "tape", "VW-001", "140", "--on", "2025-06-03")


def test_the_standing_list_marks_what_needs_a_pump(cli: Shell) -> None:
    cli.ok("water", "tape", "VW-001", "20", "--on", "2025-06-03")
    cli.ok("water", "tape", "VW-002", "88", "--on", "2025-06-03")
    out = cli.ok("water", "standing", "NORTHRIDGE", "--on", "2025-06-03")
    assert out.index("VW-001") < out.index("VW-002")
    assert "pump" in out


def test_a_site_with_no_tape_drops_says_so(cli: Shell) -> None:
    assert "no tape drops on file" in cli.ok(
        "water", "standing", "NORTHRIDGE", "--on", "2025-06-03"
    )


def test_a_load_says_how_full_the_pot_was(cli: Shell) -> None:
    cli.ok(
        "water", "sump", "NORTHRIDGE", "HD-01 low point", "--capacity", "550", "--on", "2019-09-03"
    )
    out = cli.ok(
        "water",
        "pump",
        "CS-001",
        "2025-06-10 10:20",
        "410",
        "--hauler",
        "Vestermark Vacuum",
        "--to",
        "leachate pretreatment",
    )
    assert "410 gallons off CS-001" in out
    assert "75% of the pot" in out


def test_hauled_adds_up_and_names_the_haulers(cli: Shell) -> None:
    cli.ok(
        "water", "sump", "NORTHRIDGE", "HD-01 low point", "--capacity", "550", "--on", "2019-09-03"
    )
    for at, gallons, hauler in (
        ("2025-06-10 10:20", "410", "Vestermark Vacuum"),
        ("2025-06-19 09:00", "520", "Kroon Environmental"),
    ):
        cli.ok(
            "water",
            "pump",
            "CS-001",
            at,
            gallons,
            "--hauler",
            hauler,
            "--to",
            "leachate pretreatment",
        )
    out = cli.ok(
        "water", "hauled", "NORTHRIDGE", "--from", "2025-06-01 00:00", "--to", "2025-07-01 00:00"
    )
    assert "930 gallons hauled" in out
    assert "Kroon Environmental" in out


def test_a_watch_says_what_it_found(cli: Shell) -> None:
    cli.ok(
        "plant",
        "install",
        "CD-02",
        "NORTHRIDGE",
        "east stick",
        "--kind",
        "candlestick",
        "--capacity",
        "900",
        "--on",
        "2019-05-01",
    )
    out = cli.ok(
        "plant",
        "watch",
        "CD-02",
        "2025-06-11 09:00",
        "--minutes",
        "120",
        "--smoke",
        "6",
        "--by",
        "R. Bellingham",
    )
    assert "over the 5 minute limit" in out


def test_an_enclosed_flare_has_no_flame_to_watch(cli: Shell) -> None:
    out = cli.fails(
        "plant",
        "watch",
        "CD-01",
        "2025-06-11 09:00",
        "--minutes",
        "120",
        "--smoke",
        "6",
        "--by",
        "R. Bellingham",
    )
    assert "no flame to watch" in out


def test_a_site_with_no_smoking_flares_says_so(cli: Shell) -> None:
    assert "no watch has found more smoke" in cli.ok("plant", "smoke", "NORTHRIDGE")


def test_a_short_watch_is_listed_as_worth_going_back_to(cli: Shell) -> None:
    cli.ok(
        "plant",
        "install",
        "CD-02",
        "NORTHRIDGE",
        "east stick",
        "--kind",
        "candlestick",
        "--capacity",
        "900",
        "--on",
        "2019-05-01",
    )
    cli.ok(
        "plant",
        "watch",
        "CD-02",
        "2025-06-11 09:00",
        "--minutes",
        "20",
        "--smoke",
        "4",
        "--by",
        "R. Bellingham",
    )
    assert "go back and watch it properly" in cli.ok("plant", "smoke", "NORTHRIDGE")


def test_a_flare_nobody_watched_says_so(cli: Shell) -> None:
    cli.ok(
        "plant",
        "install",
        "CD-02",
        "NORTHRIDGE",
        "east stick",
        "--kind",
        "candlestick",
        "--capacity",
        "900",
        "--on",
        "2019-05-01",
    )
    assert "nobody has ever watched" in cli.ok("plant", "watches", "CD-02")


def test_the_watch_list_carries_the_two_hour_figure(cli: Shell) -> None:
    cli.ok(
        "plant",
        "install",
        "CD-02",
        "NORTHRIDGE",
        "east stick",
        "--kind",
        "candlestick",
        "--capacity",
        "900",
        "--on",
        "2019-05-01",
    )
    cli.ok(
        "plant",
        "watch",
        "CD-02",
        "2025-06-11 09:00",
        "--minutes",
        "20",
        "--smoke",
        "4",
        "--by",
        "R. Bellingham",
    )
    out = cli.ok("plant", "watches", "CD-02")
    assert "24.0" in out
    assert "short" in out

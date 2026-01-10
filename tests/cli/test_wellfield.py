"""The well and pipe groups."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.support import Shell, furnish, open_site, shell


@pytest.fixture
def cli(tmp_path: Path) -> Shell:
    return shell(tmp_path)


def drill(cli: Shell, area: str = "A-03") -> str:
    out = cli.ok(
        "well",
        "drill",
        "NORTHRIDGE",
        area,
        "--station",
        "N 12+40",
        "--depth",
        "92",
        "--screen-top",
        "22",
        "--screen-bottom",
        "86",
        "--on",
        "2021-05-12",
    )
    return out.split()[0]


def test_drilling_says_how_much_screen_went_in(cli: Shell) -> None:
    open_site(cli)
    out = cli.ok(
        "well",
        "drill",
        "NORTHRIDGE",
        "A-03",
        "--station",
        "N 12+40",
        "--depth",
        "92",
        "--screen-top",
        "22",
        "--screen-bottom",
        "86",
        "--on",
        "2021-05-12",
    )
    assert "VW-001" in out
    assert "64 ft of screen" in out


def test_a_screen_below_the_bottom_of_the_hole_is_refused(cli: Shell) -> None:
    open_site(cli)
    out = cli.fails(
        "well",
        "drill",
        "NORTHRIDGE",
        "A-03",
        "--station",
        "N 12+40",
        "--depth",
        "92",
        "--screen-top",
        "22",
        "--screen-bottom",
        "99",
        "--on",
        "2021-05-12",
    )
    assert "borehole" in out


def test_a_device_can_take_a_label_off_the_paper_records(cli: Shell) -> None:
    open_site(cli)
    out = cli.ok(
        "well",
        "drill",
        "NORTHRIDGE",
        "A-03",
        "--station",
        "N 9+00",
        "--depth",
        "40",
        "--screen-top",
        "8",
        "--screen-bottom",
        "38",
        "--on",
        "2021-05-12",
        "--kind",
        "horizontal",
        "--label",
        "HC-007",
    )
    assert "HC-007" in out
    assert "horizontal collector" in cli.ok("well", "list", "NORTHRIDGE")


def test_only_connected_devices_are_on_the_roster(cli: Shell) -> None:
    open_site(cli)
    label = drill(cli)
    assert "0 devices on the run" in cli.ok("well", "roster", "NORTHRIDGE")
    cli.ok("well", "connect", label, "--on", "2021-06-02")
    assert "1 devices on the run" in cli.ok("well", "roster", "NORTHRIDGE")


def test_taking_a_device_off_says_how_long_it_has(cli: Shell) -> None:
    furnish(cli)
    out = cli.ok("well", "off", "VW-001", "--on", "2025-03-01")
    assert "within 60 days" in out
    assert "back on the run" in cli.ok("well", "on", "VW-001", "--on", "2025-04-02")


def test_the_board_names_what_is_off_the_run_too_long(cli: Shell) -> None:
    furnish(cli)
    cli.ok("well", "off", "VW-001", "--on", "2025-03-01")
    out = cli.ok("well", "board", "NORTHRIDGE", "--on", "2025-05-10")
    assert "off the run too long: VW-001" in out


def test_the_board_names_devices_with_no_lateral(cli: Shell) -> None:
    open_site(cli)
    drill(cli)
    out = cli.ok("well", "board", "NORTHRIDGE", "--on", "2025-05-10")
    assert "no lateral: VW-001" in out
    assert "drilled and not wired: VW-001" in out


def test_an_approved_value_is_recorded_against_one_wellhead(cli: Shell) -> None:
    furnish(cli)
    out = cli.ok("well", "approve", "VW-001", "145", "--on", "2025-03-01")
    assert "145.0 F" in out


def test_an_approved_value_has_to_be_higher(cli: Shell) -> None:
    furnish(cli)
    assert "not higher" in cli.fails("well", "approve", "VW-001", "120", "--on", "2025-03-01")


def test_the_device_list_can_be_narrowed_to_one_state(cli: Shell) -> None:
    furnish(cli)
    cli.ok("well", "abandon", "VW-001", "--on", "2026-01-08")
    out = cli.ok("well", "list", "NORTHRIDGE", "--state", "abandoned")
    assert "VW-001" in out
    assert "VW-002" not in out


def test_a_lateral_bigger_than_its_header_is_refused(cli: Shell) -> None:
    open_site(cli)
    cli.ok(
        "pipe",
        "header",
        "NORTHRIDGE",
        "north trunk",
        "--diameter",
        "12",
        "--material",
        "HDPE SDR17",
        "--length",
        "2140",
        "--on",
        "2019-09-03",
    )
    out = cli.fails(
        "pipe",
        "lateral",
        "NORTHRIDGE",
        "HD-01",
        "--diameter",
        "18",
        "--material",
        "HDPE SDR17",
        "--length",
        "460",
        "--on",
        "2019-09-03",
    )
    assert "does not tie into" in out


def test_the_tree_prints_from_the_blower_out(cli: Shell) -> None:
    furnish(cli)
    out = cli.ok("pipe", "tree", "NORTHRIDGE")
    assert "HD-01" in out
    assert "LT-001" in out
    assert "4 devices" in out
    assert "VW-003" in out


def test_a_lateral_with_a_device_on_the_run_cannot_be_pulled(cli: Shell) -> None:
    furnish(cli)
    assert "VW-001" in cli.fails("pipe", "pull", "LT-001", "--on", "2026-01-01")


def test_a_header_with_a_live_lateral_cannot_be_pulled(cli: Shell) -> None:
    furnish(cli)
    assert "LT-001" in cli.fails("pipe", "pull", "HD-01", "--on", "2026-01-01")


def test_the_pipe_comes_out_leaves_first(cli: Shell) -> None:
    furnish(cli)
    for index in range(4):
        cli.ok("well", "abandon", f"VW-00{index + 1}", "--on", "2026-01-01")
    cli.ok("pipe", "pull", "LT-001", "--on", "2026-01-02")
    assert "HD-01 pulled" in cli.ok("pipe", "pull", "HD-01", "--on", "2026-01-03")


def test_drilling_says_how_much_ground_the_device_pulls(cli: Shell) -> None:
    open_site(cli)
    out = cli.ok(
        "well",
        "drill",
        "NORTHRIDGE",
        "A-03",
        "--station",
        "N 12+40",
        "--depth",
        "92",
        "--screen-top",
        "22",
        "--screen-bottom",
        "86",
        "--on",
        "2021-05-12",
        "--influence",
        "150",
    )
    assert "pulling 1.62 acres at 150 ft" in out


def test_a_design_radius_says_how_many_devices_the_area_wants(cli: Shell) -> None:
    furnish(cli)
    narrow = cli.ok("well", "radius", "A-03", "100")
    wide = cli.ok("well", "radius", "A-03", "250")
    assert "designed at 100 ft" in narrow
    assert "designed at 250 ft" in wide
    assert narrow != wide


def test_the_coverage_table_says_what_each_area_is_short(cli: Shell) -> None:
    furnish(cli)
    out = cli.ok("well", "coverage", "NORTHRIDGE", "--on", "2025-04-30")
    assert "A-03" in out
    assert "A-04" in out
    assert "overdue since" in out

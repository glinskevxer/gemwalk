"""The meter group."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.support import Shell, furnish, shell


@pytest.fixture
def cli(tmp_path: Path) -> Shell:
    made = shell(tmp_path)
    furnish(made)
    made.ok(
        "meter",
        "add",
        "GEM5000-40912",
        "NORTHRIDGE",
        "--kind",
        "analyser",
        "--maker",
        "Verrick Instruments",
        "--model",
        "GEM5000",
        "--serial",
        "40912",
        "--on",
        "2022-03-01",
    )
    return made


def calibrate(cli: Shell, at: str, before: str = "49.6", after: str = "50.1") -> str:
    return cli.ok(
        "meter",
        "calibrate",
        "GEM5000-40912",
        at,
        "--standard",
        "50% CH4",
        "--expected",
        "50",
        "--before",
        before,
        "--after",
        after,
        "--by",
        "D. Kasprzak",
    )


def test_adding_a_meter_says_how_long_a_check_lasts(cli: Shell) -> None:
    out = cli.ok(
        "meter",
        "add",
        "TVA-8841",
        "NORTHRIDGE",
        "--kind",
        "detector",
        "--maker",
        "Verrick",
        "--model",
        "TVA1000B",
        "--serial",
        "8841",
        "--on",
        "2022-03-01",
    )
    assert "flame ionisation detector" in out
    assert "stands for 1 day" in out


def test_a_meter_with_no_calibration_is_not_fit(cli: Shell) -> None:
    out = cli.ok("meter", "standing", "GEM5000-40912", "--on", "2025-04-08")
    assert "no calibration on file" in out
    assert "not fit to use" in out


def test_a_calibration_says_the_drift_and_the_error(cli: Shell) -> None:
    out = calibrate(cli, "2025-04-08 05:40")
    assert "drift 0.8%" in out
    assert "error after 0.2%" in out


def test_a_meter_that_failed_says_it_is_not_fit(cli: Shell) -> None:
    out = calibrate(cli, "2025-04-08 05:40", after="56.0")
    assert "did not pass" in out
    assert "not fit to use" in cli.ok("meter", "standing", "GEM5000-40912", "--on", "2025-04-08")


def test_a_meter_that_drifted_says_the_readings_are_in_doubt(cli: Shell) -> None:
    out = calibrate(cli, "2025-04-08 05:40", before="40.0", after="50.2")
    assert "in doubt" in out


def test_a_calibrated_meter_is_fit_that_day_and_not_the_next(cli: Shell) -> None:
    calibrate(cli, "2025-04-08 05:40")
    assert "fit to use" in cli.ok("meter", "standing", "GEM5000-40912", "--on", "2025-04-08")
    out = cli.ok("meter", "standing", "GEM5000-40912", "--on", "2025-04-09")
    assert "does not cover" in out


def test_the_due_list_empties_once_the_meter_is_calibrated(cli: Shell) -> None:
    assert "GEM5000-40912" in cli.ok("meter", "due", "NORTHRIDGE", "--on", "2025-04-08")
    calibrate(cli, "2025-04-08 05:40")
    assert "every meter in service is calibrated" in cli.ok(
        "meter", "due", "NORTHRIDGE", "--on", "2025-04-08"
    )


def test_a_retired_meter_is_never_due(cli: Shell) -> None:
    out = cli.ok("meter", "retire", "GEM5000-40912", "--on", "2025-03-01")
    assert "out of service on 2025-03-01" in out
    assert "every meter in service" in cli.ok("meter", "due", "NORTHRIDGE", "--on", "2025-04-08")


def test_a_meter_never_calibrated_has_no_history(cli: Shell) -> None:
    assert "never been calibrated" in cli.ok("meter", "history", "GEM5000-40912")


def test_the_history_carries_the_drift_and_who_did_it(cli: Shell) -> None:
    calibrate(cli, "2025-04-08 05:40", before="40.0", after="50.2")
    out = cli.ok("meter", "history", "GEM5000-40912")
    assert "D. Kasprzak" in out
    assert "drifted" in out


def test_a_failed_calibration_is_marked_in_the_history(cli: Shell) -> None:
    calibrate(cli, "2025-04-08 05:40", after="56.0")
    assert "failed" in cli.ok("meter", "history", "GEM5000-40912")


def test_the_calibrations_of_one_day_are_listed(cli: Shell) -> None:
    calibrate(cli, "2025-04-08 05:40")
    calibrate(cli, "2025-04-08 16:20")
    out = cli.ok("meter", "day", "GEM5000-40912", "--on", "2025-04-08")
    assert "2 calibrations on 2025-04-08" in out


def test_a_run_will_not_open_on_a_meter_that_is_not_fit(cli: Shell) -> None:
    out = cli.fails(
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
    assert "no calibration" in out


def test_a_run_opens_once_the_meter_is_calibrated(cli: Shell) -> None:
    calibrate(cli, "2025-04-08 05:40")
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

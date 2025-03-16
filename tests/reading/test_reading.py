"""What one wellhead reading says, and what it does not."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import OrderError, RuleError
from gemwalk.model.reading import Reading, Run

TAKEN = dt.date(2025, 4, 8)


def a_reading(**changes: object) -> Reading:
    fields: dict[str, object] = {
        "run": "MR-2025-04-01",
        "device": "VW-041",
        "taken_on": TAKEN,
        "methane": 52.4,
        "carbon": 38.1,
        "oxygen": 0.6,
        "balance": 8.9,
        "temperature": 118.2,
        "static": -1.4,
        "applied": -12.0,
        "flow": 42.0,
        "valve_before": 3.0,
        "valve_after": 3.0,
    }
    fields.update(changes)
    return Reading(**fields)  # type: ignore[arg-type]


def a_run(**changes: object) -> Run:
    fields: dict[str, object] = {
        "label": "MR-2025-04-01",
        "site": "NORTHRIDGE",
        "started_on": TAKEN,
        "monitor": "D. Kasprzak",
        "meter": "GEM5000-40912",
    }
    fields.update(changes)
    return Run(**fields)  # type: ignore[arg-type]


def test_the_four_gas_figures_add_up_to_a_hundred() -> None:
    assert a_reading().balances
    assert a_reading().total == pytest.approx(100.0)


def test_a_sheet_that_does_not_add_up_is_flagged_and_still_stored() -> None:
    reading = a_reading(balance=2.0)
    assert not reading.balances


def test_a_gas_figure_off_the_analyser_scale_is_refused() -> None:
    with pytest.raises(RuleError, match="oxygen"):
        a_reading(oxygen=140.0)
    with pytest.raises(RuleError, match="methane"):
        a_reading(methane=-1.0)


def test_nitrogen_is_the_balance_and_is_not_measured() -> None:
    assert a_reading().nitrogen.value == pytest.approx(8.9)


def test_the_reading_hands_back_each_figure_in_its_own_unit() -> None:
    reading = a_reading()
    assert reading.methane_reading.value == pytest.approx(52.4)
    assert reading.oxygen_reading.value == pytest.approx(0.6)
    assert reading.wellhead_temperature.fahrenheit == pytest.approx(118.2)
    assert reading.gauge.inches == pytest.approx(-1.4)
    assert reading.vacuum.inches == pytest.approx(-12.0)
    assert reading.gas_flow.scfm == pytest.approx(42.0)


def test_a_valve_position_off_the_stem_is_refused() -> None:
    with pytest.raises(RuleError, match="valve"):
        a_reading(valve_after=14.0)
    with pytest.raises(RuleError, match="valve"):
        a_reading(valve_before=-1.0)


def test_a_wellhead_cannot_flow_backwards() -> None:
    with pytest.raises(RuleError, match="backwards"):
        a_reading(flow=-4.0)


def test_a_valve_left_where_it_was_found_was_not_turned() -> None:
    assert not a_reading().was_turned


def test_a_valve_opened_and_a_valve_closed_are_told_apart() -> None:
    opened = a_reading(valve_after=4.5)
    closed = a_reading(valve_after=1.5)
    assert opened.was_turned
    assert opened.was_opened
    assert closed.was_turned
    assert not closed.was_opened


def test_a_wellhead_left_shut_says_so() -> None:
    assert a_reading(valve_after=0.0).is_shut
    assert not a_reading().is_shut


def test_the_methane_share_ignores_the_air_that_got_in() -> None:
    assert a_reading().methane_share == pytest.approx(52.4 / 90.5)


def test_a_wellhead_giving_nothing_has_no_share() -> None:
    assert a_reading(methane=0.0, carbon=0.0, oxygen=20.9, balance=79.1).methane_share == 0.0


def test_a_run_is_walked_by_somebody_with_a_meter() -> None:
    with pytest.raises(RuleError, match="somebody"):
        a_run(monitor="  ")
    with pytest.raises(RuleError, match="serial"):
        a_run(meter="")


def test_a_run_is_open_until_it_is_closed() -> None:
    run = a_run()
    assert run.is_open
    closed = run.close(dt.date(2025, 4, 10))
    assert not closed.is_open
    assert closed.closed_on == dt.date(2025, 4, 10)


def test_a_run_cannot_be_closed_twice_or_before_it_started() -> None:
    run = a_run().close(dt.date(2025, 4, 10))
    with pytest.raises(RuleError):
        run.close(dt.date(2025, 4, 11))
    with pytest.raises(OrderError):
        a_run(closed_on=dt.date(2025, 4, 1))

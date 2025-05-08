"""The walkover itself, and what throws its readings out."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Quarter
from gemwalk.errors import OrderError, RuleError
from gemwalk.model.surface import Walk
from gemwalk.rules import XXX

STARTED = dt.date(2025, 5, 13)


def a_walk(**changes: object) -> Walk:
    fields: dict[str, object] = {
        "label": "SW-2025Q2-01",
        "site": "NORTHRIDGE",
        "quarter": Quarter(2025, 2),
        "started_on": STARTED,
        "monitor": "T. Wierzbicki",
        "instrument": "TVA1000B-8841",
        "background": 2.0,
        "wind_mean": 3.4,
        "wind_gust": 7.1,
        "spacing": 30.0,
    }
    fields.update(changes)
    return Walk(**fields)  # type: ignore[arg-type]


def test_a_calm_walk_on_the_right_pattern_stands() -> None:
    walk = a_walk()
    assert walk.is_valid(XXX)
    assert walk.faults(XXX) == ()


def test_wind_over_the_average_limit_throws_the_walk_out() -> None:
    walk = a_walk(wind_mean=6.2, wind_gust=9.0)
    assert not walk.is_valid(XXX)
    assert "average wind" in walk.faults(XXX)[0]


def test_a_gust_over_the_limit_throws_the_walk_out_on_its_own() -> None:
    walk = a_walk(wind_gust=12.0)
    assert not walk.wind_was_calm(XXX)
    assert any("gust" in fault for fault in walk.faults(XXX))


def test_a_pattern_wider_than_thirty_metres_throws_the_walk_out() -> None:
    walk = a_walk(spacing=45.0)
    assert not walk.pattern_was_close_enough(XXX)
    assert any("spacing" in fault for fault in walk.faults(XXX))


def test_a_walk_can_be_thrown_out_for_more_than_one_reason() -> None:
    walk = a_walk(wind_mean=8.0, wind_gust=14.0, spacing=50.0)
    assert len(walk.faults(XXX)) == 3


def test_a_gust_slower_than_the_average_is_refused() -> None:
    with pytest.raises(RuleError, match="gust"):
        a_walk(wind_mean=8.0, wind_gust=4.0)


def test_a_walk_needs_a_pattern_and_a_background() -> None:
    with pytest.raises(RuleError, match="spacing"):
        a_walk(spacing=0.0)
    with pytest.raises(RuleError, match="background"):
        a_walk(background=-1.0)


def test_a_walk_is_open_until_the_crew_finishes() -> None:
    walk = a_walk()
    assert walk.is_open
    done = walk.finish(dt.date(2025, 5, 15))
    assert not done.is_open
    with pytest.raises(RuleError):
        done.finish(dt.date(2025, 5, 16))


def test_a_walk_cannot_finish_before_it_started() -> None:
    with pytest.raises(OrderError):
        a_walk(finished_on=dt.date(2025, 5, 1))


def test_the_background_reads_back_in_its_own_unit() -> None:
    assert str(a_walk().background_reading) == "2 ppmv"

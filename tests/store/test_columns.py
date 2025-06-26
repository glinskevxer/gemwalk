"""The one place a date, a moment or a flag is written into a column."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.store.columns import (
    day_text,
    flag,
    moment_text,
    read_day_or_none,
    read_flag,
    read_moment_or_none,
)


def test_a_date_goes_out_and_comes_back() -> None:
    day = dt.date(2025, 6, 3)
    assert day_text(day) == "2025-06-03"
    assert read_day_or_none(day_text(day)) == day


def test_a_blank_date_column_stays_blank() -> None:
    assert day_text(None) is None
    assert read_day_or_none(None) is None
    assert read_day_or_none("   ") is None


def test_a_moment_goes_out_as_utc_and_comes_back_the_same_instant() -> None:
    moment = read_moment("2025-06-03 10:20", "America/Chicago")
    written = moment_text(moment)
    assert written is not None
    assert written.endswith("+00:00")
    assert read_moment_or_none(written) == moment


def test_moment_text_sorts_the_way_the_clock_does() -> None:
    zone = "America/Chicago"
    earlier = moment_text(read_moment("2025-06-03 10:20", zone))
    later = moment_text(read_moment("2025-06-03 22:20", zone))
    assert earlier is not None
    assert later is not None
    assert earlier < later


def test_a_blank_moment_column_stays_blank() -> None:
    assert moment_text(None) is None
    assert read_moment_or_none(None) is None


@pytest.mark.parametrize("value", [True, False])
def test_a_flag_goes_out_as_a_number_and_comes_back_a_bool(value: bool) -> None:
    assert flag(value) in (0, 1)
    assert read_flag(flag(value)) is value

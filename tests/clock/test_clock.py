"""The compliance calendar and the site wall clock."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import (
    Month,
    Quarter,
    days_between,
    deadline,
    elapsed,
    hours_between,
    is_overdue,
    read_day,
    read_moment,
    show_moment,
)
from gemwalk.errors import OrderError, UnitError

ZONE = "America/Chicago"


def test_a_field_sheet_date_reads_back() -> None:
    assert read_day("2025-04-08") == dt.date(2025, 4, 8)


def test_a_date_that_is_not_a_date_is_refused() -> None:
    with pytest.raises(UnitError):
        read_day("last thursday")


def test_a_five_day_window_on_a_monday_closes_on_the_saturday() -> None:
    monday = dt.date(2025, 4, 7)
    assert deadline(monday, 5) == dt.date(2025, 4, 12)


def test_a_window_cannot_run_backwards() -> None:
    with pytest.raises(OrderError):
        deadline(dt.date(2025, 4, 7), -1)


def test_a_deadline_is_open_on_its_last_day_and_shut_the_day_after() -> None:
    due = dt.date(2025, 4, 12)
    assert not is_overdue(due, dt.date(2025, 4, 12))
    assert is_overdue(due, dt.date(2025, 4, 13))


def test_days_between_runs_negative_backwards() -> None:
    assert days_between(dt.date(2025, 4, 12), dt.date(2025, 4, 7)) == -5


def test_a_wall_time_becomes_an_aware_moment() -> None:
    moment = read_moment("2025-04-08 06:30", ZONE)
    assert moment.utcoffset() == dt.timedelta(0)
    assert show_moment(moment, ZONE) == "2025-04-08 06:30"


def test_a_moment_that_is_not_a_moment_is_refused() -> None:
    with pytest.raises(UnitError):
        read_moment("half six", ZONE)


def test_an_interval_across_the_spring_change_is_an_hour_short() -> None:
    before = read_moment("2025-03-09 01:30", ZONE)
    after = read_moment("2025-03-09 03:30", ZONE)
    assert hours_between(before, after) == pytest.approx(1.0)


def test_an_interval_across_the_autumn_change_is_an_hour_long() -> None:
    before = read_moment("2025-11-02 00:30", ZONE)
    after = read_moment("2025-11-02 03:30", ZONE)
    assert hours_between(before, after) == pytest.approx(4.0)


def test_elapsed_carries_a_whole_day() -> None:
    start = read_moment("2025-04-08 06:00", ZONE)
    end = read_moment("2025-04-09 06:00", ZONE)
    assert elapsed(start, end) == dt.timedelta(days=1)


def test_a_day_lands_in_its_quarter() -> None:
    assert Quarter.of(dt.date(2025, 4, 8)) == Quarter(2025, 2)


def test_a_quarter_reads_back_from_its_label() -> None:
    assert Quarter.parse("2025-Q2") == Quarter(2025, 2)
    assert str(Quarter(2025, 2)) == "2025Q2"


def test_a_quarter_label_that_is_not_a_quarter_is_refused() -> None:
    with pytest.raises(UnitError):
        Quarter.parse("spring")


def test_a_quarter_knows_both_its_ends() -> None:
    quarter = Quarter(2025, 2)
    assert quarter.first_day == dt.date(2025, 4, 1)
    assert quarter.last_day == dt.date(2025, 6, 30)


def test_the_fourth_quarter_rolls_into_the_next_year() -> None:
    assert Quarter(2025, 4).next == Quarter(2026, 1)
    assert Quarter(2026, 1).previous == Quarter(2025, 4)


def test_a_quarter_holds_its_own_days_only() -> None:
    quarter = Quarter(2025, 2)
    assert quarter.contains(dt.date(2025, 6, 30))
    assert not quarter.contains(dt.date(2025, 7, 1))


def test_a_quarter_number_outside_one_to_four_is_refused() -> None:
    with pytest.raises(UnitError):
        Quarter(2025, 5)


def test_a_month_knows_both_its_ends_and_its_quarter() -> None:
    month = Month.parse("2025-02")
    assert month.first_day == dt.date(2025, 2, 1)
    assert month.last_day == dt.date(2025, 2, 28)
    assert month.quarter == Quarter(2025, 1)


def test_december_rolls_into_january() -> None:
    assert Month(2025, 12).next == Month(2026, 1)
    assert Month(2026, 1).previous == Month(2025, 12)


def test_a_month_label_that_is_not_a_month_is_refused() -> None:
    with pytest.raises(UnitError):
        Month.parse("2025-13")
    with pytest.raises(UnitError):
        Month.parse("April")


def test_a_month_of_a_day_is_the_day_s_own_month() -> None:
    assert Month.of(dt.date(2025, 4, 30)) == Month(2025, 4)


def test_a_month_contains_its_own_days_only() -> None:
    month = Month(2025, 4)
    assert month.contains(dt.date(2025, 4, 30))
    assert not month.contains(dt.date(2025, 5, 1))

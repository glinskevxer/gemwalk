"""The three criteria for turning a collection system off."""

from __future__ import annotations

import datetime as dt
import math

import pytest

from gemwalk.errors import RuleError
from gemwalk.nmoc import CONVERSION, DEFAULT_K, DEFAULT_L0, Inputs, rate
from gemwalk.removal import DAYS_APART, SAMPLES_WANTED, YEARS_CLOSED, Sample, case
from gemwalk.rules import XXX

CLOSED = dt.date(2005, 6, 30)
ASKED = dt.date(2025, 6, 30)


ACCEPTANCE = 180_000.0
AGE = 40.0
# What one part per million of measured concentration is worth in megagrams a
# year at this acceptance rate and age, so a case can ask for a rate and get it.
PER_PPM = 2.0 * DEFAULT_L0 * ACCEPTANCE * (1.0 - math.exp(-DEFAULT_K * AGE)) * CONVERSION


def a_sample(on: dt.date, megagrams: float) -> Sample:
    inputs = Inputs(acceptance=ACCEPTANCE, age=AGE).measure_concentration(megagrams / PER_PPM)
    made = Sample(on=on, estimate=rate(inputs))
    assert made.estimate.megagrams == pytest.approx(megagrams)
    return made


def three(first: dt.date, gap: int, rates: tuple[float, float, float]) -> list[Sample]:
    return [a_sample(first + dt.timedelta(days=gap * n), rates[n]) for n in range(3)]


def test_a_site_still_taking_waste_cannot_turn_anything_off() -> None:
    read = case(XXX, closed_on=None, asked_on=ASKED, tests=[])
    assert not read.is_allowed
    assert "still taking waste" in read.missing[0]


def test_a_site_closed_too_recently_says_how_short_it_is() -> None:
    read = case(XXX, closed_on=dt.date(2020, 1, 1), asked_on=ASKED, tests=[])
    assert not read.long_enough
    assert any("short of 15" in said for said in read.missing)


def test_a_site_closed_long_enough_passes_the_first_criterion() -> None:
    read = case(XXX, closed_on=CLOSED, asked_on=ASKED, tests=[])
    assert read.long_enough
    assert read.years_closed == pytest.approx(20.0, abs=0.1)


def test_too_few_tests_says_how_many_are_wanted() -> None:
    read = case(XXX, closed_on=CLOSED, asked_on=ASKED, tests=[a_sample(ASKED, 10.0)])
    assert not read.enough_tests
    assert any(f"short of {SAMPLES_WANTED}" in said for said in read.missing)


def test_tests_too_close_together_are_refused() -> None:
    tests = three(dt.date(2024, 1, 1), 30, (10.0, 9.0, 8.0))
    read = case(XXX, closed_on=CLOSED, asked_on=ASKED, tests=tests)
    assert read.enough_tests
    assert not read.far_enough_apart
    assert any(f"not {DAYS_APART} days apart" in said for said in read.missing)


def test_tests_far_enough_apart_pass() -> None:
    tests = three(dt.date(2024, 1, 1), 120, (10.0, 9.0, 8.0))
    read = case(XXX, closed_on=CLOSED, asked_on=ASKED, tests=tests)
    assert read.far_enough_apart


def test_a_test_over_the_threshold_stops_the_whole_thing() -> None:
    tests = three(dt.date(2024, 1, 1), 120, (10.0, 60.0, 8.0))
    read = case(XXX, closed_on=CLOSED, asked_on=ASKED, tests=tests)
    assert not read.all_under
    assert any("not every test" in said for said in read.missing)


def test_a_rate_that_is_going_up_stops_it_too() -> None:
    tests = three(dt.date(2024, 1, 1), 120, (8.0, 9.0, 10.0))
    read = case(XXX, closed_on=CLOSED, asked_on=ASKED, tests=tests)
    assert read.all_under
    assert not read.settled
    assert any("still going up" in said for said in read.missing)


def test_a_rate_holding_level_counts_as_settled() -> None:
    tests = three(dt.date(2024, 1, 1), 120, (9.0, 9.0, 9.0))
    read = case(XXX, closed_on=CLOSED, asked_on=ASKED, tests=tests)
    assert read.settled


def test_everything_true_at_once_allows_the_system_off() -> None:
    tests = three(dt.date(2023, 1, 1), 120, (10.0, 9.0, 8.0))
    read = case(XXX, closed_on=CLOSED, asked_on=ASKED, tests=tests)
    assert read.is_allowed
    assert read.missing == ()
    assert "may be turned off" in str(read)


def test_only_the_three_most_recent_tests_are_read() -> None:
    tests = [
        a_sample(dt.date(2019, 1, 1), 90.0),
        *three(dt.date(2023, 1, 1), 120, (10.0, 9.0, 8.0)),
    ]
    read = case(XXX, closed_on=CLOSED, asked_on=ASKED, tests=tests)
    assert read.is_allowed
    assert len(read.tests) == 4


def test_the_tests_are_read_in_date_order_however_they_arrive() -> None:
    tests = list(reversed(three(dt.date(2023, 1, 1), 120, (10.0, 9.0, 8.0))))
    read = case(XXX, closed_on=CLOSED, asked_on=ASKED, tests=tests)
    assert [test.on for test in read.tests] == sorted(test.on for test in tests)
    assert read.is_allowed


def test_a_day_before_the_site_closed_is_refused() -> None:
    with pytest.raises(RuleError, match="before the site closed"):
        case(XXX, closed_on=CLOSED, asked_on=dt.date(2000, 1, 1), tests=[])


def test_the_years_are_counted_from_closure_and_not_from_the_last_load() -> None:
    read = case(XXX, closed_on=CLOSED, asked_on=CLOSED, tests=[])
    assert read.years_closed == pytest.approx(0.0)
    assert YEARS_CLOSED == 15


def test_a_case_that_fails_says_everything_that_is_missing() -> None:
    read = case(XXX, closed_on=dt.date(2020, 1, 1), asked_on=ASKED, tests=[])
    assert len(read.missing) == 2
    assert str(read).startswith("not yet: ")

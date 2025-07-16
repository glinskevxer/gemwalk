"""The emission rate, and what changes when a site measures its own gas."""

from __future__ import annotations

import math

import pytest

from gemwalk.errors import RuleError
from gemwalk.nmoc import (
    CONVERSION,
    DEFAULT_ARID_K,
    DEFAULT_K,
    DEFAULT_L0,
    DEFAULT_NMOC,
    Inputs,
    Tier,
    needed,
    rate,
    tier_one,
)
from gemwalk.rules import WWW, XXX


def by_hand(acceptance: float, age: float, k: float, concentration: float) -> float:
    return 2.0 * DEFAULT_L0 * acceptance * (1.0 - math.exp(-k * age)) * concentration * CONVERSION


def test_the_equation_is_the_one_in_the_standard() -> None:
    estimate = tier_one(180_000.0, 27.0)
    assert estimate.megagrams == pytest.approx(by_hand(180_000.0, 27.0, DEFAULT_K, DEFAULT_NMOC))


def test_a_first_pass_is_at_the_first_tier() -> None:
    assert tier_one(180_000.0, 27.0).tier is Tier.ONE


def test_a_dry_climate_uses_the_slower_rate_constant() -> None:
    wet = tier_one(180_000.0, 27.0)
    dry = tier_one(180_000.0, 27.0, arid=True)
    assert dry.megagrams < wet.megagrams
    assert dry.inputs.rate_constant == DEFAULT_ARID_K


def test_a_bigger_site_generates_more() -> None:
    small = tier_one(40_000.0, 27.0)
    large = tier_one(180_000.0, 27.0)
    assert large.megagrams > small.megagrams


def test_an_older_site_generates_more_up_to_a_point() -> None:
    young = tier_one(180_000.0, 5.0)
    old = tier_one(180_000.0, 40.0)
    assert old.megagrams > young.megagrams


def test_a_closed_site_generates_less_than_the_same_site_open() -> None:
    open_site = rate(Inputs(acceptance=180_000.0, age=30.0))
    closed = rate(Inputs(acceptance=180_000.0, age=30.0, closed_years=6.0))
    assert closed.megagrams < open_site.megagrams


def test_sampling_the_gas_moves_the_site_to_the_second_tier() -> None:
    first = Inputs(acceptance=180_000.0, age=27.0)
    second = first.measure_concentration(595.0)
    assert second.tier is Tier.TWO
    assert rate(second).megagrams < rate(first).megagrams


def test_a_site_over_at_the_first_tier_can_be_under_at_the_second() -> None:
    first = rate(Inputs(acceptance=180_000.0, age=27.0))
    assert first.over(XXX)
    second = rate(Inputs(acceptance=180_000.0, age=27.0).measure_concentration(190.0))
    assert not second.over(XXX)


def test_the_two_standards_do_not_agree_about_the_threshold() -> None:
    estimate = rate(Inputs(acceptance=10_000.0, age=27.0))
    assert estimate.megagrams == pytest.approx(36.3, abs=0.5)
    assert estimate.over(XXX)
    assert not estimate.over(WWW)


def test_the_margin_says_how_far_over_or_under() -> None:
    estimate = rate(Inputs(acceptance=180_000.0, age=27.0))
    assert estimate.margin(XXX) == pytest.approx(estimate.megagrams - 34.0)
    assert estimate.margin(XXX) > 0


def test_measuring_the_rate_constant_is_the_third_tier() -> None:
    third = Inputs(acceptance=180_000.0, age=27.0).measure_rate(0.032)
    assert third.tier is Tier.THREE
    assert rate(third).megagrams < rate(Inputs(acceptance=180_000.0, age=27.0)).megagrams


def test_a_rate_constant_off_the_defaults_needs_the_third_tier() -> None:
    with pytest.raises(RuleError, match="tier 3"):
        Inputs(acceptance=180_000.0, age=27.0, rate_constant=0.032)


def test_a_measured_concentration_needs_the_second_tier() -> None:
    with pytest.raises(RuleError, match="tier 1"):
        Inputs(acceptance=180_000.0, age=27.0, concentration=595.0)


def test_a_landfill_with_no_waste_and_no_age_is_refused() -> None:
    with pytest.raises(RuleError, match="no waste"):
        Inputs(acceptance=0.0, age=27.0)
    with pytest.raises(RuleError, match="years since"):
        Inputs(acceptance=180_000.0, age=0.0)


def test_a_closure_before_the_opening_is_refused() -> None:
    with pytest.raises(RuleError, match="future"):
        Inputs(acceptance=180_000.0, age=27.0, closed_years=-1.0)
    with pytest.raises(RuleError, match="before it opened"):
        Inputs(acceptance=180_000.0, age=27.0, closed_years=30.0)


def test_the_other_figures_have_to_be_positive() -> None:
    with pytest.raises(RuleError, match="generation potential"):
        Inputs(acceptance=180_000.0, age=27.0, generation_potential=0.0)
    with pytest.raises(RuleError, match="rate constant is positive"):
        Inputs(acceptance=180_000.0, age=27.0, rate_constant=0.0, tier=Tier.THREE)
    with pytest.raises(RuleError, match="concentration is positive"):
        Inputs(acceptance=180_000.0, age=27.0, concentration=0.0, tier=Tier.TWO)


def test_a_small_landfill_over_the_threshold_is_not_caught() -> None:
    estimate = rate(Inputs(acceptance=180_000.0, age=27.0))
    assert estimate.over(XXX)
    assert not needed(estimate, XXX, 900_000.0)
    assert needed(estimate, XXX, 8_400_000.0)


def test_a_large_landfill_under_the_threshold_is_not_caught_either() -> None:
    estimate = rate(Inputs(acceptance=180_000.0, age=27.0).measure_concentration(120.0))
    assert not estimate.over(XXX)
    assert not needed(estimate, XXX, 8_400_000.0)

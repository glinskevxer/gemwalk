"""Reading an analysis for what it says about the well."""

from __future__ import annotations

import pytest

from gemwalk.errors import RuleError
from gemwalk.quality import AIR_RATIO, Character, Quality
from gemwalk.units import Flow


def a_sample(**changes: float) -> Quality:
    fields: dict[str, float] = {
        "methane": 52.4,
        "carbon": 38.1,
        "oxygen": 0.6,
        "balance": 8.9,
    }
    fields.update(changes)
    return Quality(**fields)


def test_air_brings_about_three_and_three_quarter_times_its_oxygen() -> None:
    assert pytest.approx(3.7847, abs=1e-3) == AIR_RATIO


def test_a_figure_off_the_analyser_scale_is_refused() -> None:
    with pytest.raises(RuleError, match="oxygen"):
        a_sample(oxygen=140.0)
    with pytest.raises(RuleError, match="methane"):
        a_sample(methane=-1.0)


def test_the_air_is_worked_back_from_the_oxygen() -> None:
    assert a_sample(oxygen=5.0).air == pytest.approx(5.0 * (1 + AIR_RATIO))


def test_a_sample_full_of_air_cannot_be_more_than_all_of_it() -> None:
    assert a_sample(oxygen=90.0, methane=0.0, carbon=0.0, balance=10.0).air == 100.0


def test_a_leaking_wellhead_reads_as_air() -> None:
    leaking = a_sample(methane=41.0, carbon=30.0, oxygen=6.1, balance=22.8)
    assert leaking.looks_like_air
    assert leaking.character() is Character.AIR


def test_nitrogen_with_no_oxygen_behind_it_is_not_air() -> None:
    starved = a_sample(methane=38.0, carbon=27.0, oxygen=0.4, balance=34.5)
    assert not starved.looks_like_air
    assert starved.excess_nitrogen > 15.0
    assert starved.character() is Character.STARVED


def test_an_ordinary_wellhead_is_settled() -> None:
    assert a_sample().character() is Character.SETTLED


def test_a_wellhead_making_nothing_is_thin() -> None:
    assert a_sample(methane=0.4, carbon=1.0, oxygen=20.0, balance=78.0).character() is (
        Character.THIN
    )


def test_four_figures_that_cannot_be_one_sample_say_so() -> None:
    assert a_sample(balance=40.0).character() is Character.IMPOSSIBLE


def test_a_sample_with_no_oxygen_has_no_ratio_to_speak_of() -> None:
    dry = a_sample(oxygen=0.0, balance=9.5)
    assert dry.nitrogen_ratio == float("inf")
    assert not dry.looks_like_air


def test_taking_the_air_out_raises_the_methane() -> None:
    leaking = a_sample(methane=41.0, carbon=30.0, oxygen=6.1, balance=22.8)
    assert leaking.corrected_methane.value > 41.0


def test_two_readings_that_differ_only_in_air_correct_to_the_same_gas() -> None:
    tight = Quality(methane=52.0, carbon=38.0, oxygen=0.5, balance=9.5)
    # The same gas with a quarter of the sample made up of air.
    leaking = Quality(methane=39.0, carbon=28.5, oxygen=5.6, balance=26.9)
    assert tight.corrected_methane.value == pytest.approx(leaking.corrected_methane.value, abs=2.0)


def test_a_sample_that_is_all_air_corrects_to_nothing() -> None:
    corrected = Quality(methane=0.0, carbon=0.0, oxygen=20.9, balance=79.1).without_air()
    assert corrected.methane == 0.0
    assert corrected.balance == 0.0
    assert corrected.total == 0.0


def test_the_heat_value_follows_the_methane() -> None:
    assert a_sample(methane=50.0).heat_value() == pytest.approx(506.0)
    assert a_sample(methane=0.0).heat_value() == 0.0


def test_the_energy_follows_the_flow() -> None:
    sample = a_sample(methane=50.0)
    assert sample.energy(Flow(1_000.0)) == pytest.approx(506.0 * 60_000 / 1_000_000)
    assert sample.energy(Flow(0.0)) == 0.0


def test_a_character_prints_the_sentence_the_desk_reads() -> None:
    assert str(Character.AIR) == "air being pulled in"
    assert len({str(c) for c in Character}) == len(Character)

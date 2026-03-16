"""Describing a column of numbers."""

from __future__ import annotations

import pytest

from gemwalk.errors import RuleError
from gemwalk.spread import quantile, share_over, share_under, spread

EVEN = [1.0, 2.0, 3.0, 4.0]
ODD = [1.0, 2.0, 3.0, 4.0, 5.0]


def test_the_median_of_an_even_list_is_between_the_middle_two() -> None:
    assert quantile(EVEN, 0.5) == pytest.approx(2.5)


def test_the_median_of_an_odd_list_is_the_middle_one() -> None:
    assert quantile(ODD, 0.5) == pytest.approx(3.0)


def test_the_ends_are_the_smallest_and_the_largest() -> None:
    assert quantile(EVEN, 0.0) == pytest.approx(1.0)
    assert quantile(EVEN, 1.0) == pytest.approx(4.0)


def test_a_list_of_one_is_all_of_its_own_quantiles() -> None:
    assert quantile([7.0], 0.25) == pytest.approx(7.0)
    assert quantile([7.0], 0.9) == pytest.approx(7.0)


def test_the_quartiles_interpolate_the_way_a_spreadsheet_does() -> None:
    assert quantile(EVEN, 0.25) == pytest.approx(1.75)
    assert quantile(EVEN, 0.75) == pytest.approx(3.25)


def test_an_order_does_not_matter() -> None:
    assert quantile([4.0, 1.0, 3.0, 2.0], 0.5) == pytest.approx(2.5)


def test_a_quantile_of_nothing_is_refused() -> None:
    with pytest.raises(RuleError, match="nothing to take"):
        quantile([], 0.5)


def test_a_quantile_outside_the_range_is_refused() -> None:
    with pytest.raises(RuleError, match="between none of it"):
        quantile(EVEN, 1.4)


def test_a_spread_carries_both_ends_and_the_middle() -> None:
    read = spread(ODD)
    assert read.count == 5
    assert read.smallest == pytest.approx(1.0)
    assert read.largest == pytest.approx(5.0)
    assert read.middle == pytest.approx(3.0)
    assert read.mean == pytest.approx(3.0)


def test_the_middle_half_and_the_whole_reach_are_told_apart() -> None:
    read = spread(ODD)
    assert read.between == pytest.approx(2.0)
    assert read.reach == pytest.approx(4.0)


def test_two_fields_with_the_same_mean_have_different_shapes() -> None:
    flat = spread([50.0] * 8)
    split = spread([30.0] * 4 + [70.0] * 4)
    assert flat.mean == pytest.approx(split.mean)
    assert flat.between < split.between


def test_a_field_that_is_all_the_same_is_tight() -> None:
    assert spread([50.0] * 8).is_tight


def test_a_field_with_one_outlier_is_still_tight() -> None:
    read = spread([50.0] * 20 + [4.0])
    assert read.is_tight


def test_a_field_spread_evenly_is_not_tight() -> None:
    assert not spread([float(n) for n in range(20)]).is_tight


def test_an_outlier_is_found_and_the_rest_are_not() -> None:
    values = [50.0, 51.0, 49.0, 52.0, 48.0, 4.0]
    read = spread(values)
    assert read.outliers(values) == [4.0]


def test_a_column_with_no_middle_half_has_no_outliers() -> None:
    values = [50.0] * 6
    assert spread(values).outliers(values) == []


def test_a_spread_prints_the_sentence_the_report_uses() -> None:
    assert "5 readings, 1 to 5" in str(spread(ODD))


def test_a_spread_of_nothing_is_refused() -> None:
    with pytest.raises(RuleError, match="nothing to describe"):
        spread([])


def test_the_share_under_and_over_a_threshold() -> None:
    assert share_under(ODD, 3.0) == pytest.approx(0.4)
    assert share_over(ODD, 3.0) == pytest.approx(0.4)
    assert share_under(ODD, 0.0) == pytest.approx(0.0)
    assert share_over(ODD, 9.0) == pytest.approx(0.0)


def test_a_share_of_nothing_is_refused() -> None:
    with pytest.raises(RuleError, match="nothing to count"):
        share_under([], 3.0)
    with pytest.raises(RuleError, match="nothing to count"):
        share_over([], 3.0)

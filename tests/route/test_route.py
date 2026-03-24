"""The pattern a walkover is meant to follow."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.route import SQUARE_METRES_IN_AN_ACRE, Leg, Route, pattern_for
from gemwalk.rules import XXX


def a_leg(label: str = "LG-01", metres: float = 200.0) -> Leg:
    return Leg(
        label=label,
        site="NORTHRIDGE",
        area="A-03",
        name=f"line {label}",
        metres=metres,
    )


def test_a_leg_is_some_distance_and_has_a_name() -> None:
    with pytest.raises(RuleError, match="some distance"):
        a_leg(metres=0.0)
    with pytest.raises(RuleError, match="called something"):
        Leg(label="LG-01", site="X", area="A", name="  ", metres=100.0)


def test_a_leg_sweeps_a_strip_a_spacing_wide() -> None:
    assert a_leg().swept(XXX) == pytest.approx(200.0 * 30.0)


def test_a_leg_retires_once() -> None:
    retired = a_leg().retire(dt.date(2025, 6, 1))
    assert not retired.is_live
    with pytest.raises(StateError):
        retired.retire(dt.date(2025, 7, 1))


def test_a_route_with_no_pattern_says_so() -> None:
    route = Route(area="A-03", acres=12.4, legs=(), walked=())
    assert not route.is_whole
    assert route.share == 0.0
    assert "no pattern has been laid out" in str(route)


def test_a_route_walked_whole_says_so() -> None:
    legs = (a_leg("LG-01"), a_leg("LG-02"))
    route = Route(area="A-03", acres=12.4, legs=legs, walked=("LG-01", "LG-02"))
    assert route.is_whole
    assert route.missed == ()
    assert route.share == pytest.approx(1.0)
    assert "all 2 legs walked" in str(route)


def test_a_route_that_missed_a_leg_names_it() -> None:
    legs = (a_leg("LG-01"), a_leg("LG-02"), a_leg("LG-03"))
    route = Route(area="A-03", acres=12.4, legs=legs, walked=("LG-01", "LG-03"))
    assert route.missed == ("LG-02",)
    assert route.share == pytest.approx(2 / 3)
    assert "missed LG-02" in str(route)


def test_the_ground_swept_is_the_legs_that_were_walked() -> None:
    legs = (a_leg("LG-01"), a_leg("LG-02"))
    route = Route(area="A-03", acres=12.4, legs=legs, walked=("LG-01",))
    assert route.swept(XXX) == pytest.approx(200.0 * 30.0 / SQUARE_METRES_IN_AN_ACRE)


def test_a_pattern_big_enough_covers_the_area() -> None:
    legs = tuple(a_leg(f"LG-{n:02d}", metres=400.0) for n in range(1, 20))
    route = Route(area="A-03", acres=12.4, legs=legs, walked=tuple(leg.label for leg in legs))
    assert route.enough_for(XXX)


def test_a_pattern_too_small_does_not_cover_the_area() -> None:
    legs = (a_leg("LG-01"),)
    route = Route(area="A-03", acres=12.4, legs=legs, walked=("LG-01",))
    assert not route.enough_for(XXX)


def test_how_many_legs_a_pattern_needs() -> None:
    assert pattern_for(12.4, XXX, 400.0) == 5
    assert pattern_for(12.4, XXX, 200.0) == 9


def test_a_longer_leg_means_fewer_of_them() -> None:
    assert pattern_for(12.4, XXX, 800.0) < pattern_for(12.4, XXX, 200.0)


def test_a_pattern_over_no_ground_is_refused() -> None:
    with pytest.raises(RuleError, match="covers some ground"):
        pattern_for(0.0, XXX, 200.0)
    with pytest.raises(OrderError):
        pattern_for(12.4, XXX, 0.0)


def test_a_tiny_area_still_wants_one_leg() -> None:
    assert pattern_for(0.01, XXX, 400.0) == 1

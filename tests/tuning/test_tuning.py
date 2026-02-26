"""What to do to the valve, worked out from what the wellhead read."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.model.device import Device, Kind
from gemwalk.model.reading import Reading
from gemwalk.rules import XXX
from gemwalk.tuning import Advice, Move, advise, plan
from gemwalk.units import Temperature

TAKEN = dt.date(2025, 4, 8)


def a_device(**changes: object) -> Device:
    fields: dict[str, object] = {
        "label": "VW-041",
        "site": "NORTHRIDGE",
        "area": "A-03",
        "kind": Kind.VERTICAL,
        "station": "N 12+40",
        "total_depth": 92.0,
        "screen_top": 22.0,
        "screen_bottom": 86.0,
        "drilled_on": dt.date(2021, 5, 12),
    }
    fields.update(changes)
    return Device(**fields)  # type: ignore[arg-type]


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


def said(**changes: object) -> Advice:
    return advise(a_reading(**changes), a_device(), XXX)


def test_a_settled_wellhead_is_left_alone() -> None:
    given = said()
    assert given.move is Move.HOLD
    assert not given.is_action
    assert "nothing about it wants moving" in str(given)


def test_a_hot_wellhead_is_closed_in_a_whole_turn() -> None:
    given = said(temperature=138.0)
    assert given.move is Move.CLOSE
    assert given.turns == pytest.approx(1.0)
    assert "over the 131.0 F limit" in str(given)


def test_a_wellhead_near_the_limit_is_closed_in_a_half() -> None:
    given = said(temperature=127.0)
    assert given.move is Move.CLOSE
    assert given.turns == pytest.approx(0.5)
    assert "within 5 of" in str(given)


def test_an_approved_value_changes_what_counts_as_hot() -> None:
    raised = a_device().approve_higher_temperature(Temperature(145.0), dt.date(2025, 3, 1))
    given = advise(a_reading(temperature=138.0), raised, XXX)
    assert given.move is Move.HOLD


def test_a_wellhead_pulling_air_is_closed_in() -> None:
    given = said(methane=41.0, carbon=30.0, oxygen=6.1, balance=22.8)
    assert given.move is Move.CLOSE
    assert given.turns == pytest.approx(1.0)
    assert "of the sample is air" in str(given)


def test_a_little_air_gets_a_smaller_move() -> None:
    given = said(methane=45.0, carbon=33.0, oxygen=4.5, balance=17.0)
    assert given.move is Move.CLOSE
    assert given.turns == pytest.approx(0.5)


def test_a_starved_wellhead_is_closed_in() -> None:
    given = said(methane=38.0, carbon=27.0, oxygen=0.4, balance=34.5)
    assert given.move is Move.CLOSE
    assert "nitrogen with no oxygen behind it" in str(given)


def test_a_wellhead_at_atmosphere_is_opened_up() -> None:
    given = said(static=0.4)
    assert given.move is Move.OPEN
    assert given.turns == pytest.approx(0.5)
    assert "going out through the cover" in str(given)


def test_a_wellhead_giving_nothing_is_shut_in() -> None:
    given = said(methane=1.0, carbon=1.0, oxygen=0.5, balance=97.5)
    assert given.move is Move.SHUT
    assert given.is_action


def test_a_wellhead_already_shut_and_giving_nothing_is_left() -> None:
    given = said(methane=1.0, carbon=1.0, oxygen=0.5, balance=97.5, flow=0.0, valve_after=0.0)
    assert given.move is Move.HOLD


def test_a_flooded_wellhead_gets_no_valve_answer() -> None:
    given = advise(a_reading(flow=0.0), a_device(), XXX, flooded=True)
    assert given.move is Move.NONE
    assert not given.is_action
    assert "dewater it" in str(given)


def test_a_sheet_that_does_not_add_up_gets_no_answer_either() -> None:
    given = said(balance=2.0)
    assert given.move is Move.NONE
    assert "do not add up" in str(given)


def test_a_flooded_wellhead_is_answered_before_the_gas_is_read() -> None:
    given = advise(
        a_reading(methane=4.0, carbon=3.0, oxygen=2.0, balance=91.0, flow=0.0),
        a_device(),
        XXX,
        flooded=True,
    )
    assert given.move is Move.NONE
    assert "water" in str(given)


def test_closing_in_never_takes_the_valve_off_the_stem() -> None:
    given = said(temperature=138.0)
    assert given.position(a_reading(valve_after=0.5)) == pytest.approx(0.0)


def test_opening_up_never_takes_the_valve_off_the_stem() -> None:
    given = said(static=0.4)
    assert given.position(a_reading(valve_after=10.0)) == pytest.approx(10.0)


def test_a_hold_leaves_the_valve_where_it_is() -> None:
    given = said()
    assert given.position(a_reading(valve_after=3.0)) == pytest.approx(3.0)


def test_shutting_in_puts_the_valve_at_nothing() -> None:
    given = said(methane=1.0, carbon=1.0, oxygen=0.5, balance=97.5)
    assert given.position(a_reading(valve_after=3.0)) == pytest.approx(0.0)


def test_a_plan_puts_the_wellheads_that_need_touching_first() -> None:
    given = plan(
        [
            (a_reading(device="VW-001"), a_device(label="VW-001"), False),
            (a_reading(device="VW-002", temperature=138.0), a_device(label="VW-002"), False),
            (a_reading(device="VW-003", static=0.4), a_device(label="VW-003"), False),
        ],
        XXX,
    )
    assert [a.device for a in given] == ["VW-002", "VW-003", "VW-001"]


def test_a_bigger_move_comes_before_a_smaller_one() -> None:
    given = plan(
        [
            (a_reading(device="VW-001", temperature=127.0), a_device(label="VW-001"), False),
            (a_reading(device="VW-002", temperature=138.0), a_device(label="VW-002"), False),
        ],
        XXX,
    )
    assert [a.device for a in given] == ["VW-002", "VW-001"]

"""How a device is built, and the states it goes through."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.device import Device, Kind, State
from gemwalk.rules import WWW, XXX
from gemwalk.units import Temperature

DRILLED = dt.date(2021, 5, 12)


def a_device(**changes: object) -> Device:
    fields: dict[str, object] = {
        "label": "VW-041",
        "site": "NORTHRIDGE",
        "area": "A-03",
        "kind": Kind.VERTICAL,
        "station": "N 12+40 E 3+15",
        "total_depth": 92.0,
        "screen_top": 22.0,
        "screen_bottom": 86.0,
        "drilled_on": DRILLED,
    }
    fields.update(changes)
    return Device(**fields)  # type: ignore[arg-type]


def test_a_screen_cannot_sit_below_the_bottom_of_the_hole() -> None:
    with pytest.raises(RuleError, match="borehole"):
        a_device(screen_bottom=99.0)


def test_a_screen_has_to_run_downwards() -> None:
    with pytest.raises(OrderError):
        a_device(screen_top=86.0, screen_bottom=22.0)


def test_a_device_has_depth_and_a_screen_below_the_surface() -> None:
    with pytest.raises(RuleError):
        a_device(total_depth=0.0)
    with pytest.raises(RuleError):
        a_device(screen_top=-2.0)


def test_the_screen_length_is_what_is_pulling_on_the_refuse() -> None:
    assert a_device().screen_length == pytest.approx(64.0)


def test_a_drilled_device_is_not_on_the_run_yet() -> None:
    device = a_device()
    assert device.state is State.DRILLED
    assert not device.is_monitored


def test_connecting_puts_a_device_on_the_run() -> None:
    device = a_device().connect(dt.date(2021, 6, 2))
    assert device.is_connected
    assert device.is_monitored
    assert device.connected_on == dt.date(2021, 6, 2)


def test_a_device_cannot_be_connected_before_it_was_drilled() -> None:
    with pytest.raises(OrderError):
        a_device().connect(dt.date(2021, 1, 1))


def test_a_device_cannot_be_connected_twice() -> None:
    device = a_device().connect(dt.date(2021, 6, 2))
    with pytest.raises(StateError):
        device.connect(dt.date(2021, 7, 2))


def test_a_device_off_the_run_is_not_monitored() -> None:
    device = a_device().connect(dt.date(2021, 6, 2)).take_offline(dt.date(2025, 3, 1))
    assert device.state is State.OFFLINE
    assert not device.is_monitored


def test_a_device_that_was_never_connected_cannot_go_offline() -> None:
    with pytest.raises(StateError):
        a_device().take_offline(dt.date(2025, 3, 1))


def test_a_device_goes_back_on_the_run_after_a_raise() -> None:
    device = a_device().connect(dt.date(2021, 6, 2)).take_offline(dt.date(2025, 3, 1))
    back = device.put_online(dt.date(2025, 4, 2))
    assert back.is_monitored
    assert back.offline_since is None


def test_a_device_cannot_come_back_before_it_went_off() -> None:
    device = a_device().connect(dt.date(2021, 6, 2)).take_offline(dt.date(2025, 3, 1))
    with pytest.raises(OrderError):
        device.put_online(dt.date(2025, 2, 1))


def test_a_device_on_the_run_cannot_come_back_on() -> None:
    device = a_device().connect(dt.date(2021, 6, 2))
    with pytest.raises(StateError):
        device.put_online(dt.date(2025, 4, 2))


def test_a_raise_that_runs_past_sixty_days_is_a_finding() -> None:
    device = a_device().connect(dt.date(2021, 6, 2)).take_offline(dt.date(2025, 3, 1))
    assert device.offline_days(dt.date(2025, 4, 30)) == 60
    assert not device.offline_too_long(XXX, dt.date(2025, 4, 30))
    assert device.offline_too_long(XXX, dt.date(2025, 5, 1))


def test_a_device_on_the_run_has_been_off_for_no_days() -> None:
    device = a_device().connect(dt.date(2021, 6, 2))
    assert device.offline_days(dt.date(2025, 5, 1)) == 0


def test_an_abandoned_device_stays_abandoned() -> None:
    device = a_device().connect(dt.date(2021, 6, 2)).abandon(dt.date(2026, 1, 8))
    assert device.state is State.ABANDONED
    assert device.abandoned_on == dt.date(2026, 1, 8)
    with pytest.raises(StateError):
        device.abandon(dt.date(2026, 2, 8))


def test_without_an_approval_the_wellhead_is_held_to_the_standard() -> None:
    device = a_device()
    assert device.temperature_limit(XXX, dt.date(2025, 4, 8)) == Temperature(131.0)


def test_an_approved_value_lifts_the_limit_from_the_day_it_was_approved() -> None:
    device = a_device().approve_higher_temperature(Temperature(145.0), dt.date(2025, 3, 1))
    assert device.temperature_limit(XXX, dt.date(2025, 2, 8)) == Temperature(131.0)
    assert device.temperature_limit(XXX, dt.date(2025, 4, 8)) == Temperature(145.0)


def test_an_approval_applies_to_one_device_and_not_its_neighbour() -> None:
    raised = a_device().approve_higher_temperature(Temperature(145.0), dt.date(2025, 3, 1))
    plain = a_device(label="VW-042")
    day = dt.date(2025, 4, 8)
    assert raised.temperature_limit(XXX, day).fahrenheit == 145.0
    assert plain.temperature_limit(XXX, day).fahrenheit == 131.0


def test_a_standard_that_allows_an_approval_and_one_that_does_not() -> None:
    device = a_device().approve_higher_temperature(Temperature(145.0), dt.date(2025, 3, 1))
    day = dt.date(2025, 4, 8)
    assert device.temperature_limit(XXX, day).fahrenheit == 145.0
    assert WWW.allows_higher_temperature
    assert device.temperature_limit(WWW, day).fahrenheit == 145.0


def test_a_kind_and_a_state_print_as_the_words_the_sheet_uses() -> None:
    assert str(Kind.HORIZONTAL) == "horizontal collector"
    assert str(State.OFFLINE) == "offline"

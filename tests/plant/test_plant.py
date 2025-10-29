"""The control devices, their operating record and their outages."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.plant import Control, ControlKind, Operation, Outage, block_start

ZONE = "America/Chicago"
INSTALLED = dt.date(2016, 4, 1)


def a_control(**changes: object) -> Control:
    fields: dict[str, object] = {
        "label": "CD-01",
        "site": "NORTHRIDGE",
        "name": "west flare",
        "kind": ControlKind.ENCLOSED_FLARE,
        "capacity": 2_400.0,
        "installed_on": INSTALLED,
        "floor_degrees": 1_400.0,
    }
    fields.update(changes)
    return Control(**fields)  # type: ignore[arg-type]


def an_operation(**changes: object) -> Operation:
    fields: dict[str, object] = {
        "control": "CD-01",
        "at": read_moment("2025-06-11 09:00", ZONE),
        "running": True,
        "flow": 1_180.0,
        "methane": 49.2,
        "temperature": 1_512.0,
    }
    fields.update(changes)
    return Operation(**fields)  # type: ignore[arg-type]


def an_outage(**changes: object) -> Outage:
    fields: dict[str, object] = {
        "label": "OT-2025-004",
        "control": "CD-01",
        "site": "NORTHRIDGE",
        "started_at": read_moment("2025-06-11 09:00", ZONE),
        "reason": "blower bearing",
    }
    fields.update(changes)
    return Outage(**fields)  # type: ignore[arg-type]


def test_an_enclosed_flare_has_a_chamber_and_a_floor() -> None:
    control = a_control()
    assert control.kind.has_chamber
    floor = control.floor
    assert floor is not None
    assert floor.fahrenheit == pytest.approx(1_400.0)


def test_an_enclosed_flare_without_a_floor_is_refused() -> None:
    with pytest.raises(RuleError, match="minimum chamber"):
        a_control(floor_degrees=None)


def test_a_candlestick_has_no_chamber_to_measure() -> None:
    control = a_control(kind=ControlKind.CANDLESTICK, floor_degrees=None)
    assert not control.kind.has_chamber
    assert control.floor is None
    with pytest.raises(RuleError, match="no chamber"):
        a_control(kind=ControlKind.CANDLESTICK)


def test_an_engine_has_no_chamber_either() -> None:
    control = a_control(kind=ControlKind.ENGINE, floor_degrees=None)
    assert not control.kind.has_chamber


def test_a_control_device_has_a_capacity() -> None:
    with pytest.raises(RuleError, match="capacity"):
        a_control(capacity=0.0)
    assert str(a_control().rated_flow) == "2400.0 scfm"


def test_a_control_device_retires_once() -> None:
    control = a_control().retire(dt.date(2026, 3, 1))
    assert not control.is_live
    with pytest.raises(StateError):
        control.retire(dt.date(2026, 4, 1))
    with pytest.raises(OrderError):
        a_control(retired_on=dt.date(2010, 1, 1))


def test_an_operating_record_carries_its_offset() -> None:
    with pytest.raises(RuleError, match="offset"):
        an_operation(at=dt.datetime(2025, 6, 11, 9, 0))  # noqa: DTZ001


def test_the_methane_flow_is_what_gets_destroyed() -> None:
    assert an_operation().methane_flow == pytest.approx(580.56)


def test_an_operating_record_is_refused_off_the_scale() -> None:
    with pytest.raises(RuleError, match="backwards"):
        an_operation(flow=-1.0)
    with pytest.raises(RuleError, match="methane"):
        an_operation(methane=140.0)


def test_a_record_off_a_device_with_no_chamber_has_no_temperature() -> None:
    assert an_operation(temperature=None).chamber is None
    chamber = an_operation().chamber
    assert chamber is not None
    assert chamber.fahrenheit == pytest.approx(1_512.0)


def test_an_outage_needs_a_reason_and_an_offset() -> None:
    with pytest.raises(RuleError, match="reason"):
        an_outage(reason="  ")
    with pytest.raises(RuleError, match="offset"):
        an_outage(started_at=dt.datetime(2025, 6, 11, 9, 0))  # noqa: DTZ001


def test_an_open_outage_runs_up_to_the_moment_asked_about() -> None:
    outage = an_outage()
    assert outage.is_open
    assert outage.hours(read_moment("2025-06-11 15:00", ZONE)) == pytest.approx(6.0)


def test_an_outage_across_the_spring_change_is_an_hour_short() -> None:
    outage = an_outage(started_at=read_moment("2025-03-09 01:00", ZONE))
    assert outage.hours(read_moment("2025-03-09 04:00", ZONE)) == pytest.approx(2.0)


def test_an_outage_past_the_window_says_so() -> None:
    outage = an_outage()
    assert not outage.over_window(5, read_moment("2025-06-16 08:00", ZONE))
    assert outage.over_window(5, read_moment("2025-06-16 10:00", ZONE))


def test_an_outage_closes_once() -> None:
    outage = an_outage().close(read_moment("2025-06-12 15:00", ZONE), "bearing replaced")
    assert not outage.is_open
    assert outage.note == "bearing replaced"
    assert outage.days(read_moment("2025-06-20 09:00", ZONE)) == pytest.approx(1.25)
    with pytest.raises(StateError):
        outage.close(read_moment("2025-06-13 09:00", ZONE))


def test_an_outage_cannot_end_before_it_started() -> None:
    with pytest.raises(OrderError):
        an_outage(ended_at=read_moment("2025-06-10 09:00", ZONE))
    with pytest.raises(OrderError):
        an_outage().close(read_moment("2025-06-10 09:00", ZONE))


@pytest.mark.parametrize(
    ("moment", "start"),
    [
        ("2025-06-11 09:00", "2025-06-11 09:00"),
        ("2025-06-11 10:40", "2025-06-11 09:00"),
        ("2025-06-11 11:59", "2025-06-11 09:00"),
        ("2025-06-11 12:00", "2025-06-11 12:00"),
        ("2025-06-11 00:10", "2025-06-11 00:00"),
        ("2025-06-11 23:59", "2025-06-11 21:00"),
    ],
)
def test_a_block_is_pinned_to_the_clock_and_not_to_the_reading(moment: str, start: str) -> None:
    assert block_start(read_moment(moment, "UTC")) == read_moment(start, "UTC")

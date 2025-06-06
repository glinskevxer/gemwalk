"""Liquid levels worked out from the one number the crew can measure."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.device import Device, Kind
from gemwalk.model.liquids import Level, Pumpout, Sump, SumpKind

TAKEN = dt.date(2025, 6, 3)


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


def a_sump(**changes: object) -> Sump:
    fields: dict[str, object] = {
        "label": "CS-004",
        "site": "NORTHRIDGE",
        "station": "HD-01 low point",
        "kind": SumpKind.KNOCKOUT,
        "capacity": 550.0,
        "installed_on": dt.date(2019, 9, 3),
    }
    fields.update(changes)
    return Sump(**fields)  # type: ignore[arg-type]


def a_pumpout(**changes: object) -> Pumpout:
    fields: dict[str, object] = {
        "sump": "CS-004",
        "at": read_moment("2025-06-03 10:20", "America/Chicago"),
        "gallons": 410.0,
        "hauler": "Vestermark Vacuum",
        "bound_for": "leachate pretreatment",
    }
    fields.update(changes)
    return Pumpout(**fields)  # type: ignore[arg-type]


def test_a_dry_hole_has_nothing_standing_in_it() -> None:
    level = Level(device="VW-041", taken_on=TAKEN, depth=92.0)
    assert level.liquid_column(a_device()) == pytest.approx(0.0)
    assert level.is_dry(a_device())
    assert not level.is_flooded(a_device())


def test_water_below_the_screen_does_not_touch_it() -> None:
    level = Level(device="VW-041", taken_on=TAKEN, depth=88.0)
    device = a_device()
    assert level.liquid_column(device) == pytest.approx(4.0)
    assert level.submerged(device) == pytest.approx(0.0)
    assert level.is_dry(device)


def test_the_tape_reading_and_the_column_run_opposite_ways() -> None:
    device = a_device()
    shallow = Level(device="VW-041", taken_on=TAKEN, depth=30.0)
    deep = Level(device="VW-041", taken_on=TAKEN, depth=80.0)
    assert shallow.liquid_column(device) > deep.liquid_column(device)
    assert shallow.submerged(device) > deep.submerged(device)


def test_water_part_way_up_the_screen_covers_part_of_it() -> None:
    level = Level(device="VW-041", taken_on=TAKEN, depth=70.0)
    device = a_device()
    assert level.liquid_column(device) == pytest.approx(22.0)
    assert level.submerged(device) == pytest.approx(16.0)
    assert level.submerged_share(device) == pytest.approx(0.25)
    assert not level.is_flooded(device)


def test_water_over_the_top_of_the_screen_floods_the_well() -> None:
    level = Level(device="VW-041", taken_on=TAKEN, depth=14.0)
    device = a_device()
    assert level.is_flooded(device)
    assert level.submerged_share(device) == pytest.approx(1.0)
    assert level.above_screen(device) == pytest.approx(8.0)


def test_water_exactly_at_the_top_of_the_screen_floods_it() -> None:
    level = Level(device="VW-041", taken_on=TAKEN, depth=22.0)
    device = a_device()
    assert level.submerged(device) == pytest.approx(64.0)
    assert level.is_flooded(device)
    assert level.above_screen(device) == pytest.approx(0.0)


def test_a_shallow_well_reads_the_same_way() -> None:
    device = a_device(total_depth=40.0, screen_top=10.0, screen_bottom=38.0)
    level = Level(device="VW-041", taken_on=TAKEN, depth=5.0)
    assert level.submerged_share(device) == pytest.approx(1.0)


def test_a_depth_measured_upwards_is_refused() -> None:
    with pytest.raises(RuleError, match="downwards"):
        Level(device="VW-041", taken_on=TAKEN, depth=-4.0)


def test_a_sump_holds_something_and_retires_once() -> None:
    with pytest.raises(RuleError, match="holds something"):
        a_sump(capacity=0.0)
    retired = a_sump().retire(dt.date(2026, 2, 1))
    assert not retired.is_live
    with pytest.raises(StateError):
        retired.retire(dt.date(2026, 3, 1))
    with pytest.raises(OrderError):
        a_sump(retired_on=dt.date(2010, 1, 1))


def test_a_load_has_volume_a_hauler_and_a_destination() -> None:
    with pytest.raises(RuleError, match="volume"):
        a_pumpout(gallons=0.0)
    with pytest.raises(RuleError, match="somebody"):
        a_pumpout(hauler="  ")
    with pytest.raises(RuleError, match="somewhere"):
        a_pumpout(bound_for="")


def test_a_load_is_stamped_with_an_offset() -> None:
    with pytest.raises(RuleError, match="offset"):
        a_pumpout(at=dt.datetime(2025, 6, 3, 10, 20))  # noqa: DTZ001


def test_a_load_is_measured_against_what_the_sump_holds() -> None:
    assert a_pumpout().fills(a_sump()) == pytest.approx(410.0 / 550.0)

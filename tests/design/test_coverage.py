"""Whether an area has enough collection in it."""

from __future__ import annotations

import datetime as dt
import math

import pytest

from gemwalk.design import PACKING, Coverage, acres_for, coverage, wells_for
from gemwalk.errors import RuleError
from gemwalk.model.device import SQUARE_FEET_IN_AN_ACRE, Device, Kind
from gemwalk.model.landfill import Area


def an_area(**changes: object) -> Area:
    fields: dict[str, object] = {
        "label": "A-03",
        "site": "NORTHRIDGE",
        "name": "phase 3",
        "acres": 12.4,
        "first_waste": dt.date(2019, 4, 15),
    }
    fields.update(changes)
    return Area(**fields)  # type: ignore[arg-type]


def a_device(label: str, area: str = "A-03", influence: float = 100.0) -> Device:
    return Device(
        label=label,
        site="NORTHRIDGE",
        area=area,
        kind=Kind.VERTICAL,
        station="N 12+40",
        total_depth=92.0,
        screen_top=22.0,
        screen_bottom=86.0,
        drilled_on=dt.date(2021, 5, 12),
        influence=influence,
    )


def test_a_hundred_foot_radius_pulls_about_three_quarters_of_an_acre() -> None:
    assert acres_for(100.0) == pytest.approx(math.pi * 10_000 / SQUARE_FEET_IN_AN_ACRE)
    assert acres_for(100.0) == pytest.approx(0.721, abs=1e-3)


def test_a_radius_that_is_not_a_distance_is_refused() -> None:
    with pytest.raises(RuleError, match="real distance"):
        acres_for(0.0)
    with pytest.raises(RuleError, match="covers some ground"):
        wells_for(0.0, 100.0)


def test_a_device_knows_how_much_ground_it_pulls_on() -> None:
    assert a_device("VW-001").acres_pulled == pytest.approx(acres_for(100.0))
    assert a_device("VW-002", influence=200.0).acres_pulled == pytest.approx(acres_for(200.0))


def test_a_device_has_to_pull_on_some_ground() -> None:
    with pytest.raises(RuleError, match="some ground"):
        a_device("VW-001", influence=0.0)


def test_a_wider_radius_wants_fewer_wells() -> None:
    assert wells_for(12.4, 200.0) < wells_for(12.4, 100.0)


def test_the_well_count_rounds_up_because_you_cannot_drill_two_thirds() -> None:
    assert wells_for(1.0, 100.0) == 2
    assert wells_for(0.1, 100.0) == 1


def test_an_empty_area_is_short_by_everything() -> None:
    read = coverage(an_area(), [])
    assert read.devices == ()
    assert read.share == 0.0
    assert read.short_by == read.wanted
    assert not read.is_enough


def test_devices_in_another_area_do_not_count() -> None:
    read = coverage(an_area(), [a_device("VW-001", area="A-04")])
    assert read.devices == ()


def test_an_area_with_its_full_complement_is_enough() -> None:
    wanted = wells_for(12.4, 100.0)
    devices = [a_device(f"VW-{n:03d}") for n in range(wanted)]
    read = coverage(an_area(), devices)
    assert read.is_enough
    assert read.short_by == 0


def test_the_share_never_goes_over_all_of_it() -> None:
    devices = [a_device(f"VW-{n:03d}", influence=300.0) for n in range(20)]
    assert coverage(an_area(), devices).share == 1.0


def test_the_packing_factor_takes_the_overlap_off() -> None:
    devices = [a_device("VW-001")]
    tight = coverage(an_area(), devices, packing=1.0)
    loose = coverage(an_area(), devices, packing=PACKING)
    assert loose.covered < tight.covered


def test_an_area_with_a_wider_design_radius_wants_fewer() -> None:
    narrow = coverage(an_area(), [])
    wide = coverage(an_area(target_radius=200.0), [])
    assert wide.wanted < narrow.wanted


def test_a_design_radius_that_is_not_a_distance_is_refused() -> None:
    with pytest.raises(RuleError, match="real distance"):
        an_area(target_radius=0.0)


def test_a_coverage_prints_the_sentence_the_desk_reads() -> None:
    read = coverage(an_area(), [a_device("VW-001")])
    assert "A-03: 1 of" in str(read)
    assert "12.4 acres" in str(read)


def test_a_coverage_carries_the_radius_it_was_read_against() -> None:
    assert coverage(an_area(target_radius=150.0), []).radius == pytest.approx(150.0)


def test_a_coverage_of_no_acres_reads_as_nothing_covered() -> None:
    """An area cannot have no acres, but the reading is defined anyway."""
    assert Coverage("A-03", 0.0, 100.0, (), 0.0, 1).share == 0.0

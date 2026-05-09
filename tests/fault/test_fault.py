"""What is wrong with the cover, and how long it gets."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.fault import BIG_SQUARE_FEET, ORDINARY_DAYS, URGENT_DAYS, Damage, Fault

FOUND = dt.date(2025, 5, 13)


def a_fault(**changes: object) -> Fault:
    fields: dict[str, object] = {
        "label": "CF-2025-001",
        "site": "NORTHRIDGE",
        "area": "A-03",
        "kind": Damage.SETTLEMENT,
        "station": "grid 14-J",
        "extent": 120.0,
        "found_on": FOUND,
        "found_by": "T. Wierzbicki",
    }
    fields.update(changes)
    return Fault(**fields)  # type: ignore[arg-type]


def test_a_fault_covers_some_ground_and_somebody_found_it() -> None:
    with pytest.raises(RuleError, match="some ground"):
        a_fault(extent=0.0)
    with pytest.raises(RuleError, match="somebody found it"):
        a_fault(found_by="  ")


def test_settlement_over_a_small_patch_gets_the_long_window() -> None:
    fault = a_fault()
    assert not fault.is_urgent
    assert fault.window == ORDINARY_DAYS
    assert fault.due == dt.date(2025, 6, 12)


def test_exposed_refuse_is_urgent_however_small() -> None:
    fault = a_fault(kind=Damage.EXPOSED, extent=2.0)
    assert fault.is_urgent
    assert fault.window == URGENT_DAYS
    assert fault.due == dt.date(2025, 5, 23)


def test_a_slope_failure_and_a_crack_are_urgent_too() -> None:
    assert a_fault(kind=Damage.SLIDE, extent=1.0).is_urgent
    assert a_fault(kind=Damage.CRACK, extent=1.0).is_urgent
    assert not a_fault(kind=Damage.PONDING, extent=1.0).is_urgent


def test_anything_big_enough_is_urgent_whatever_it_is() -> None:
    assert a_fault(extent=BIG_SQUARE_FEET).is_big
    assert a_fault(extent=BIG_SQUARE_FEET).is_urgent
    assert not a_fault(extent=BIG_SQUARE_FEET - 1).is_urgent


def test_a_fault_runs_late_the_day_after_its_window() -> None:
    fault = a_fault()
    assert fault.days_left(dt.date(2025, 6, 10)) == 2
    assert not fault.is_late(dt.date(2025, 6, 12))
    assert fault.is_late(dt.date(2025, 6, 13))


def test_a_fixed_fault_has_no_window_left() -> None:
    fault = a_fault().fix(dt.date(2025, 5, 20), "regraded and seeded")
    assert not fault.is_open
    assert fault.due is None
    assert fault.days_left(dt.date(2026, 1, 1)) is None
    assert not fault.is_late(dt.date(2026, 1, 1))
    assert fault.note == "regraded and seeded"


def test_a_fault_cannot_be_fixed_twice_or_before_it_was_found() -> None:
    fixed = a_fault().fix(dt.date(2025, 5, 20))
    with pytest.raises(StateError):
        fixed.fix(dt.date(2025, 5, 21))
    with pytest.raises(OrderError):
        a_fault().fix(dt.date(2025, 5, 1))
    with pytest.raises(OrderError):
        a_fault(fixed_on=dt.date(2025, 5, 1))


def test_an_open_fault_prints_its_deadline() -> None:
    said = str(a_fault())
    assert "settlement at grid 14-J" in said
    assert "due 2025-06-12" in said


def test_a_fixed_fault_prints_the_day_it_was_fixed() -> None:
    said = str(a_fault().fix(dt.date(2025, 5, 20)))
    assert "fixed 2025-05-20" in said


def test_every_kind_of_damage_prints_the_words_the_crew_uses() -> None:
    assert str(Damage.EXPOSED) == "exposed refuse"
    assert len({str(kind) for kind in Damage}) == len(Damage)

"""One spot on the cover, and the windows it moves through."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.landfill import Cover
from gemwalk.model.surface import Hit, Step
from gemwalk.rules import XXX

FOUND = dt.date(2025, 5, 13)


def a_hit(**changes: object) -> Hit:
    fields: dict[str, object] = {
        "label": "SH-2025Q2-003",
        "walk": "SW-2025Q2-01",
        "site": "NORTHRIDGE",
        "area": "A-03",
        "station": "grid 14-J",
        "reading": 720.0,
        "cover": Cover.INTERMEDIATE,
        "found_on": FOUND,
    }
    fields.update(changes)
    return Hit(**fields)  # type: ignore[arg-type]


def test_a_new_hit_is_waiting_on_a_repair() -> None:
    hit = a_hit()
    assert hit.step is Step.REPAIR
    assert hit.attempt == 1
    assert hit.is_open


def test_the_repair_window_runs_from_the_day_it_was_found() -> None:
    assert a_hit().due(XXX) == dt.date(2025, 5, 23)


def test_the_remonitor_window_runs_from_the_day_of_the_repair() -> None:
    early = a_hit().repair(dt.date(2025, 5, 14))
    late = a_hit().repair(dt.date(2025, 5, 22))
    assert early.due(XXX) == dt.date(2025, 5, 24)
    assert late.due(XXX) == dt.date(2025, 6, 1)


def test_the_expansion_window_goes_back_to_the_day_it_was_found() -> None:
    hit = a_hit().repair(dt.date(2025, 5, 22))
    hit = hit.still_over(XXX, dt.date(2025, 5, 30))
    hit = hit.repair(dt.date(2025, 6, 3))
    hit = hit.still_over(XXX, dt.date(2025, 6, 10))
    assert hit.step is Step.EXPANSION
    assert hit.due(XXX) == dt.date(2025, 9, 10)


def test_a_second_attempt_starts_the_repair_window_again() -> None:
    hit = a_hit().repair(dt.date(2025, 5, 14)).still_over(XXX, dt.date(2025, 5, 20))
    assert hit.step is Step.REPAIR
    assert hit.attempt == 2
    assert hit.repaired_on is None
    assert hit.due(XXX) == dt.date(2025, 5, 23)


def test_a_clean_remonitor_closes_the_spot() -> None:
    hit = a_hit().repair(dt.date(2025, 5, 14)).clear(dt.date(2025, 5, 20))
    assert not hit.is_open
    assert hit.closed_on == dt.date(2025, 5, 20)
    assert hit.due(XXX) is None
    assert hit.days_left(XXX, dt.date(2025, 6, 1)) is None


def test_a_spot_waiting_on_a_repair_cannot_be_cleared() -> None:
    with pytest.raises(StateError, match="repair"):
        a_hit().clear(dt.date(2025, 5, 20))


def test_a_spot_waiting_on_a_remonitor_cannot_be_repaired_again() -> None:
    hit = a_hit().repair(dt.date(2025, 5, 14))
    with pytest.raises(StateError):
        hit.repair(dt.date(2025, 5, 16))


def test_a_repair_before_the_spot_was_found_is_refused() -> None:
    with pytest.raises(OrderError):
        a_hit().repair(dt.date(2025, 5, 1))
    with pytest.raises(OrderError):
        a_hit(repaired_on=dt.date(2025, 5, 1))


def test_a_spot_runs_late_the_day_after_its_window_shuts() -> None:
    hit = a_hit()
    assert hit.days_left(XXX, dt.date(2025, 5, 20)) == 3
    assert not hit.is_late(XXX, dt.date(2025, 5, 23))
    assert hit.is_late(XXX, dt.date(2025, 5, 24))


def test_a_remonitor_that_never_happened_leaves_the_repair_deadline() -> None:
    hit = a_hit(step=Step.REMONITOR)
    assert hit.due(XXX) == dt.date(2025, 5, 23)


def test_a_spot_can_be_closed_out_from_anywhere() -> None:
    hit = a_hit().close(dt.date(2025, 6, 1), "area taken out of service")
    assert not hit.is_open
    assert hit.note == "area taken out of service"
    with pytest.raises(StateError):
        hit.close(dt.date(2025, 6, 2))


def test_a_reading_and_an_attempt_have_to_be_real() -> None:
    with pytest.raises(RuleError, match="negative"):
        a_hit(reading=-1.0)
    with pytest.raises(RuleError, match="attempt one"):
        a_hit(attempt=0)


def test_the_reading_reads_back_in_its_own_unit() -> None:
    assert str(a_hit().surface_reading) == "720 ppmv"

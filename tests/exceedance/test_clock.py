"""The clock one bad reading starts, and what a recheck does to it."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.exceedance import Exceedance, Stage
from gemwalk.rules import WWW, XXX, Finding

OPENED = dt.date(2025, 4, 8)


def an_exceedance(**changes: object) -> Exceedance:
    fields: dict[str, object] = {
        "label": "EX-2025-001",
        "site": "NORTHRIDGE",
        "device": "VW-041",
        "kind": Finding.TEMPERATURE,
        "opened_on": OPENED,
        "reading": 91,
        "value": 138.0,
        "limit_value": 131.0,
    }
    fields.update(changes)
    return Exceedance(**fields)  # type: ignore[arg-type]


def test_a_new_exceedance_starts_at_the_first_stage() -> None:
    found = an_exceedance()
    assert found.stage is Stage.CORRECT
    assert found.is_open


def test_the_first_window_is_five_days_off_the_reading() -> None:
    assert an_exceedance().due(XXX) == dt.date(2025, 4, 13)


def test_the_second_window_is_fifteen_days_off_the_same_reading() -> None:
    found = an_exceedance().escalate()
    assert found.stage is Stage.ACTION
    assert found.due(XXX) == dt.date(2025, 4, 23)


def test_the_third_window_is_a_hundred_and_twenty_days_off_the_same_reading() -> None:
    found = an_exceedance().escalate().escalate()
    assert found.stage is Stage.EXPANSION
    assert found.due(XXX) == dt.date(2025, 8, 6)


def test_escalating_past_the_last_stage_is_refused() -> None:
    found = an_exceedance().escalate().escalate()
    with pytest.raises(StateError, match="expansion"):
        found.escalate()


def test_the_days_left_run_negative_once_the_window_is_gone() -> None:
    found = an_exceedance()
    assert found.days_left(XXX, dt.date(2025, 4, 10)) == 3
    assert found.days_left(XXX, dt.date(2025, 4, 16)) == -3
    assert not found.is_late(XXX, dt.date(2025, 4, 13))
    assert found.is_late(XXX, dt.date(2025, 4, 14))


def test_a_closed_exceedance_has_no_window_left() -> None:
    found = an_exceedance().close(dt.date(2025, 4, 12))
    assert not found.is_open
    assert found.due(XXX) is None
    assert found.days_left(XXX, dt.date(2025, 4, 20)) is None
    assert not found.is_late(XXX, dt.date(2025, 6, 1))


def test_a_closed_exceedance_cannot_be_closed_again_or_escalated() -> None:
    found = an_exceedance().close(dt.date(2025, 4, 12))
    with pytest.raises(StateError):
        found.close(dt.date(2025, 4, 14))
    with pytest.raises(StateError):
        found.escalate()


def test_an_exceedance_cannot_close_before_it_opened() -> None:
    with pytest.raises(OrderError):
        an_exceedance().close(dt.date(2025, 4, 1))
    with pytest.raises(OrderError):
        an_exceedance(closed_on=dt.date(2025, 4, 1), stage=Stage.CLOSED)


def test_a_closed_date_without_the_closed_stage_is_refused() -> None:
    with pytest.raises(RuleError):
        an_exceedance(closed_on=dt.date(2025, 4, 12))


def test_the_calendar_says_which_stage_a_day_belongs_to() -> None:
    found = an_exceedance()
    assert found.stage_for(XXX, dt.date(2025, 4, 13)) is Stage.CORRECT
    assert found.stage_for(XXX, dt.date(2025, 4, 14)) is Stage.ACTION
    assert found.stage_for(XXX, dt.date(2025, 4, 23)) is Stage.ACTION
    assert found.stage_for(XXX, dt.date(2025, 4, 24)) is Stage.EXPANSION


def test_a_closed_exceedance_belongs_to_no_stage() -> None:
    found = an_exceedance().close(dt.date(2025, 4, 12))
    assert found.stage_for(XXX, dt.date(2025, 6, 1)) is Stage.CLOSED


def test_a_record_left_behind_by_the_calendar_says_so() -> None:
    found = an_exceedance()
    assert not found.behind(XXX, dt.date(2025, 4, 13))
    assert found.behind(XXX, dt.date(2025, 4, 20))
    assert not found.escalate().behind(XXX, dt.date(2025, 4, 20))


def test_a_closed_exceedance_is_never_behind() -> None:
    found = an_exceedance().close(dt.date(2025, 4, 12))
    assert not found.behind(XXX, dt.date(2026, 1, 1))


def test_the_windows_do_not_move_when_the_standard_does() -> None:
    found = an_exceedance()
    assert found.due(WWW) == found.due(XXX)


def test_a_recheck_does_not_restart_the_clock() -> None:
    found = an_exceedance()
    same = found.escalate()
    assert same.opened_on == OPENED
    assert same.due(XXX) == dt.date(2025, 4, 23)

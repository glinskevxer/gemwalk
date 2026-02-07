"""Watching a flare for smoke."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import RuleError
from gemwalk.model.observation import ALLOWED_MINUTES, WINDOW_MINUTES, Observation

ZONE = "America/Chicago"


def a_watch(**changes: object) -> Observation:
    fields: dict[str, object] = {
        "label": "VE-2025-001",
        "control": "CD-01",
        "site": "NORTHRIDGE",
        "started_at": read_moment("2025-06-11 09:00", ZONE),
        "watched": 120.0,
        "visible": 2.0,
        "observer": "R. Bellingham",
    }
    fields.update(changes)
    return Observation(**fields)  # type: ignore[arg-type]


def test_the_rule_is_five_minutes_in_two_hours() -> None:
    assert ALLOWED_MINUTES == 5.0
    assert WINDOW_MINUTES == 120.0


def test_a_clean_two_hour_watch_is_inside() -> None:
    watch = a_watch()
    assert watch.is_long_enough
    assert not watch.over
    assert "inside" in str(watch)


def test_six_minutes_in_two_hours_is_over() -> None:
    watch = a_watch(visible=6.0)
    assert watch.over
    assert "over the 5 minute limit" in str(watch)


def test_exactly_five_minutes_is_not_over() -> None:
    assert not a_watch(visible=5.0).over


def test_a_short_watch_cannot_find_a_violation() -> None:
    watch = a_watch(watched=20.0, visible=4.0)
    assert not watch.is_long_enough
    assert not watch.over


def test_a_short_watch_on_course_to_be_over_says_to_go_back() -> None:
    watch = a_watch(watched=20.0, visible=4.0)
    assert watch.worth_another_look
    assert watch.in_two_hours == pytest.approx(24.0)
    assert "go back and watch it properly" in str(watch)


def test_a_short_clean_watch_says_nothing() -> None:
    watch = a_watch(watched=20.0, visible=0.0)
    assert not watch.worth_another_look
    assert "says nothing" in str(watch)


def test_a_long_watch_is_never_worth_another_look() -> None:
    assert not a_watch(visible=6.0).worth_another_look


def test_the_watch_knows_when_it_ended() -> None:
    watch = a_watch()
    assert watch.finished_at == read_moment("2025-06-11 11:00", ZONE)


def test_more_smoke_than_watching_is_refused() -> None:
    with pytest.raises(RuleError, match="minutes of smoke in a"):
        a_watch(watched=20.0, visible=30.0)


def test_a_watch_of_no_minutes_is_refused() -> None:
    with pytest.raises(RuleError, match="covers some minutes"):
        a_watch(watched=0.0)


def test_negative_smoke_is_refused() -> None:
    with pytest.raises(RuleError, match="negative minutes"):
        a_watch(visible=-1.0)


def test_somebody_has_to_have_stood_there() -> None:
    with pytest.raises(RuleError, match="stood there"):
        a_watch(observer="  ")


def test_a_watch_is_stamped_with_an_offset() -> None:
    with pytest.raises(RuleError, match="offset"):
        a_watch(started_at=dt.datetime(2025, 6, 11, 9, 0))  # noqa: DTZ001


def test_the_rate_is_the_share_of_the_watch_that_smoked() -> None:
    assert a_watch(visible=12.0).rate == pytest.approx(0.1)

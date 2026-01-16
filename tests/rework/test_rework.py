"""Raising a well, and what it does to what the well is."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.device import Device, Kind
from gemwalk.model.rework import Job, Rework
from gemwalk.rules import XXX

STARTED = dt.date(2025, 3, 1)


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


def a_job(kind: Rework = Rework.RAISE) -> Job:
    return Job.opened("RW-001", a_device(), kind, STARTED)


def test_a_job_takes_the_construction_as_it_stands() -> None:
    job = a_job()
    assert job.before_depth == pytest.approx(92.0)
    assert job.before_top == pytest.approx(22.0)
    assert job.is_open


def test_an_open_job_has_not_raised_anything_yet() -> None:
    assert a_job().raised_by == pytest.approx(0.0)


def test_a_finished_raise_says_how_much_taller_the_well_is() -> None:
    finished = a_job().finish(
        dt.date(2025, 3, 20), depth=122.0, screen_top=52.0, screen_bottom=116.0
    )
    assert finished.raised_by == pytest.approx(30.0)
    assert not finished.is_open


def test_the_device_comes_back_measured_from_the_new_top_of_casing() -> None:
    finished = a_job().finish(
        dt.date(2025, 3, 20), depth=122.0, screen_top=52.0, screen_bottom=116.0
    )
    after = finished.apply(a_device())
    assert after.total_depth == pytest.approx(122.0)
    assert after.screen_top == pytest.approx(52.0)
    assert after.screen_length == pytest.approx(64.0)


def test_a_repair_leaves_the_device_the_shape_it_was() -> None:
    finished = a_job(Rework.REPAIR).finish(dt.date(2025, 3, 5))
    assert finished.apply(a_device()) == a_device()
    assert not Rework.REPAIR.changes_construction


def test_a_finished_raise_has_to_be_measured() -> None:
    with pytest.raises(RuleError, match="measured afterwards"):
        a_job().finish(dt.date(2025, 3, 20))


def test_a_job_that_is_measured_and_not_finished_is_refused() -> None:
    with pytest.raises(RuleError, match="when the work is finished"):
        Job(
            label="RW-001",
            device="VW-041",
            site="NORTHRIDGE",
            kind=Rework.RAISE,
            started_on=STARTED,
            before_depth=92.0,
            before_top=22.0,
            before_bottom=86.0,
            after_depth=122.0,
        )


def test_a_job_cannot_finish_before_it_started() -> None:
    with pytest.raises(OrderError):
        a_job().finish(dt.date(2025, 2, 1), depth=122.0, screen_top=52.0, screen_bottom=116.0)


def test_a_finished_job_cannot_finish_again() -> None:
    finished = a_job(Rework.REPAIR).finish(dt.date(2025, 3, 5))
    with pytest.raises(StateError):
        finished.finish(dt.date(2025, 3, 6))


def test_an_open_job_cannot_be_applied_to_the_device() -> None:
    with pytest.raises(StateError):
        a_job().apply(a_device())


def test_a_job_counts_its_days_up_to_the_day_asked_about() -> None:
    job = a_job()
    assert job.days(dt.date(2025, 3, 20)) == 19
    finished = job.finish(dt.date(2025, 3, 20), depth=122.0, screen_top=52.0, screen_bottom=116.0)
    assert finished.days(dt.date(2025, 6, 1)) == 19


def test_a_raise_past_the_window_says_so() -> None:
    job = a_job()
    assert not job.over_window(XXX, dt.date(2025, 4, 30))
    assert job.over_window(XXX, dt.date(2025, 5, 1))


def test_a_finished_raise_is_never_past_its_window() -> None:
    finished = a_job().finish(
        dt.date(2025, 3, 20), depth=122.0, screen_top=52.0, screen_bottom=116.0
    )
    assert not finished.over_window(XXX, dt.date(2026, 1, 1))


def test_a_kind_prints_the_word_the_ticket_uses() -> None:
    assert str(Rework.REDRILL) == "redrill"
    assert Rework.REDRILL.changes_construction

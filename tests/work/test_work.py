"""One job at one place, and the date it carries."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.work import Job, Standing, WorkOrder

RAISED = dt.date(2025, 4, 8)


def an_order(**changes: object) -> WorkOrder:
    fields: dict[str, object] = {
        "label": "WO-2025-0142",
        "site": "NORTHRIDGE",
        "job": Job.VALVE,
        "target": "VW-041",
        "raised_on": RAISED,
        "due_on": dt.date(2025, 4, 13),
    }
    fields.update(changes)
    return WorkOrder(**fields)  # type: ignore[arg-type]


def test_a_new_order_is_open_and_carries_its_window() -> None:
    order = an_order()
    assert order.is_open
    assert order.days_allowed == 5
    assert order.days_left(dt.date(2025, 4, 10)) == 3


def test_an_order_cannot_be_due_before_it_was_raised() -> None:
    with pytest.raises(OrderError):
        an_order(due_on=dt.date(2025, 4, 1))


def test_an_order_names_a_place() -> None:
    with pytest.raises(RuleError, match="names a place"):
        an_order(target="   ")


def test_an_order_runs_late_the_day_after_its_date() -> None:
    order = an_order()
    assert not order.is_late(dt.date(2025, 4, 13))
    assert order.is_late(dt.date(2025, 4, 14))
    assert order.days_left(dt.date(2025, 4, 16)) == -3


def test_assigning_puts_a_crew_on_it() -> None:
    order = an_order().assign("north crew", dt.date(2025, 4, 9))
    assert order.state is Standing.ASSIGNED
    assert order.crew == "north crew"


def test_an_assigned_order_has_to_have_a_crew() -> None:
    with pytest.raises(RuleError, match="crew"):
        an_order().assign("  ", dt.date(2025, 4, 9))
    with pytest.raises(RuleError, match="crew"):
        an_order(state=Standing.ASSIGNED)


def test_an_order_cannot_be_assigned_before_it_was_raised() -> None:
    with pytest.raises(OrderError):
        an_order().assign("north crew", dt.date(2025, 4, 1))


def test_finishing_closes_the_order() -> None:
    order = an_order().assign("north crew", dt.date(2025, 4, 9))
    done = order.finish(dt.date(2025, 4, 11), "valve turned in a half")
    assert not done.is_open
    assert done.done_on == dt.date(2025, 4, 11)
    assert done.days_left(dt.date(2025, 4, 20)) is None
    assert not done.is_late(dt.date(2025, 4, 20))


def test_an_order_finished_after_its_date_says_so() -> None:
    late = an_order().finish(dt.date(2025, 4, 20))
    assert late.was_late()
    assert not an_order().finish(dt.date(2025, 4, 11)).was_late()
    assert not an_order().was_late()


def test_a_closed_order_takes_nothing_more() -> None:
    done = an_order().finish(dt.date(2025, 4, 11))
    with pytest.raises(StateError):
        done.finish(dt.date(2025, 4, 12))
    with pytest.raises(StateError):
        done.assign("north crew", dt.date(2025, 4, 12))
    with pytest.raises(StateError):
        done.cancel(dt.date(2025, 4, 12), "no longer needed")


def test_a_cancelled_order_says_why() -> None:
    with pytest.raises(RuleError, match="says why"):
        an_order().cancel(dt.date(2025, 4, 11), "  ")
    off = an_order().cancel(dt.date(2025, 4, 11), "well abandoned instead")
    assert off.state is Standing.CANCELLED
    assert off.note == "well abandoned instead"


def test_a_finish_date_on_an_open_order_is_refused() -> None:
    with pytest.raises(RuleError, match="closed"):
        an_order(done_on=dt.date(2025, 4, 11))


def test_an_order_cannot_finish_before_it_was_raised() -> None:
    with pytest.raises(OrderError):
        an_order().finish(dt.date(2025, 4, 1))


def test_a_job_prints_as_the_line_on_the_ticket() -> None:
    assert str(Job.DEWATER) == "dewater the well"
    assert str(Standing.ASSIGNED) == "assigned"

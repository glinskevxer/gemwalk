"""The work orders the field crew is actually handed.

A compliance record says a wellhead is over a limit. It does not say what
anybody is meant to do about it, and it does not go in a truck. A work order
does both: it names one job at one place, carries the record it came out of,
and has a date on it that is either the regulation's or the desk's.

The due date is the part worth being careful with. An order raised off a
compliance clock inherits that clock's deadline, so moving the order does not
move the deadline and closing the order does not close the record. An order
raised because somebody noticed something has whatever date the desk gave it.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import Enum

from gemwalk.errors import OrderError, RuleError, StateError


class Job(Enum):
    """What the crew is being sent to do."""

    VALVE = "adjust the valve"
    WELLHEAD = "repair the wellhead"
    RAISE = "raise the well"
    DEWATER = "dewater the well"
    COVER = "repair the cover"
    PIPE = "repair the pipe"
    SUMP = "pump the sump"
    DRILL = "drill a new device"
    OTHER = "other"

    def __str__(self) -> str:
        return self.value


class Standing(Enum):
    """Where a work order is."""

    OPEN = "open"
    ASSIGNED = "assigned"
    DONE = "done"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        return self.value


CLOSED = (Standing.DONE, Standing.CANCELLED)


@dataclass(frozen=True)
class WorkOrder:
    """One job at one place, with the record it came out of."""

    label: str
    site: str
    job: Job
    target: str
    raised_on: dt.date
    due_on: dt.date
    state: Standing = Standing.OPEN
    because: str | None = None
    crew: str = ""
    done_on: dt.date | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if not self.target.strip():
            raise RuleError("work order", "an order names a place")
        if self.done_on is not None and self.state not in CLOSED:
            raise RuleError("work order", "an order with a finish date is closed")
        if self.state is Standing.ASSIGNED and not self.crew.strip():
            raise RuleError("work order", "an assigned order has a crew on it")

    @property
    def is_open(self) -> bool:
        """True while the job still has to be done."""
        return self.state not in CLOSED

    @property
    def days_allowed(self) -> int:
        """How many days the order was given when it was raised.

        This can be negative, and a negative one is not a mistake. An order
        raised off a record whose hundred and twenty day window shut in May is
        written in June with a date in May, because the date belongs to the
        record and writing the ticket later does not move it.
        """
        return (self.due_on - self.raised_on).days

    @property
    def born_late(self) -> bool:
        """True when the order was already past its date the day it was written."""
        return self.due_on < self.raised_on

    def days_left(self, on: dt.date) -> int | None:
        """How many days are left, negative when late, nothing when closed."""
        return None if not self.is_open else (self.due_on - on).days

    def is_late(self, on: dt.date) -> bool:
        """True when an open order has gone past its date."""
        return self.is_open and on > self.due_on

    def assign(self, crew: str, on: dt.date) -> WorkOrder:
        """Hand the order to a crew."""
        if not self.is_open:
            raise StateError(self.label, str(self.state), "open")
        if not crew.strip():
            raise RuleError("work order", "an assigned order has a crew on it")
        if on < self.raised_on:
            raise OrderError(self.label, str(self.raised_on), str(on))
        return replace(self, state=Standing.ASSIGNED, crew=crew)

    def finish(self, on: dt.date, note: str = "") -> WorkOrder:
        """Record the job as done."""
        if not self.is_open:
            raise StateError(self.label, str(self.state), "open")
        if on < self.raised_on:
            raise OrderError(self.label, str(self.raised_on), str(on))
        return replace(self, state=Standing.DONE, done_on=on, note=note or self.note)

    def cancel(self, on: dt.date, why: str) -> WorkOrder:
        """Call the job off, with a reason."""
        if not self.is_open:
            raise StateError(self.label, str(self.state), "open")
        if not why.strip():
            raise RuleError("work order", "a cancelled order says why")
        return replace(self, state=Standing.CANCELLED, done_on=on, note=why)

    def was_late(self) -> bool:
        """True when the order was finished after the date it carried."""
        return self.done_on is not None and self.done_on > self.due_on


__all__ = ["CLOSED", "Job", "Standing", "WorkOrder"]

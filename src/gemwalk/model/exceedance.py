"""The clock a bad wellhead reading starts, and how it is walked.

One reading over one limit opens one exceedance, and it stays open until a
later reading of the same wellhead comes back under the limit. What changes
while it is open is how long the operator has left and what they are expected
to have done.

The three stages run off the day of the first bad reading and not off each
other. The first is five days: turn the valve, wait, read it again. The second
is fifteen: do something to the well itself. The third is a hundred and twenty:
put more collection in the ground. A recheck that comes back clear at any stage
closes the exceedance where it stands, and a recheck that comes back still over
does not restart anything, because the windows were never counted from it.

That last part is the piece people get wrong. A wellhead read hot on the eighth,
rechecked hot on the twelfth and rechecked hot again on the twentieth is not
three exceedances and it is not five days from the twentieth. It is one
exceedance with eight days left.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import Enum

from gemwalk.clock import deadline, is_overdue
from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.rules import Finding, Standard


class Stage(Enum):
    """How far along the exceedance is."""

    CORRECT = "correct"
    ACTION = "action"
    EXPANSION = "expansion"
    CLOSED = "closed"

    def __str__(self) -> str:
        return self.value


ORDER = (Stage.CORRECT, Stage.ACTION, Stage.EXPANSION)


@dataclass(frozen=True)
class Recheck:
    """One later reading of a wellhead that has an exceedance open on it."""

    exceedance: str
    taken_on: dt.date
    value: float
    clear: bool
    stage: Stage
    reading: int | None = None
    note: str = ""
    id: int = 0


@dataclass(frozen=True)
class Exceedance:
    """One wellhead over one limit, with the clock it started."""

    label: str
    site: str
    device: str
    kind: Finding
    opened_on: dt.date
    reading: int
    value: float
    limit_value: float
    stage: Stage = Stage.CORRECT
    closed_on: dt.date | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.closed_on is not None and self.closed_on < self.opened_on:
            raise OrderError("exceedance", str(self.opened_on), str(self.closed_on))
        if self.closed_on is not None and self.stage is not Stage.CLOSED:
            raise RuleError("exceedance", "a closed exceedance is at the closed stage")

    @property
    def is_open(self) -> bool:
        """True while the wellhead is still over the limit."""
        return self.stage is not Stage.CLOSED

    def window(self, standard: Standard) -> int:
        """How many days the current stage allows, counted from the first reading."""
        windows = standard.windows
        if self.stage is Stage.CORRECT:
            return windows.correct
        if self.stage is Stage.ACTION:
            return windows.action
        if self.stage is Stage.EXPANSION:
            return windows.expand
        return 0

    def due(self, standard: Standard) -> dt.date | None:
        """The last day the current stage is still open, or nothing when closed."""
        if not self.is_open:
            return None
        return deadline(self.opened_on, self.window(standard))

    def days_left(self, standard: Standard, on: dt.date) -> int | None:
        """How many days are left in the current stage, negative when past it."""
        due = self.due(standard)
        return None if due is None else (due - on).days

    def is_late(self, standard: Standard, on: dt.date) -> bool:
        """True when the current stage's window has already run out."""
        due = self.due(standard)
        return due is not None and is_overdue(due, on)

    def escalate(self) -> Exceedance:
        """Move the exceedance onto the next stage."""
        if not self.is_open:
            raise StateError(self.label, "closed", "open")
        if self.stage is Stage.EXPANSION:
            raise StateError(self.label, "at expansion", "earlier in the walk")
        return replace(self, stage=ORDER[ORDER.index(self.stage) + 1])

    def close(self, on: dt.date, note: str = "") -> Exceedance:
        """Close the exceedance because a later reading came back under."""
        if not self.is_open:
            raise StateError(self.label, "closed", "open")
        if on < self.opened_on:
            raise OrderError(self.label, str(self.opened_on), str(on))
        return replace(self, stage=Stage.CLOSED, closed_on=on, note=note or self.note)

    def stage_for(self, standard: Standard, on: dt.date) -> Stage:
        """The stage the calendar says this exceedance should be at on *on*.

        The stage on the record is what the operator has done. This is what the
        regulation expects, and the two only differ when something was missed.
        """
        if not self.is_open:
            return Stage.CLOSED
        windows = standard.windows
        if (on - self.opened_on).days <= windows.correct:
            return Stage.CORRECT
        if (on - self.opened_on).days <= windows.action:
            return Stage.ACTION
        return Stage.EXPANSION

    def behind(self, standard: Standard, on: dt.date) -> bool:
        """True when the calendar has moved past the stage on the record."""
        if not self.is_open:
            return False
        expected = self.stage_for(standard, on)
        return ORDER.index(expected) > ORDER.index(self.stage)


__all__ = ["ORDER", "Exceedance", "Recheck", "Stage"]

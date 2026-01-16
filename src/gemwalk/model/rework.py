"""Raising a well, deepening it, and redrilling it altogether.

An area keeps being filled after its wells go in, so a well that was at grade
in 2021 is thirty feet under the working face by 2024. It has to be raised:
taken off the run, extended upward with new pipe and a new seal, and put back.
While it is off the run it is not being read, which is why the window it has to
come back inside exists at all.

A raise changes what the device *is*. The total depth measured from the new top
of casing is larger, and the screen depths measured from the same new datum move
with it. Recording the construction before and after is the only way a reading
from 2022 stays interpretable, because a tape drop of forty feet means something
different either side of a raise.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import Enum

from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.device import Device
from gemwalk.rules import Standard


class Rework(Enum):
    """What was done to the device."""

    RAISE = "raise"
    DEEPEN = "deepen"
    REDRILL = "redrill"
    REPAIR = "repair"

    def __str__(self) -> str:
        return self.value

    @property
    def changes_construction(self) -> bool:
        """True when the job leaves the device a different shape."""
        return self is not Rework.REPAIR


@dataclass(frozen=True)
class Job:
    """One piece of work on one device, with the construction either side."""

    label: str
    device: str
    site: str
    kind: Rework
    started_on: dt.date
    before_depth: float
    before_top: float
    before_bottom: float
    finished_on: dt.date | None = None
    after_depth: float | None = None
    after_top: float | None = None
    after_bottom: float | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.finished_on is not None and self.finished_on < self.started_on:
            raise OrderError("rework", str(self.started_on), str(self.finished_on))
        finished = self.finished_on is not None
        measured = self.after_depth is not None
        if finished and self.kind.changes_construction and not measured:
            raise RuleError("rework", f"a finished {self.kind} is measured afterwards")
        if measured and not finished:
            raise RuleError("rework", "a device is measured when the work is finished")

    @property
    def is_open(self) -> bool:
        """True while the work is still going on."""
        return self.finished_on is None

    def days(self, on: dt.date) -> int:
        """How many days the work has taken so far."""
        return ((self.finished_on or on) - self.started_on).days

    def over_window(self, standard: Standard, on: dt.date) -> bool:
        """True when the work has run past the window a raise is allowed."""
        return self.is_open and self.days(on) > standard.raising_days

    @property
    def raised_by(self) -> float:
        """How much taller the device came back, zero when it is still open."""
        if self.after_depth is None:
            return 0.0
        return self.after_depth - self.before_depth

    def finish(
        self,
        on: dt.date,
        *,
        depth: float | None = None,
        screen_top: float | None = None,
        screen_bottom: float | None = None,
        note: str = "",
    ) -> Job:
        """Record the work as finished, with what the device measures now."""
        if not self.is_open:
            raise StateError(self.label, "finished", "open")
        if on < self.started_on:
            raise OrderError(self.label, str(self.started_on), str(on))
        if not self.kind.changes_construction:
            return replace(self, finished_on=on, note=note or self.note)
        if depth is None or screen_top is None or screen_bottom is None:
            raise RuleError("rework", f"a finished {self.kind} is measured afterwards")
        return replace(
            self,
            finished_on=on,
            after_depth=depth,
            after_top=screen_top,
            after_bottom=screen_bottom,
            note=note or self.note,
        )

    def apply(self, device: Device) -> Device:
        """The device as it is once the work is finished."""
        if self.is_open:
            raise StateError(self.label, "open", "finished")
        if not self.kind.changes_construction:
            return device
        if self.after_depth is None or self.after_top is None or self.after_bottom is None:
            raise RuleError("rework", "the device was not measured afterwards")
        return replace(
            device,
            total_depth=self.after_depth,
            screen_top=self.after_top,
            screen_bottom=self.after_bottom,
        )

    @classmethod
    def opened(cls, label: str, device: Device, kind: Rework, on: dt.date, note: str = "") -> Job:
        """Start a piece of work, taking the construction as it stands now."""
        return cls(
            label=label,
            device=device.label,
            site=device.site,
            kind=kind,
            started_on=on,
            before_depth=device.total_depth,
            before_top=device.screen_top,
            before_bottom=device.screen_bottom,
            note=note,
        )


__all__ = ["Job", "Rework"]

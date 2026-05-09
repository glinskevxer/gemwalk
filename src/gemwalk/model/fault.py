"""What the cover itself looks like, which is not what it is emitting.

The surface programme measures gas coming through the cover. This is the other
half of the same job: walking the cover and writing down what is wrong with it
before it starts emitting. A crack, a rut worn by the water, a place where the
soil has slid off the slope, a spot where the refuse is showing through.

The two are separate records on purpose. A crack is a cover fault whether or
not anything is coming out of it today, and a reading over the limit is a
finding whether or not anybody can see why. Filing them together would mean a
crack nobody could smell went unrecorded, which is exactly the crack worth
recording, because in three months it will be the one emitting.

How urgent a fault is comes from what kind it is and how big, and the two do
not trade off. Exposed refuse is serious at any size. An inch of settlement
over an acre is not.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import Enum

from gemwalk.clock import deadline, is_overdue
from gemwalk.errors import OrderError, RuleError, StateError

URGENT_DAYS = 10
ORDINARY_DAYS = 30
BIG_SQUARE_FEET = 400.0


class Damage(Enum):
    """What is wrong with the cover."""

    CRACK = "crack"
    EROSION = "erosion"
    PONDING = "ponding"
    SETTLEMENT = "settlement"
    EXPOSED = "exposed refuse"
    SLIDE = "slope failure"
    VEGETATION = "bare ground"

    def __str__(self) -> str:
        return self.value

    @property
    def is_urgent(self) -> bool:
        """True when this kind of damage cannot wait whatever its size."""
        return self in (Damage.EXPOSED, Damage.SLIDE, Damage.CRACK)


@dataclass(frozen=True)
class Fault:
    """One thing wrong with the cover, in one place, on one day."""

    label: str
    site: str
    area: str
    kind: Damage
    station: str
    extent: float
    found_on: dt.date
    found_by: str
    fixed_on: dt.date | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.extent <= 0:
            raise RuleError("fault", "a fault covers some ground")
        if not self.found_by.strip():
            raise RuleError("fault", "somebody found it")
        if self.fixed_on is not None and self.fixed_on < self.found_on:
            raise OrderError("fault", str(self.found_on), str(self.fixed_on))

    @property
    def is_open(self) -> bool:
        """True while the cover is still like this."""
        return self.fixed_on is None

    @property
    def is_big(self) -> bool:
        """True when the fault is large enough to be urgent whatever it is."""
        return self.extent >= BIG_SQUARE_FEET

    @property
    def is_urgent(self) -> bool:
        """True when the fault has to be fixed on the short window."""
        return self.kind.is_urgent or self.is_big

    @property
    def window(self) -> int:
        """How many days the fault gets, which is one of two numbers."""
        return URGENT_DAYS if self.is_urgent else ORDINARY_DAYS

    @property
    def due(self) -> dt.date | None:
        """The last day the fault is still inside its window."""
        return None if not self.is_open else deadline(self.found_on, self.window)

    def days_left(self, on: dt.date) -> int | None:
        """How many days are left, negative when late, nothing when fixed."""
        due = self.due
        return None if due is None else (due - on).days

    def is_late(self, on: dt.date) -> bool:
        """True when an open fault has gone past its window."""
        due = self.due
        return due is not None and is_overdue(due, on)

    def fix(self, on: dt.date, note: str = "") -> Fault:
        """Record the cover work that put it right."""
        if not self.is_open:
            raise StateError(self.label, "fixed", "open")
        if on < self.found_on:
            raise OrderError(self.label, str(self.found_on), str(on))
        return replace(self, fixed_on=on, note=note or self.note)

    def __str__(self) -> str:
        where = f"{self.kind} at {self.station}, {self.extent:g} square feet"
        if not self.is_open:
            return f"{self.label}: {where}, fixed {self.fixed_on}"
        return f"{self.label}: {where}, due {self.due}"


__all__ = [
    "BIG_SQUARE_FEET",
    "ORDINARY_DAYS",
    "URGENT_DAYS",
    "Damage",
    "Fault",
]

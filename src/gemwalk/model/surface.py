"""The quarterly walkover of the cover, and the spots it finds.

A crew walks the whole cover on a serpentine pattern at thirty metre spacing
with a flame ionisation detector held five centimetres off the ground. Any
instantaneous reading of five hundred parts per million or more is a hit, and
the hit is marked, recorded and worked.

Two things about the walk itself can invalidate every reading on it. If the
average wind is over five miles an hour or a gust is over ten, the gas is being
blown off the surface before the detector reaches it, and the walk has to be
done again. If the background is high, every reading on the walk is measured
against a moving floor.

The clock a hit starts is not the clock a wellhead starts. The repair window
runs from the day the hit was found. The remonitor window runs from the day the
repair was made, which the operator chooses. Only the last window, the one that
means putting more collection in the ground, goes back to the day it was found.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import Enum

from gemwalk.clock import Quarter, deadline, is_overdue
from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.landfill import Cover
from gemwalk.rules import Standard
from gemwalk.units import Ppmv


class Step(Enum):
    """Where a surface hit is in the work it needs."""

    REPAIR = "repair"
    REMONITOR = "remonitor"
    EXPANSION = "expansion"
    CLOSED = "closed"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Walk:
    """One quarterly pass over the cover with a detector."""

    label: str
    site: str
    quarter: Quarter
    started_on: dt.date
    monitor: str
    instrument: str
    background: float
    wind_mean: float
    wind_gust: float
    spacing: float
    finished_on: dt.date | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.background < 0:
            raise RuleError("walk", "a background reading cannot be negative")
        if self.wind_mean < 0 or self.wind_gust < self.wind_mean:
            raise RuleError("walk", "a gust cannot be slower than the average")
        if self.spacing <= 0:
            raise RuleError("walk", "a pattern has some spacing")
        if self.finished_on is not None and self.finished_on < self.started_on:
            raise OrderError("walk", str(self.started_on), str(self.finished_on))

    @property
    def is_open(self) -> bool:
        """True while the crew is still walking."""
        return self.finished_on is None

    @property
    def background_reading(self) -> Ppmv:
        """The background the walk was measured against."""
        return Ppmv(self.background)

    def wind_was_calm(self, standard: Standard) -> bool:
        """True when the wind was inside what the standard allows."""
        return (
            self.wind_mean <= standard.wind_average_mph and self.wind_gust <= standard.wind_gust_mph
        )

    def pattern_was_close_enough(self, standard: Standard) -> bool:
        """True when the crew walked no wider than the pattern the standard sets."""
        return self.spacing <= standard.sem_spacing_metres

    def is_valid(self, standard: Standard) -> bool:
        """True when nothing about the walk itself throws its readings out."""
        return self.wind_was_calm(standard) and self.pattern_was_close_enough(standard)

    def faults(self, standard: Standard) -> tuple[str, ...]:
        """Everything about the walk that throws its readings out."""
        found: list[str] = []
        if self.wind_mean > standard.wind_average_mph:
            found.append(
                f"average wind {self.wind_mean:g} mph over the "
                f"{standard.wind_average_mph:g} mph limit"
            )
        if self.wind_gust > standard.wind_gust_mph:
            found.append(
                f"gust {self.wind_gust:g} mph over the {standard.wind_gust_mph:g} mph limit"
            )
        if self.spacing > standard.sem_spacing_metres:
            found.append(
                f"{self.spacing:g} metre spacing wider than the "
                f"{standard.sem_spacing_metres:g} metre pattern"
            )
        return tuple(found)

    def limit(self, standard: Standard) -> Ppmv:
        """What a reading on this walk has to beat to be a hit.

        The standard is five hundred parts per million **above background**, so
        the floor moves with the walk. Two crews on the same cover on the same
        morning can read the same spot and disagree about whether it is a hit,
        and both of them are right.
        """
        return Ppmv(self.background + standard.surface_limit.value)

    def is_over(self, reading: float, standard: Standard) -> bool:
        """True when a reading on this walk is a hit."""
        return reading >= self.limit(standard).value

    def finish(self, on: dt.date) -> Walk:
        """Close the walk off once the whole cover has been crossed."""
        if not self.is_open:
            raise RuleError("walk", f"{self.label} finished on {self.finished_on}")
        return replace(self, finished_on=on)


@dataclass(frozen=True)
class Hit:
    """One spot on the cover reading over the limit, and the work it needs."""

    label: str
    walk: str
    site: str
    area: str
    station: str
    reading: float
    cover: Cover
    found_on: dt.date
    step: Step = Step.REPAIR
    attempt: int = 1
    repaired_on: dt.date | None = None
    remonitor_on: dt.date | None = None
    closed_on: dt.date | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.reading < 0:
            raise RuleError("hit", "a surface reading cannot be negative")
        if self.attempt < 1:
            raise RuleError("hit", "the first attempt is attempt one")
        if self.repaired_on is not None and self.repaired_on < self.found_on:
            raise OrderError("hit", str(self.found_on), str(self.repaired_on))

    @property
    def is_open(self) -> bool:
        """True while the spot still needs work."""
        return self.step is not Step.CLOSED

    @property
    def surface_reading(self) -> Ppmv:
        """What the detector read at the spot."""
        return Ppmv(self.reading)

    def due(self, standard: Standard) -> dt.date | None:
        """The last day the current step is still open.

        The repair window is counted from the day the spot was found and the
        remonitor window from the day it was repaired, so the second deadline
        moves when the crew does.
        """
        windows = standard.surface_windows
        if self.step is Step.REPAIR:
            return deadline(self.found_on, windows.repair)
        if self.step is Step.REMONITOR:
            if self.repaired_on is None:
                return deadline(self.found_on, windows.repair)
            return deadline(self.repaired_on, windows.remonitor)
        if self.step is Step.EXPANSION:
            return deadline(self.found_on, windows.expand)
        return None

    def days_left(self, standard: Standard, on: dt.date) -> int | None:
        """How many days are left in the current step, negative when past it."""
        due = self.due(standard)
        return None if due is None else (due - on).days

    def is_late(self, standard: Standard, on: dt.date) -> bool:
        """True when the current step's window has already run out."""
        due = self.due(standard)
        return due is not None and is_overdue(due, on)

    def repair(self, on: dt.date, note: str = "") -> Hit:
        """Record the cover work and start the remonitor window."""
        if self.step is not Step.REPAIR:
            raise StateError(self.label, str(self.step), "waiting on a repair")
        if on < self.found_on:
            raise OrderError(self.label, str(self.found_on), str(on))
        return replace(self, step=Step.REMONITOR, repaired_on=on, note=note or self.note)

    def clear(self, on: dt.date, note: str = "") -> Hit:
        """Record a remonitor that came back under the limit."""
        if self.step is not Step.REMONITOR:
            raise StateError(self.label, str(self.step), "waiting on a remonitor")
        return replace(
            self,
            step=Step.CLOSED,
            remonitor_on=on,
            closed_on=on,
            note=note or self.note,
        )

    def still_over(self, standard: Standard, on: dt.date, note: str = "") -> Hit:
        """Record a remonitor that came back over, and start the next attempt.

        The operator gets a fixed number of goes at the cover. After the last
        one the spot stops being a cover problem and becomes a collection one,
        and the window for that runs from the day the spot was first found.
        """
        if self.step is not Step.REMONITOR:
            raise StateError(self.label, str(self.step), "waiting on a remonitor")
        if self.attempt >= standard.surface_windows.attempts:
            return replace(
                self,
                step=Step.EXPANSION,
                remonitor_on=on,
                note=note or self.note,
            )
        return replace(
            self,
            step=Step.REPAIR,
            attempt=self.attempt + 1,
            remonitor_on=on,
            repaired_on=None,
            found_on=self.found_on,
            note=note or self.note,
        )

    def close(self, on: dt.date, note: str = "") -> Hit:
        """Close the spot out from wherever it is, once the work is done."""
        if not self.is_open:
            raise StateError(self.label, "closed", "open")
        return replace(self, step=Step.CLOSED, closed_on=on, note=note or self.note)


__all__ = ["Hit", "Step", "Walk"]

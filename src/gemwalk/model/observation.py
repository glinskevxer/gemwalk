"""Standing and watching a flare for smoke, which is a rule about minutes.

The standard for an open flare is not a concentration and not a temperature. It
is that there are no visible emissions for more than five minutes in any two
consecutive hours, and the way that gets established is that somebody stands
where they can see the flare tip with the sun behind them and writes down how
many minutes of it were smoking.

Two things about it catch people out. The limit is a **total** across the two
hours, not a single stretch: six separate fifty second puffs is over. And the
observation has to actually cover two hours before it can say anything about a
two hour rule, so a twenty minute watch with four minutes of smoke in it has not
found a violation, it has found something worth coming back for.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from gemwalk.errors import RuleError

WINDOW_MINUTES = 120.0
ALLOWED_MINUTES = 5.0


@dataclass(frozen=True)
class Observation:
    """One period spent watching a flare, and how much of it was smoking."""

    label: str
    control: str
    site: str
    started_at: dt.datetime
    watched: float
    visible: float
    observer: str
    note: str = ""

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None:
            raise RuleError("observation", "an observation is stamped with an offset")
        if self.watched <= 0:
            raise RuleError("observation", "an observation covers some minutes")
        if self.visible < 0:
            raise RuleError("observation", "smoke is not measured in negative minutes")
        if self.visible > self.watched:
            raise RuleError(
                "observation",
                f"{self.visible:g} minutes of smoke in a {self.watched:g} minute watch",
            )
        if not self.observer.strip():
            raise RuleError("observation", "somebody stood there and watched it")

    @property
    def is_long_enough(self) -> bool:
        """True when the watch covered the two hours the rule is written about."""
        return self.watched >= WINDOW_MINUTES

    @property
    def rate(self) -> float:
        """Smoking minutes as a share of the minutes watched."""
        return self.visible / self.watched

    @property
    def in_two_hours(self) -> float:
        """The smoking minutes scaled up to the two hour window of the rule."""
        return self.rate * WINDOW_MINUTES

    @property
    def over(self) -> bool:
        """True when a long enough watch found more smoke than the rule allows."""
        return self.is_long_enough and self.visible > ALLOWED_MINUTES

    @property
    def worth_another_look(self) -> bool:
        """True when a short watch was on course to be over had it run its time."""
        if self.is_long_enough:
            return False
        return self.in_two_hours > ALLOWED_MINUTES

    @property
    def finished_at(self) -> dt.datetime:
        """The moment the watch ended."""
        return self.started_at + dt.timedelta(minutes=self.watched)

    def __str__(self) -> str:
        if self.over:
            return (
                f"{self.label}: {self.visible:g} minutes of smoke in "
                f"{self.watched:g}, over the {ALLOWED_MINUTES:g} minute limit"
            )
        if self.worth_another_look:
            return (
                f"{self.label}: {self.visible:g} minutes in {self.watched:g}, which is "
                f"{self.in_two_hours:.1f} over two hours, so go back and watch it properly"
            )
        if not self.is_long_enough:
            return f"{self.label}: only {self.watched:g} minutes watched, which says nothing"
        return f"{self.label}: {self.visible:g} minutes of smoke in {self.watched:g}, inside"


__all__ = ["ALLOWED_MINUTES", "WINDOW_MINUTES", "Observation"]

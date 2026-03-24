"""The route a walkover is meant to follow, and whether it followed it.

A surface walkover is not a wander. The pattern is laid out in advance as a
serpentine across the whole area at the standard spacing, and it is written down
as legs, because a leg is what a crew can actually be told to walk and what they
can tick off when they have.

The point of writing it down is that a walk that covered nine of eleven legs is
not a walk of the area. It is a walk of most of the area, and the two legs
nobody crossed are exactly where nobody looked. Recording only the spots that
were found makes those two legs invisible: an area with no findings and an area
nobody walked produce identical paperwork.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace

from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.rules import Standard

SQUARE_METRES_IN_AN_ACRE = 4_046.86


@dataclass(frozen=True)
class Leg:
    """One length of the pattern across one area."""

    label: str
    site: str
    area: str
    name: str
    metres: float
    retired_on: dt.date | None = None

    def __post_init__(self) -> None:
        if self.metres <= 0:
            raise RuleError("leg", "a leg is some distance")
        if not self.name.strip():
            raise RuleError("leg", "a leg is called something a crew can find")

    @property
    def is_live(self) -> bool:
        """True while the leg is still part of the pattern."""
        return self.retired_on is None

    def swept(self, standard: Standard) -> float:
        """How much ground one pass along this leg covers, in square metres.

        A pass sweeps a strip a full spacing wide, because the legs are laid a
        spacing apart and each one covers the ground halfway to its neighbours
        on both sides.
        """
        return self.metres * standard.sem_spacing_metres

    def retire(self, on: dt.date) -> Leg:
        """Take the leg out of the pattern."""
        if not self.is_live:
            raise StateError(self.label, "retired", "live")
        return replace(self, retired_on=on)


@dataclass(frozen=True)
class Covered:
    """One leg of the pattern that one walk actually crossed."""

    walk: str
    leg: str
    note: str = ""
    id: int = 0


@dataclass(frozen=True)
class Route:
    """The pattern over one area, and how much of it a walk covered."""

    area: str
    acres: float
    legs: tuple[Leg, ...]
    walked: tuple[str, ...]

    @property
    def missed(self) -> tuple[str, ...]:
        """Every live leg of the pattern the walk did not cross."""
        return tuple(leg.label for leg in self.legs if leg.label not in self.walked)

    @property
    def share(self) -> float:
        """What share of the pattern the walk covered."""
        if not self.legs:
            return 0.0
        return (len(self.legs) - len(self.missed)) / len(self.legs)

    @property
    def is_whole(self) -> bool:
        """True when the walk crossed every live leg of the pattern."""
        return bool(self.legs) and not self.missed

    def swept(self, standard: Standard) -> float:
        """How much ground the walk covered, in acres."""
        crossed = [leg for leg in self.legs if leg.label in self.walked]
        return sum(leg.swept(standard) for leg in crossed) / SQUARE_METRES_IN_AN_ACRE

    def enough_for(self, standard: Standard) -> bool:
        """True when the ground crossed reaches the acreage of the area."""
        return self.swept(standard) >= self.acres

    def __str__(self) -> str:
        if not self.legs:
            return f"{self.area}: no pattern has been laid out"
        if self.is_whole:
            return f"{self.area}: all {len(self.legs)} legs walked"
        return (
            f"{self.area}: {len(self.legs) - len(self.missed)} of {len(self.legs)} legs, "
            f"missed " + ", ".join(self.missed)
        )


def pattern_for(acres: float, standard: Standard, length: float) -> int:
    """How many legs of a given length a pattern over this area needs."""
    if acres <= 0:
        raise RuleError("route", "an area covers some ground")
    if length <= 0:
        raise OrderError("route", "a leg", "some distance")
    each = length * standard.sem_spacing_metres / SQUARE_METRES_IN_AN_ACRE
    return max(1, -(-acres // each).__int__())


__all__ = ["SQUARE_METRES_IN_AN_ACRE", "Covered", "Leg", "Route", "pattern_for"]

"""Describing a column of numbers, for a desk that does not want a chart.

A wellfield report that gives the average methane and nothing else is hiding
the only interesting thing about it. Forty wells averaging fifty percent could
be forty wells at fifty, or twenty at seventy and twenty at thirty, and those
are completely different fields with completely different problems.

So everything here is about the shape rather than the middle. The quartiles say
how spread out the field is, the extremes say who the outliers are, and the
count of readings under a threshold says how much of the field is in trouble
without anybody having to read a list.

The quartiles are the linear interpolation kind, which is what a spreadsheet
does, so a figure worked out here and a figure worked out in the spreadsheet
somebody keeps alongside will agree.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from gemwalk.errors import RuleError


def quantile(values: list[float], fraction: float) -> float:
    """The value at a fraction of the way through a sorted list.

    Interpolated between the two neighbours the way a spreadsheet does it, so
    the median of an even length list is the mean of the middle two.
    """
    if not values:
        raise RuleError("spread", "there is nothing to take a quantile of")
    if not 0.0 <= fraction <= 1.0:
        raise RuleError("spread", "a quantile is between none of it and all of it")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    place = fraction * (len(ordered) - 1)
    below = math.floor(place)
    above = math.ceil(place)
    if below == above:
        return ordered[below]
    return ordered[below] + (ordered[above] - ordered[below]) * (place - below)


@dataclass(frozen=True)
class Spread:
    """The shape of a column of numbers."""

    count: int
    smallest: float
    lower: float
    middle: float
    upper: float
    largest: float
    mean: float

    @property
    def between(self) -> float:
        """How wide the middle half of the numbers is."""
        return self.upper - self.lower

    @property
    def reach(self) -> float:
        """How far the whole column runs from end to end."""
        return self.largest - self.smallest

    @property
    def is_tight(self) -> bool:
        """True when the middle half sits inside a tenth of the whole range."""
        if self.reach == 0:
            return True
        return self.between <= self.reach * 0.1

    def outliers(self, values: list[float]) -> list[float]:
        """Every value more than one and a half middle halves outside it.

        The usual rule, and it is here rather than in the caller because a
        wellfield report that lists the outliers has to list the same ones each
        time somebody asks.
        """
        if self.between == 0:
            return []
        room = self.between * 1.5
        return sorted(v for v in values if v < self.lower - room or v > self.upper + room)

    def __str__(self) -> str:
        return (
            f"{self.count} readings, {self.smallest:g} to {self.largest:g}, "
            f"middle half {self.lower:g} to {self.upper:g}"
        )


def spread(values: list[float]) -> Spread:
    """Read the shape of a column of numbers."""
    if not values:
        raise RuleError("spread", "there is nothing to describe")
    return Spread(
        count=len(values),
        smallest=min(values),
        lower=quantile(values, 0.25),
        middle=quantile(values, 0.5),
        upper=quantile(values, 0.75),
        largest=max(values),
        mean=sum(values) / len(values),
    )


def share_under(values: list[float], threshold: float) -> float:
    """What share of the numbers are under a threshold."""
    if not values:
        raise RuleError("spread", "there is nothing to count")
    return sum(1 for value in values if value < threshold) / len(values)


def share_over(values: list[float], threshold: float) -> float:
    """What share of the numbers are over a threshold."""
    if not values:
        raise RuleError("spread", "there is nothing to count")
    return sum(1 for value in values if value > threshold) / len(values)


__all__ = ["Spread", "quantile", "share_over", "share_under", "spread"]

"""When a collection system is allowed to be turned off and taken out.

This is the end of the whole exercise and it is deliberately hard to reach.
Three things all have to be true at once, and the third one is the interesting
one because it cannot be established at a moment: the emission rate has to have
been under the threshold on three successive tests, at least ninety days apart,
which means the earliest a site can even start the argument is six months after
it first came in under.

The clock on the first criterion runs from closure, not from the last load and
not from when the system went in. And the second criterion is about the rate at
the tier the site actually used: a site that got under the threshold by paying
for tier two sampling has got under the threshold, and one that got there by
guessing has not, which is why the tier travels with the estimate everywhere in
this package.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from itertools import pairwise

from gemwalk.errors import RuleError
from gemwalk.nmoc import Estimate
from gemwalk.rules import Standard

YEARS_CLOSED = 15
SAMPLES_WANTED = 3
DAYS_APART = 90


@dataclass(frozen=True)
class Sample:
    """One emission rate worked out on one day.

    Called a sample rather than a test because the standard calls the whole
    exercise a test and pytest calls anything named that a test case, and the
    two of them together produced a collection error nobody could read.
    """

    on: dt.date
    estimate: Estimate

    def under(self, standard: Standard) -> bool:
        """True when this test came in under the threshold."""
        return not self.estimate.over(standard)


@dataclass(frozen=True)
class Case:
    """Whether a site can turn its collection system off, and what is missing."""

    closed_on: dt.date | None
    asked_on: dt.date
    tests: tuple[Sample, ...]
    years_closed: float
    long_enough: bool
    enough_tests: bool
    far_enough_apart: bool
    all_under: bool
    settled: bool

    @property
    def is_allowed(self) -> bool:
        """True when every one of the three criteria is met."""
        return (
            self.long_enough
            and self.enough_tests
            and self.far_enough_apart
            and (self.all_under and self.settled)
        )

    @property
    def missing(self) -> tuple[str, ...]:
        """Everything that is not yet true, in the order the standard lists it."""
        short: list[str] = []
        if self.closed_on is None:
            short.append("the site is still taking waste")
        elif not self.long_enough:
            short.append(f"closed {self.years_closed:.1f} years, which is short of {YEARS_CLOSED}")
        if not self.enough_tests:
            short.append(f"{len(self.tests)} tests on file, which is short of {SAMPLES_WANTED}")
        elif not self.far_enough_apart:
            short.append(f"the tests are not {DAYS_APART} days apart")
        if self.enough_tests and not self.all_under:
            short.append("not every test came in under the threshold")
        if self.enough_tests and self.all_under and not self.settled:
            short.append("the rate is still going up")
        return tuple(short)

    def __str__(self) -> str:
        if self.is_allowed:
            return "the collection system may be turned off"
        return "not yet: " + "; ".join(self.missing)


def _spaced(tests: tuple[Sample, ...]) -> bool:
    days = [test.on for test in tests]
    return all((later - earlier).days >= DAYS_APART for earlier, later in pairwise(days))


def _settled(tests: tuple[Sample, ...]) -> bool:
    rates = [test.estimate.megagrams for test in tests]
    return all(later <= earlier for earlier, later in pairwise(rates))


def case(
    standard: Standard,
    *,
    closed_on: dt.date | None,
    asked_on: dt.date,
    tests: list[Sample],
) -> Case:
    """Read a site against the three criteria for taking the system out."""
    if closed_on is not None and asked_on < closed_on:
        raise RuleError("removal", "the day asked about is before the site closed")
    ordered = tuple(sorted(tests, key=lambda test: test.on))
    recent = ordered[-SAMPLES_WANTED:]
    years = 0.0 if closed_on is None else (asked_on - closed_on).days / 365.25
    enough = len(ordered) >= SAMPLES_WANTED
    return Case(
        closed_on=closed_on,
        asked_on=asked_on,
        tests=ordered,
        years_closed=years,
        long_enough=closed_on is not None and years >= YEARS_CLOSED,
        enough_tests=enough,
        far_enough_apart=enough and _spaced(recent),
        all_under=enough and all(test.under(standard) for test in recent),
        settled=enough and _settled(recent),
    )


__all__ = ["DAYS_APART", "SAMPLES_WANTED", "YEARS_CLOSED", "Case", "Sample", "case"]

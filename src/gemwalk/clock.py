"""Dates, moments and the calendar the regulation counts in.

Two clocks run through this package and they are not the same clock.

The compliance clock counts **calendar days** from the day a reading was taken.
It does not skip weekends, it does not care what time of day the reading was
taken, and a deadline that lands on a Sunday is still a Sunday. Everything
about it lives on :class:`datetime.date`.

The operating clock is a wall clock at the site, which sits in one named zone
and moves twice a year. Plant runtime, flare temperature blocks and downtime
are all measured on it. Everything about it is an aware
:class:`datetime.datetime`, stored in utc and shown in the site zone.

Subtracting two aware datetimes that carry the same ``tzinfo`` ignores the
offset, so an interval spanning a clock change comes out an hour wrong. Every
subtraction in this package goes through :func:`elapsed`, which converts both
sides to utc first.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from gemwalk.errors import OrderError, UnitError

UTC = dt.UTC

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y")
_TIME_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S")


def read_day(text: str) -> dt.date:
    """Read a date off a field sheet, which is written ``YYYY-MM-DD`` here."""
    stripped = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(stripped, fmt).date()  # noqa: DTZ007
        except ValueError:
            continue
    raise UnitError(text, "a date")


def read_moment(text: str, zone: str) -> dt.datetime:
    """Read a local wall time at *zone* and return it as an aware utc moment."""
    stripped = text.strip()
    for fmt in _TIME_FORMATS:
        try:
            naive = dt.datetime.strptime(stripped, fmt)  # noqa: DTZ007
        except ValueError:
            continue
        return naive.replace(tzinfo=ZoneInfo(zone)).astimezone(UTC)
    raise UnitError(text, "a moment")


def show_moment(moment: dt.datetime, zone: str) -> str:
    """Print an aware moment as the site's own wall clock reads it."""
    return moment.astimezone(ZoneInfo(zone)).strftime("%Y-%m-%d %H:%M")


def elapsed(start: dt.datetime, end: dt.datetime) -> dt.timedelta:
    """The real interval between two aware moments, offsets honoured."""
    return end.astimezone(UTC) - start.astimezone(UTC)


def hours_between(start: dt.datetime, end: dt.datetime) -> float:
    """The real interval in hours, which is what runtime is billed in."""
    return elapsed(start, end).total_seconds() / 3600.0


def deadline(start: dt.date, days: int) -> dt.date:
    """The last day a calendar-day window is still open.

    The regulation says "within *n* calendar days" and counts the day after the
    reading as day one, so a five day window on a Monday closes on the Saturday.
    """
    if days < 0:
        raise OrderError("window", str(days), "zero")
    return start + dt.timedelta(days=days)


def days_between(start: dt.date, end: dt.date) -> int:
    """Calendar days from *start* to *end*, negative when *end* came first."""
    return (end - start).days


def is_overdue(due: dt.date, on: dt.date) -> bool:
    """True when *on* is past the last day of the window."""
    return on > due


@dataclass(frozen=True, order=True)
class Quarter:
    """A calendar quarter, which is what surface monitoring is counted in."""

    year: int
    number: int

    def __post_init__(self) -> None:
        if not 1 <= self.number <= 4:
            raise UnitError(f"{self.year}Q{self.number}", "a quarter")

    @classmethod
    def of(cls, day: dt.date) -> Quarter:
        """The quarter a day falls in."""
        return cls(day.year, (day.month - 1) // 3 + 1)

    @classmethod
    def parse(cls, text: str) -> Quarter:
        """Read ``"2025Q2"`` or ``"2025-Q2"`` as a quarter."""
        flat = text.strip().upper().replace("-", "")
        if len(flat) != 6 or flat[4] != "Q" or not flat[:4].isdigit() or not flat[5].isdigit():
            raise UnitError(text, "a quarter")
        return cls(int(flat[:4]), int(flat[5]))

    @property
    def first_day(self) -> dt.date:
        """The first day of the quarter."""
        return dt.date(self.year, (self.number - 1) * 3 + 1, 1)

    @property
    def last_day(self) -> dt.date:
        """The last day of the quarter."""
        return self.next.first_day - dt.timedelta(days=1)

    @property
    def next(self) -> Quarter:
        """The quarter after this one."""
        if self.number == 4:
            return Quarter(self.year + 1, 1)
        return Quarter(self.year, self.number + 1)

    @property
    def previous(self) -> Quarter:
        """The quarter before this one."""
        if self.number == 1:
            return Quarter(self.year - 1, 4)
        return Quarter(self.year, self.number - 1)

    def contains(self, day: dt.date) -> bool:
        """True when *day* falls inside this quarter."""
        return self.first_day <= day <= self.last_day

    def __str__(self) -> str:
        return f"{self.year}Q{self.number}"


@dataclass(frozen=True, order=True)
class Month:
    """A calendar month, which is what wellfield monitoring is counted in."""

    year: int
    number: int

    def __post_init__(self) -> None:
        if not 1 <= self.number <= 12:
            raise UnitError(f"{self.year}-{self.number}", "a month")

    @classmethod
    def of(cls, day: dt.date) -> Month:
        """The month a day falls in."""
        return cls(day.year, day.month)

    @classmethod
    def parse(cls, text: str) -> Month:
        """Read ``"2025-04"`` as a month."""
        flat = text.strip()
        if len(flat) != 7 or flat[4] != "-":
            raise UnitError(text, "a month")
        try:
            return cls(int(flat[:4]), int(flat[5:]))
        except ValueError:
            raise UnitError(text, "a month") from None

    @property
    def first_day(self) -> dt.date:
        """The first day of the month."""
        return dt.date(self.year, self.number, 1)

    @property
    def last_day(self) -> dt.date:
        """The last day of the month."""
        return self.next.first_day - dt.timedelta(days=1)

    @property
    def next(self) -> Month:
        """The month after this one."""
        if self.number == 12:
            return Month(self.year + 1, 1)
        return Month(self.year, self.number + 1)

    @property
    def previous(self) -> Month:
        """The month before this one."""
        if self.number == 1:
            return Month(self.year - 1, 12)
        return Month(self.year, self.number - 1)

    def contains(self, day: dt.date) -> bool:
        """True when *day* falls inside this month."""
        return self.first_day <= day <= self.last_day

    @property
    def quarter(self) -> Quarter:
        """The quarter this month sits in."""
        return Quarter.of(self.first_day)

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.number:02d}"


__all__ = [
    "UTC",
    "Month",
    "Quarter",
    "days_between",
    "deadline",
    "elapsed",
    "hours_between",
    "is_overdue",
    "read_day",
    "read_moment",
    "show_moment",
]

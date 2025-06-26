"""Turning the handful of column types the book uses in and out of python.

Eight repositories were each writing their own ``None if x is None else
x.isoformat()``. That is fine until one of them writes a date one way and reads
it back another, which is not something any test of that repository can see,
because it round trips through its own pair. These are the only functions in
the package that write a date, a moment or a flag into a column.
"""

from __future__ import annotations

import datetime as dt

from gemwalk.clock import UTC, read_day


def day_text(day: dt.date | None) -> str | None:
    """Write a date the way every table stores one, blanks included."""
    return None if day is None else day.isoformat()


def read_day_or_none(value: object) -> dt.date | None:
    """Read a date a column may have left blank."""
    if value is None:
        return None
    text = str(value)
    return None if not text.strip() else read_day(text)


def moment_text(moment: dt.datetime | None) -> str | None:
    """Write a moment as utc text, which sorts the way it compares."""
    return None if moment is None else moment.astimezone(UTC).isoformat(timespec="seconds")


def read_moment_or_none(value: object) -> dt.datetime | None:
    """Read a moment a column may have left blank."""
    if value is None:
        return None
    return dt.datetime.fromisoformat(str(value)).astimezone(UTC)


def flag(value: bool) -> int:
    """Write a yes or no the way sqlite holds one."""
    return int(value)


def read_flag(value: object) -> bool:
    """Read a yes or no back out of the book."""
    return bool(value)


__all__ = [
    "day_text",
    "flag",
    "moment_text",
    "read_day_or_none",
    "read_flag",
    "read_moment_or_none",
]

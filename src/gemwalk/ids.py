"""Where every label in the book comes from.

Nothing in this package invents a label at the point of use. A reading, a
finding, a walkover and a work order all get theirs from one counter, and the
counter lives in the book, so two people at two terminals cannot hand out the
same number.

The counters are scoped, because the field paperwork is. An extraction well is
numbered once for the life of the site and keeps its number after it is
abandoned, so nobody drills VW-041 twice. A monitoring run is numbered inside
its month, a surface walkover inside its quarter, and a work order inside its
year, because that is how the folders on the shelf are organised.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum

from gemwalk.clock import Month, Quarter
from gemwalk.errors import UnknownError
from gemwalk.store.book import Book
from gemwalk.store.labels import LabelRepository


class Scope(Enum):
    """How far a counter runs before it starts again at one."""

    FOREVER = "forever"
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"

    def key(self, on: dt.date) -> str:
        """The counter bucket a day falls in."""
        if self is Scope.FOREVER:
            return "-"
        if self is Scope.YEAR:
            return f"{on.year:04d}"
        if self is Scope.QUARTER:
            return str(Quarter.of(on))
        return str(Month.of(on))

    def stem(self, on: dt.date) -> str:
        """The part of the label that says which bucket it came from."""
        if self is Scope.FOREVER:
            return ""
        if self is Scope.YEAR:
            return f"{on.year:04d}-"
        if self is Scope.QUARTER:
            return f"{Quarter.of(on)}-"
        return f"{Month.of(on)}-"


@dataclass(frozen=True)
class Series:
    """One counter: what it labels, what it is called, and how wide it runs."""

    kind: str
    prefix: str
    width: int
    scope: Scope

    def format(self, number: int, on: dt.date) -> str:
        """The label for the *number*th thing in the bucket *on* falls in."""
        return f"{self.prefix}-{self.scope.stem(on)}{number:0{self.width}d}"


SERIES: dict[str, Series] = {
    "device": Series("device", "VW", 3, Scope.FOREVER),
    "lateral": Series("lateral", "LT", 3, Scope.FOREVER),
    "header": Series("header", "HD", 2, Scope.FOREVER),
    "run": Series("run", "MR", 2, Scope.MONTH),
    "finding": Series("finding", "EX", 3, Scope.YEAR),
    "walk": Series("walk", "SW", 2, Scope.QUARTER),
    "hit": Series("hit", "SH", 3, Scope.QUARTER),
    "order": Series("order", "WO", 4, Scope.YEAR),
    "outage": Series("outage", "OT", 3, Scope.YEAR),
    "sump": Series("sump", "CS", 3, Scope.FOREVER),
}


class Labels:
    """The book's label counters."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.rows = LabelRepository(book)

    def series(self, kind: str) -> Series:
        """The counter that labels this kind of thing."""
        try:
            return SERIES[kind]
        except KeyError:
            raise UnknownError("label series", kind) from None

    def next(self, kind: str, on: dt.date) -> str:
        """Hand out the next label of this kind for the bucket *on* falls in."""
        series = self.series(kind)
        return series.format(self.rows.take(kind, series.scope.key(on)), on)

    def peek(self, kind: str, on: dt.date) -> int:
        """How many labels of this kind the bucket has already handed out."""
        series = self.series(kind)
        return self.rows.last(kind, series.scope.key(on))

    def reserve(self, kind: str, on: dt.date, upto: int) -> None:
        """Push a counter forward, for a book seeded from paper records."""
        series = self.series(kind)
        scope = series.scope.key(on)
        with self.book.writing():
            if self.rows.last(kind, scope) < upto:
                self.rows.set(kind, scope, upto)

    def buckets(self, kind: str) -> list[tuple[str, int]]:
        """Every bucket one kind has handed numbers out of."""
        self.series(kind)
        return self.rows.buckets(kind)

    def kinds(self) -> list[str]:
        """Every kind of thing the book hands labels out for."""
        return sorted(SERIES)


__all__ = ["SERIES", "Labels", "Scope", "Series"]

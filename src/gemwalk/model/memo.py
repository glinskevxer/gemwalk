"""A note anybody can put against anything in the book.

Every record in this package is a shape somebody designed, and the field is
full of things nobody designed a shape for: a phone call with the state, a
photograph reference, the reason the crew skipped a wellhead, what the drilling
contractor said about the refuse at eighty feet.

Those things all end up written on the back of a field sheet and lost. A note
is where they go instead. It is deliberately almost featureless: what it is
about, when, who, and the words. The only structure it has is the label of the
thing it is about, so the wellhead's card can carry it.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum

from gemwalk.errors import RuleError


class About(Enum):
    """What kind of thing a note is about."""

    DEVICE = "device"
    AREA = "area"
    RECORD = "record"
    SPOT = "spot"
    RUN = "run"
    WALK = "walk"
    CONTROL = "control device"
    ORDER = "work order"
    SITE = "site"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Memo:
    """One note, about one thing, written by one person at one moment."""

    site: str
    about: About
    subject: str
    at: dt.datetime
    by_whom: str
    body: str
    id: int = 0

    def __post_init__(self) -> None:
        if self.at.tzinfo is None:
            raise RuleError("note", "a note is stamped with an offset")
        if not self.subject.strip():
            raise RuleError("note", "a note is about something")
        if not self.by_whom.strip():
            raise RuleError("note", "a note is written by somebody")
        if not self.body.strip():
            raise RuleError("note", "a note with nothing in it is not a note")

    @property
    def first_line(self) -> str:
        """The first line of the note, for a list that has no room for it all."""
        return self.body.strip().splitlines()[0]

    def mentions(self, word: str) -> bool:
        """True when the note says a word, whatever case it wrote it in."""
        return word.lower() in self.body.lower() or word.lower() in self.subject.lower()

    def __str__(self) -> str:
        return f"{self.about} {self.subject}: {self.first_line}"


__all__ = ["About", "Memo"]

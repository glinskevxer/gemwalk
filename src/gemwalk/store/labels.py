"""The rows behind the label counters.

The counters used to write their own sql from :mod:`gemwalk.ids`, which is two
layers above the store. It worked, and it meant the shape of ``label_run`` was
known somewhere a migration would never look. ``check_sql`` found it.
"""

from __future__ import annotations

from gemwalk.store.book import Book


class LabelRepository:
    """The one table that hands out numbers."""

    def __init__(self, book: Book) -> None:
        self.book = book

    def last(self, kind: str, scope: str) -> int:
        """How far a counter has got, or zero if it has never been used."""
        row = self.book.one(
            "SELECT last FROM label_run WHERE kind = ? AND scope = ?", (kind, scope)
        )
        return 0 if row is None else int(row["last"])

    def take(self, kind: str, scope: str) -> int:
        """Hand out the next number in one bucket and write it back."""
        with self.book.writing():
            number = self.last(kind, scope) + 1
            self.set(kind, scope, number)
            return number

    def set(self, kind: str, scope: str, number: int) -> None:
        """Put a counter at a number, wherever it was before."""
        self.book.execute(
            "INSERT INTO label_run (kind, scope, last) VALUES (?, ?, ?) "
            "ON CONFLICT (kind, scope) DO UPDATE SET last = excluded.last",
            (kind, scope, number),
        )

    def buckets(self, kind: str) -> list[tuple[str, int]]:
        """Every bucket one kind has handed numbers out of, in bucket order."""
        rows = self.book.all(
            "SELECT scope, last FROM label_run WHERE kind = ? ORDER BY scope", (kind,)
        )
        return [(str(row["scope"]), int(row["last"])) for row in rows]


__all__ = ["LabelRepository"]

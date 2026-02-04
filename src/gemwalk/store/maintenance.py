"""Looking after the book itself: checking it, tidying it, copying it.

None of this is about the landfill. It is about the file, and it is here
because a site with three years of records in one sqlite file will eventually
want somebody to answer "is this file all right" without that person having to
know sqlite.

The two checks answer different questions and both are worth running. The
integrity check reads every page and says whether the file is damaged. The
foreign key check reads every row and says whether the records point at each
other properly, which is a thing that can go wrong even in a perfectly healthy
file, because sqlite only enforces keys on connections that asked it to.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gemwalk.store.book import Book


@dataclass(frozen=True)
class Orphan:
    """One row pointing at a parent that is not there."""

    table: str
    rowid: int
    parent: str

    def __str__(self) -> str:
        return f"{self.table} row {self.rowid} points at a {self.parent} that is not there"


@dataclass(frozen=True)
class Health:
    """What the book had to say about itself."""

    pages: int
    page_size: int
    tables: int
    damage: tuple[str, ...]
    orphans: tuple[Orphan, ...]

    @property
    def bytes(self) -> int:
        """How big the book is on disk, near enough."""
        return self.pages * self.page_size

    @property
    def is_sound(self) -> bool:
        """True when nothing is damaged and no record points at nothing."""
        return not self.damage and not self.orphans

    def __str__(self) -> str:
        if self.is_sound:
            return f"{self.tables} tables, {self.bytes:,} bytes, sound"
        return (
            f"{self.tables} tables, {self.bytes:,} bytes, "
            f"{len(self.damage)} damaged, {len(self.orphans)} orphaned rows"
        )


def damage(book: Book) -> tuple[str, ...]:
    """Everything the integrity check had to say, or nothing when it is fine."""
    said = [str(row[0]) for row in book.all("PRAGMA integrity_check")]
    return () if said == ["ok"] else tuple(said)


def orphans(book: Book) -> tuple[Orphan, ...]:
    """Every row pointing at a parent that is not there."""
    return tuple(
        Orphan(table=str(row[0]), rowid=int(row[1] or 0), parent=str(row[2]))
        for row in book.all("PRAGMA foreign_key_check")
    )


def health(book: Book) -> Health:
    """Read the book for damage and for records that point at nothing."""
    return Health(
        pages=int(book.value("PRAGMA page_count") or 0),
        page_size=int(book.value("PRAGMA page_size") or 0),
        tables=len(book.tables()),
        damage=damage(book),
        orphans=orphans(book),
    )


def tidy(book: Book) -> Health:
    """Rebuild the file to reclaim space, then read it again."""
    book.execute("VACUUM")
    book.execute("ANALYZE")
    return health(book)


def copy_to(book: Book, path: str | Path) -> Path:
    """Take a consistent copy of the book, whatever is going on in it."""
    return book.backup(path)


def row_counts(book: Book) -> dict[str, int]:
    """How many rows are in each table, biggest first."""
    counts = {table: book.count(table) for table in book.tables()}
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


__all__ = ["Health", "Orphan", "copy_to", "damage", "health", "orphans", "row_counts", "tidy"]

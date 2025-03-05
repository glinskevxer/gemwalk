"""The schema, written as a list of migrations that only ever grows.

A migration is a number, a name and a script. The book records the ones it has
run in ``schema_log``, so opening an old book applies what it is missing and
opening a current one does nothing. Nothing here is ever edited after it has
shipped: a mistake in migration four is fixed by migration nineteen.

Each migration runs inside one transaction, so a script that fails half way
leaves the book on the version it started at.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from gemwalk.errors import StateError
from gemwalk.store.book import Book

LOG_TABLE = """
CREATE TABLE IF NOT EXISTS schema_log (
  number   INTEGER PRIMARY KEY,
  name     TEXT NOT NULL,
  ran_at   TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Migration:
    """One numbered step of the schema."""

    number: int
    name: str
    script: str

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("migrations are numbered from one")
        if not self.script.strip():
            raise ValueError(f"migration {self.number} has no script")


M001 = Migration(
    number=1,
    name="sites and the areas waste goes into",
    script="""
    CREATE TABLE site (
      label            TEXT PRIMARY KEY,
      name             TEXT NOT NULL,
      standard         TEXT NOT NULL,
      permit           TEXT NOT NULL,
      zone             TEXT NOT NULL,
      design_capacity  REAL NOT NULL,
      opened_on        TEXT NOT NULL,
      closed_on        TEXT
    );

    CREATE TABLE area (
      label        TEXT PRIMARY KEY,
      site         TEXT NOT NULL REFERENCES site(label),
      name         TEXT NOT NULL,
      acres        REAL NOT NULL,
      first_waste  TEXT NOT NULL,
      last_waste   TEXT,
      closed_on    TEXT,
      cover        TEXT NOT NULL
    );

    CREATE INDEX area_by_site ON area(site);
    """,
)

M002 = Migration(
    number=2,
    name="the counters every label is handed out of",
    script="""
    CREATE TABLE label_run (
      kind   TEXT NOT NULL,
      scope  TEXT NOT NULL,
      last   INTEGER NOT NULL,
      PRIMARY KEY (kind, scope)
    );
    """,
)

MIGRATIONS: tuple[Migration, ...] = (M001, M002)


def _applied(book: Book) -> set[int]:
    book.script(LOG_TABLE)
    return {int(row["number"]) for row in book.all("SELECT number FROM schema_log")}


def pending(book: Book) -> list[Migration]:
    """The migrations this book has not run yet, in order."""
    done = _applied(book)
    return [m for m in MIGRATIONS if m.number not in done]


def version(book: Book) -> int:
    """The highest migration number this book has run, or zero."""
    done = _applied(book)
    return max(done) if done else 0


def migrate(book: Book, *, at: dt.datetime | None = None) -> list[Migration]:
    """Bring the book up to the current schema and say what was run."""
    if book.closed:
        raise StateError("the book", "closed", "open")
    stamp = (at or dt.datetime.now(tz=dt.UTC)).isoformat(timespec="seconds")
    ran: list[Migration] = []
    for migration in pending(book):
        with book.writing():
            book.script(migration.script)
            book.execute(
                "INSERT INTO schema_log (number, name, ran_at) VALUES (?, ?, ?)",
                (migration.number, migration.name, stamp),
            )
        ran.append(migration)
    return ran


def numbers_are_contiguous() -> bool:
    """True when the migration numbers run one, two, three with no gaps."""
    return [m.number for m in MIGRATIONS] == list(range(1, len(MIGRATIONS) + 1))


__all__ = [
    "LOG_TABLE",
    "MIGRATIONS",
    "Migration",
    "migrate",
    "numbers_are_contiguous",
    "pending",
    "version",
]

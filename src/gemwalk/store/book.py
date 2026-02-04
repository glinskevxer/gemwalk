"""The sqlite connection every service reads and writes through.

Three things about it are deliberate and each one was a defect first.

The connection runs in autocommit. Python's sqlite driver opens an implicit
transaction on the first write and holds it until something commits, so a desk
that wrote a reading and then closed the book lost the reading. Every test
still passed, because a test reads back through the same connection that wrote
it and sees its own open transaction. Autocommit plus an explicit
:meth:`Book.writing` for work that has to land together is the fix.

Foreign keys are on. Sqlite has them off by default, per connection, and a book
with them off will happily hold a reading against a device that was never
drilled.

:meth:`Book.script` runs statements one at a time rather than handing the lot
to ``executescript``, which commits whatever transaction is open before it
starts and quietly drops a savepoint a migration was relying on.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Any

from gemwalk.errors import StateError

Row = sqlite3.Row
Params = Sequence[Any] | dict[str, Any]

_PRAGMAS = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA busy_timeout = 5000",
)


def _split_statements(script: str) -> list[str]:
    """Split a schema script into statements, leaving triggers whole."""
    statements: list[str] = []
    buffer: list[str] = []
    depth = 0
    for raw in script.splitlines():
        line = raw.split("--", 1)[0] if raw.strip().startswith("--") else raw
        if not line.strip():
            continue
        buffer.append(line)
        lowered = line.strip().lower()
        if lowered.startswith("begin"):
            depth += 1
        if lowered.endswith(";"):
            if depth and lowered.startswith("end;"):
                depth -= 1
            if depth == 0:
                statements.append("\n".join(buffer).strip())
                buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


class Book:
    """One landfill's records, held in one sqlite file."""

    def __init__(self, connection: sqlite3.Connection, path: Path) -> None:
        self._connection = connection
        self._path = path
        self._closed = False
        self._depth = 0

    @classmethod
    def open(cls, path: str | Path) -> Book:
        """Open, or create, the book at *path*."""
        resolved = Path(path)
        connection = sqlite3.connect(resolved, isolation_level=None)
        connection.row_factory = sqlite3.Row
        for pragma in _PRAGMAS:
            connection.execute(pragma)
        return cls(connection, resolved)

    @classmethod
    def memory(cls) -> Book:
        """Open a book that lives only as long as the process does."""
        return cls.open(":memory:")

    @property
    def path(self) -> Path:
        """Where the book sits on disk."""
        return self._path

    @property
    def closed(self) -> bool:
        """True once the book has been shut."""
        return self._closed

    def _live(self) -> sqlite3.Connection:
        if self._closed:
            raise StateError(f"the book at {self._path}", "closed", "open")
        return self._connection

    def execute(self, sql: str, params: Params = ()) -> sqlite3.Cursor:
        """Run one statement and hand back its cursor."""
        return self._live().execute(sql, params)

    def executemany(self, sql: str, rows: Sequence[Params]) -> sqlite3.Cursor:
        """Run one statement once per row."""
        return self._live().executemany(sql, rows)

    def script(self, sql: str) -> None:
        """Run a schema script statement by statement."""
        connection = self._live()
        for statement in _split_statements(sql):
            connection.execute(statement)

    def one(self, sql: str, params: Params = ()) -> Row | None:
        """The first row a query returns, or nothing."""
        row: Row | None = self.execute(sql, params).fetchone()
        return row

    def all(self, sql: str, params: Params = ()) -> list[Row]:
        """Every row a query returns."""
        return self.execute(sql, params).fetchall()

    def value(self, sql: str, params: Params = ()) -> Any:
        """The first column of the first row, or nothing."""
        row = self.one(sql, params)
        return None if row is None else row[0]

    def count(self, table: str, where: str = "", params: Params = ()) -> int:
        """How many rows a table holds, optionally narrowed."""
        clause = f" WHERE {where}" if where else ""
        return int(self.value(f"SELECT count(*) FROM {table}{clause}", params) or 0)

    def tables(self) -> list[str]:
        """Every table in the book, in name order, sqlite's own excluded."""
        rows = self.all(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [str(row["name"]) for row in rows]

    @contextmanager
    def writing(self) -> Iterator[Book]:
        """Hold a transaction open so a piece of work lands whole or not at all.

        Nesting is allowed and only the outermost block commits, so a service
        can call another service without either of them having to know.
        """
        connection = self._live()
        outermost = self._depth == 0
        if outermost:
            connection.execute("BEGIN")
        self._depth += 1
        try:
            yield self
        except BaseException:
            self._depth -= 1
            if outermost:
                connection.execute("ROLLBACK")
            raise
        else:
            self._depth -= 1
            if outermost:
                connection.execute("COMMIT")

    @property
    def in_transaction(self) -> bool:
        """True while a :meth:`writing` block is open."""
        return self._depth > 0

    def backup(self, path: str | Path) -> Path:
        """Copy the whole book to *path*, safely, while it is open.

        Copying the file with the filesystem is not the same thing. A book in
        write ahead logging mode keeps recent work in a second file, so a
        filesystem copy of the main one is a copy of the book as it was at some
        moment nobody chose. Sqlite's own backup takes a consistent one.
        """
        target = Path(path)
        with sqlite3.connect(target) as other:
            self._live().backup(other)
        return target

    def close(self) -> None:
        """Shut the book. Closing twice is not an error."""
        if not self._closed:
            self._connection.close()
            self._closed = True

    def __enter__(self) -> Book:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.close()


__all__ = ["Book", "Params", "Row"]

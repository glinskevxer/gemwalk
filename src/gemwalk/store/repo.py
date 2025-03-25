"""One repository base, so fifteen tables do not each write their own.

A repository is the only thing in the package that knows sql. It turns rows
into model objects and model objects back into rows, refuses a label the book
has never issued, and refuses a label the book already holds. Everything above
it works in model objects and never sees a cursor.

Subclasses fill in four class attributes and two methods. The four attributes
are the table, the word the error messages use for the thing, the primary key
column and the column order. The two methods are the row reader and the row
writer, and they have to agree with each other: :mod:`gemwalk.tools.check_sql`
holds that line by round tripping every repository it can find.
"""

from __future__ import annotations

import sqlite3
from typing import Any, ClassVar, Generic, TypeVar

from gemwalk.errors import DuplicateError, UnknownError
from gemwalk.store.book import Book, Row

T = TypeVar("T")


class Repository(Generic[T]):
    """Rows of one table, read and written as model objects."""

    table: ClassVar[str] = ""
    kind: ClassVar[str] = ""
    key: ClassVar[str] = "label"
    columns: ClassVar[tuple[str, ...]] = ()
    order: ClassVar[str] = "label"
    auto: ClassVar[bool] = False

    def __init__(self, book: Book) -> None:
        self.book = book

    def read(self, row: Row) -> T:
        """Turn one row into a model object."""
        raise NotImplementedError

    def write(self, item: T) -> dict[str, Any]:
        """Turn one model object into the column values it is stored as."""
        raise NotImplementedError

    def label_of(self, item: T) -> str:
        """The primary key of a model object."""
        value = getattr(item, self.key)
        return str(value)

    def with_key(self, item: T, key: int) -> T:
        """The same object carrying the key sqlite just chose for it."""
        raise NotImplementedError

    @property
    def insert_columns(self) -> tuple[str, ...]:
        """The columns an insert writes, which leaves out a key sqlite chooses."""
        if self.auto:
            return tuple(name for name in self.columns if name != self.key)
        return self.columns

    def _select(self, where: str = "", params: tuple[Any, ...] = ()) -> list[Row]:
        clause = f" WHERE {where}" if where else ""
        return self.book.all(f"SELECT * FROM {self.table}{clause} ORDER BY {self.order}", params)

    def find(self, label: str) -> T | None:
        """The thing with this label, or nothing."""
        row = self.book.one(f"SELECT * FROM {self.table} WHERE {self.key} = ?", (label,))
        return None if row is None else self.read(row)

    def get(self, label: str) -> T:
        """The thing with this label, or a refusal naming it."""
        found = self.find(label)
        if found is None:
            raise UnknownError(self.kind, label)
        return found

    def exists(self, label: str) -> bool:
        """True when the book holds this label."""
        return (
            self.book.value(f"SELECT 1 FROM {self.table} WHERE {self.key} = ?", (label,))
            is not None
        )

    def add(self, item: T) -> T:
        """Put a new thing in the book, refusing a label it already holds."""
        label = self.label_of(item)
        values = self.write(item)
        written = self.insert_columns
        placeholders = ", ".join(f":{name}" for name in written)
        names = ", ".join(written)
        try:
            cursor = self.book.execute(
                f"INSERT INTO {self.table} ({names}) VALUES ({placeholders})", values
            )
        except sqlite3.IntegrityError as failure:
            if "UNIQUE" in str(failure):
                raise DuplicateError(self.kind, label) from None
            raise
        if self.auto:
            return self.with_key(item, int(cursor.lastrowid or 0))
        return item

    def put(self, item: T) -> T:
        """Write a thing that is already in the book back over itself."""
        label = self.label_of(item)
        if not self.exists(label):
            raise UnknownError(self.kind, label)
        values = self.write(item)
        assignments = ", ".join(f"{name} = :{name}" for name in self.columns if name != self.key)
        self.book.execute(
            f"UPDATE {self.table} SET {assignments} WHERE {self.key} = :{self.key}", values
        )
        return item

    def remove(self, label: str) -> None:
        """Take a thing out of the book, refusing a label it does not hold."""
        if not self.exists(label):
            raise UnknownError(self.kind, label)
        self.book.execute(f"DELETE FROM {self.table} WHERE {self.key} = ?", (label,))

    def all(self) -> list[T]:
        """Everything in the table, in the order the desk reads it."""
        return [self.read(row) for row in self._select()]

    def where(self, clause: str, params: tuple[Any, ...] = ()) -> list[T]:
        """Everything matching a narrowing clause, in the same order."""
        return [self.read(row) for row in self._select(clause, params)]

    def count(self) -> int:
        """How many things the table holds."""
        return self.book.count(self.table)

    def labels(self) -> list[str]:
        """Every label in the table, in the order the desk reads it."""
        rows = self.book.all(f"SELECT {self.key} FROM {self.table} ORDER BY {self.order}")
        return [str(row[self.key]) for row in rows]


__all__ = ["Repository"]

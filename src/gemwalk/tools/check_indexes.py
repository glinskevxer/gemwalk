"""Every foreign key has an index behind it on the child side.

Sqlite indexes the parent side of a key, because the parent side is a primary
key and it had to. It does not index the child side. So a delete of a parent
row, and every query that walks from a parent to its children, is a table scan
until somebody writes the index by hand.

This is worth a check rather than a habit. Seven of them were missing when it
was first run, and none of them were visible in any query plan anybody had
looked at, because the tables were all small at the time.

The check builds a real book and asks sqlite what it has, rather than reading
the migration text, so an index added by an ``ALTER`` in a later migration is
seen the same way as one written beside its table.
"""

from __future__ import annotations

import sys

from gemwalk.store.book import Book
from gemwalk.store.migrations import migrate
from gemwalk.tools.walker import report


def indexed_columns(book: Book, table: str) -> set[str]:
    """Every column that is the first column of some index or key on a table."""
    covered: set[str] = set()
    for row in book.all(f"PRAGMA index_list('{table}')"):
        columns = book.all(f"PRAGMA index_info('{row['name']}')")
        if columns:
            covered.add(str(columns[0]["name"]))
    for row in book.all(f"PRAGMA table_info('{table}')"):
        if row["pk"]:
            covered.add(str(row["name"]))
    return covered


def faults_in(book: Book) -> list[str]:
    """Every foreign key in the book with nothing indexing its own side."""
    found: list[str] = []
    for table in book.tables():
        covered = indexed_columns(book, table)
        for key in book.all(f"PRAGMA foreign_key_list('{table}')"):
            column = str(key["from"])
            if column not in covered:
                found.append(f"{table}.{column} points at {key['table']}.{key['to']} with no index")
    return found


def main() -> int:
    """Build a book at the current schema and check every key is indexed."""
    with Book.memory() as book:
        migrate(book)
        faults = faults_in(book)
    return report("check_indexes", faults)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

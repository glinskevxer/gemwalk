"""Write the schema out of a real book, and check the written one is current.

``docs/schema.sql`` is not maintained. It is produced by building a book at the
current migration and asking sqlite what it ended up with, so it is the schema
as it actually is and not as the migrations were meant to leave it. An ``ALTER``
in migration nine shows up in the table it altered, where somebody reading the
file will find it.

Run with ``--check`` it compares instead of writing, which is what ci does.
"""

from __future__ import annotations

import sys

from gemwalk.store.book import Book
from gemwalk.store.migrations import MIGRATIONS, migrate
from gemwalk.tools.walker import repo_root

TARGET = "docs/schema.sql"
HEADER = (
    "-- The schema as sqlite holds it at migration {number}.\n"
    "-- Written by gemwalk.tools.schema_dump. Do not edit: add a migration.\n"
)


def dump() -> str:
    """Build a book at the current schema and print what sqlite has."""
    with Book.memory() as book:
        migrate(book)
        rows = book.all(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
            "ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name"
        )
        statements = [f"{str(row['sql']).strip()};" for row in rows]
    body = "\n\n".join(statements)
    return HEADER.format(number=MIGRATIONS[-1].number) + "\n" + body + "\n"


def written() -> str:
    """What the file on disk says, or an empty string if there is none."""
    path = repo_root() / TARGET
    return path.read_text() if path.exists() else ""


def update() -> int:
    """Write the schema file out."""
    path = repo_root() / TARGET
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump())
    print(f"schema_dump: wrote {TARGET}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Write the schema file, or check the one on disk is current."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check" not in args:
        return update()
    if written() == dump():
        print("schema_dump: nothing to report")
        return 0
    print(f"schema_dump: {TARGET} is not the schema, run this tool with no arguments")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

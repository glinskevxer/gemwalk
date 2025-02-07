"""The schema goes on from wherever the book already is."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemwalk.errors import StateError
from gemwalk.store.book import Book
from gemwalk.store.migrations import (
    MIGRATIONS,
    Migration,
    migrate,
    numbers_are_contiguous,
    pending,
    version,
)


@pytest.fixture
def book(tmp_path: Path) -> Book:
    return Book.open(tmp_path / "site.sqlite3")


def test_a_new_book_is_at_version_zero_and_owes_everything(book: Book) -> None:
    assert version(book) == 0
    assert len(pending(book)) == len(MIGRATIONS)
    book.close()


def test_migrating_runs_the_lot_and_then_nothing(book: Book) -> None:
    ran = migrate(book)
    assert [m.number for m in ran] == [m.number for m in MIGRATIONS]
    assert migrate(book) == []
    assert version(book) == MIGRATIONS[-1].number
    book.close()


def test_the_tables_a_migration_names_are_there_afterwards(book: Book) -> None:
    migrate(book)
    assert "site" in book.tables()
    assert "area" in book.tables()
    book.close()


def test_the_log_carries_the_name_and_the_moment(book: Book) -> None:
    migrate(book)
    row = book.one("SELECT * FROM schema_log WHERE number = 1")
    assert row is not None
    assert row["name"] == MIGRATIONS[0].name
    assert row["ran_at"].startswith("20")
    book.close()


def test_a_migration_survives_the_book_being_reopened(tmp_path: Path) -> None:
    path = tmp_path / "site.sqlite3"
    first = Book.open(path)
    migrate(first)
    first.close()

    second = Book.open(path)
    assert version(second) == MIGRATIONS[-1].number
    assert pending(second) == []
    second.close()


def test_a_shut_book_cannot_be_migrated(book: Book) -> None:
    book.close()
    with pytest.raises(StateError):
        migrate(book)


def test_migration_numbers_have_no_gaps() -> None:
    assert numbers_are_contiguous()


def test_a_migration_needs_a_number_and_a_script() -> None:
    with pytest.raises(ValueError, match="numbered from one"):
        Migration(0, "nothing", "SELECT 1;")
    with pytest.raises(ValueError, match="no script"):
        Migration(1, "nothing", "   ")


def test_every_migration_name_is_written_once() -> None:
    names = [m.name for m in MIGRATIONS]
    assert len(names) == len(set(names))

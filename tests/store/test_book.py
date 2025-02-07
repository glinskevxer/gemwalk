"""The book commits, rolls back and shuts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from gemwalk.errors import StateError
from gemwalk.store.book import Book


@pytest.fixture
def book(tmp_path: Path) -> Book:
    opened = Book.open(tmp_path / "site.sqlite3")
    opened.script("CREATE TABLE probe (label TEXT PRIMARY KEY, note TEXT NOT NULL);")
    return opened


def test_a_write_survives_the_book_being_shut(tmp_path: Path) -> None:
    path = tmp_path / "site.sqlite3"
    first = Book.open(path)
    first.script("CREATE TABLE probe (label TEXT PRIMARY KEY);")
    first.execute("INSERT INTO probe VALUES ('VW-001')")
    first.close()

    second = Book.open(path)
    assert second.count("probe") == 1
    second.close()


def test_a_writing_block_that_raises_leaves_nothing_behind(book: Book) -> None:
    def abandon(fail: bool) -> None:
        with book.writing():
            book.execute("INSERT INTO probe VALUES ('VW-001', 'drilled')")
            if fail:
                raise RuntimeError("the crew went home")

    with pytest.raises(RuntimeError):
        abandon(True)
    assert book.count("probe") == 0
    book.close()


def test_a_writing_block_that_finishes_lands_the_lot(book: Book) -> None:
    with book.writing():
        book.execute("INSERT INTO probe VALUES ('VW-001', 'drilled')")
        book.execute("INSERT INTO probe VALUES ('VW-002', 'drilled')")
    assert book.count("probe") == 2
    book.close()


def test_only_the_outermost_writing_block_commits(book: Book) -> None:
    with book.writing():
        book.execute("INSERT INTO probe VALUES ('VW-001', 'drilled')")
        with book.writing():
            book.execute("INSERT INTO probe VALUES ('VW-002', 'drilled')")
        inside = book.in_transaction
    outside = book.in_transaction
    assert inside
    assert not outside
    assert book.count("probe") == 2
    book.close()


def test_an_inner_failure_rolls_the_whole_block_back(book: Book) -> None:
    def abandon(fail: bool) -> None:
        with book.writing():
            book.execute("INSERT INTO probe VALUES ('VW-001', 'drilled')")
            with book.writing():
                book.execute("INSERT INTO probe VALUES ('VW-002', 'drilled')")
                if fail:
                    raise RuntimeError("the meter died")

    with pytest.raises(RuntimeError):
        abandon(True)
    assert book.count("probe") == 0
    book.close()


def test_foreign_keys_are_on(book: Book) -> None:
    book.script(
        "CREATE TABLE child (label TEXT PRIMARY KEY, parent TEXT NOT NULL REFERENCES probe(label));"
    )
    with pytest.raises(sqlite3.IntegrityError):
        book.execute("INSERT INTO child VALUES ('L-1', 'VW-404')")
    book.close()


def test_a_script_keeps_a_trigger_whole(book: Book) -> None:
    book.script(
        """
        CREATE TABLE seen (label TEXT PRIMARY KEY);
        CREATE TRIGGER probe_seen AFTER INSERT ON probe
        BEGIN
          INSERT INTO seen (label) VALUES (new.label);
        END;
        """
    )
    book.execute("INSERT INTO probe VALUES ('VW-001', 'drilled')")
    assert book.count("seen") == 1
    book.close()


def test_the_book_lists_its_own_tables(book: Book) -> None:
    assert book.tables() == ["probe"]
    book.close()


def test_counting_can_be_narrowed(book: Book) -> None:
    book.executemany(
        "INSERT INTO probe VALUES (?, ?)",
        [("VW-001", "drilled"), ("VW-002", "connected")],
    )
    assert book.count("probe", "note = ?", ("drilled",)) == 1
    book.close()


def test_a_value_off_an_empty_table_is_nothing(book: Book) -> None:
    assert book.value("SELECT note FROM probe") is None
    assert book.all("SELECT * FROM probe") == []
    book.close()


def test_a_shut_book_refuses_to_be_read(book: Book) -> None:
    book.close()
    with pytest.raises(StateError):
        book.count("probe")


def test_shutting_a_shut_book_is_not_an_error(book: Book) -> None:
    book.close()
    book.close()
    assert book.closed


def test_the_book_can_be_used_as_a_context(tmp_path: Path) -> None:
    with Book.open(tmp_path / "site.sqlite3") as opened:
        opened.script("CREATE TABLE probe (label TEXT PRIMARY KEY);")
    assert opened.closed


def test_a_book_in_memory_knows_it_has_no_real_path() -> None:
    with Book.memory() as opened:
        assert str(opened.path) == ":memory:"

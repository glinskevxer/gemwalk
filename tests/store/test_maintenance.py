"""Looking after the book itself."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemwalk.service.office import Office
from gemwalk.service.seed import seed
from gemwalk.store.book import Book
from gemwalk.store.maintenance import copy_to, damage, health, orphans, row_counts, tidy


@pytest.fixture
def filled(book: Book) -> Book:
    seed(Office(book))
    return book


def test_a_fresh_book_is_sound(book: Book) -> None:
    found = health(book)
    assert found.is_sound
    assert found.damage == ()
    assert found.orphans == ()
    assert "sound" in str(found)


def test_a_book_knows_how_big_it_is(filled: Book) -> None:
    found = health(filled)
    assert found.pages > 0
    assert found.page_size > 0
    assert found.bytes == found.pages * found.page_size


def test_a_book_knows_how_many_tables_it_has(book: Book) -> None:
    assert health(book).tables == len(book.tables())


def test_the_integrity_check_says_nothing_about_a_healthy_book(book: Book) -> None:
    assert damage(book) == ()


def test_a_row_pointing_at_nothing_is_found(book: Book) -> None:
    book.execute("PRAGMA foreign_keys = OFF")
    book.execute(
        "INSERT INTO area (label, site, name, acres, first_waste, cover) "
        "VALUES ('A-99', 'NOWHERE', 'phase 99', 4.0, '2020-01-01', 'daily')"
    )
    book.execute("PRAGMA foreign_keys = ON")
    found = orphans(book)
    assert [o.table for o in found] == ["area"]
    assert "points at a site that is not there" in str(found[0])
    assert not health(book).is_sound
    assert "orphaned rows" in str(health(book))


def test_tidying_leaves_the_book_sound(filled: Book) -> None:
    after = tidy(filled)
    assert after.is_sound
    assert after.tables == len(filled.tables())


def test_a_copy_is_a_whole_book(filled: Book, tmp_path: Path) -> None:
    target = tmp_path / "copy.sqlite3"
    written = copy_to(filled, target)
    assert written == target
    with Book.open(target) as other:
        assert row_counts(other) == row_counts(filled)


def test_a_copy_can_be_opened_and_read(filled: Book, tmp_path: Path) -> None:
    copy_to(filled, tmp_path / "copy.sqlite3")
    with Book.open(tmp_path / "copy.sqlite3") as other:
        office = Office(other)
        assert office.sites.sites.get("NORTHRIDGE").permit == "MSW-1188-04"


def test_the_row_counts_come_back_biggest_first(filled: Book) -> None:
    counts = row_counts(filled)
    values = list(counts.values())
    assert values == sorted(values, reverse=True)
    assert counts["reading"] == 72


def test_an_empty_book_has_nothing_in_any_table_but_its_own_log(book: Book) -> None:
    counts = row_counts(book)
    assert set(counts) == set(book.tables())
    assert counts["site"] == 0
    assert counts["reading"] == 0
    assert counts["schema_log"] > 0


def test_a_backup_leaves_no_connection_open_behind_it(filled: Book, tmp_path: Path) -> None:
    """The one that only fails on python 3.13, and only somewhere else.

    ``with sqlite3.connect(...)`` is a transaction context manager, not a
    closing one, so a backup written that way leaves its target connection open
    until the interpreter collects it. On 3.12 that is silent. On 3.13 it is a
    ``ResourceWarning`` raised against whichever test the collector was inside,
    which is never this one.
    """
    import gc
    import sqlite3
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", ResourceWarning)
        for number in range(3):
            copy_to(filled, tmp_path / f"copy-{number}.sqlite3")
        gc.collect()
    assert (tmp_path / "copy-0.sqlite3").exists()
    del sqlite3

"""Fixtures every suite shares.

Every book a test opens is closed again here. An unclosed sqlite connection is
silence on python 3.12 and a ``ResourceWarning`` on 3.13, and because the
warning is raised when the object is collected it lands on whichever test the
collector happened to be running. Twenty two failures, none of them the leak.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from pathlib import Path

import pytest

from gemwalk.store.book import Book
from gemwalk.store.migrations import migrate

ZONE = "America/Chicago"
STAMP = dt.datetime(2025, 1, 2, 12, 0, tzinfo=dt.UTC)


@pytest.fixture
def book(tmp_path: Path) -> Iterator[Book]:
    """An empty book at the current schema, shut again afterwards."""
    opened = Book.open(tmp_path / "northridge.sqlite3")
    migrate(opened, at=STAMP)
    try:
        yield opened
    finally:
        opened.close()


@pytest.fixture
def raw_book(tmp_path: Path) -> Iterator[Book]:
    """A book with no schema in it at all, shut again afterwards."""
    opened = Book.open(tmp_path / "raw.sqlite3")
    try:
        yield opened
    finally:
        opened.close()

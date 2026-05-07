"""A book with a real amount in it, and the plans sqlite makes to read it.

Every table in this book is small on the day it is made and none of them stay
that way: a hundred and twenty wells read every month for fifteen years is a
quarter of a million readings, and the query that fetches one well's history is
the one a person waits on.

So this suite builds a book with several years of a large field in it and asks
sqlite what it intends to do. A plan containing SCAN over a table this size is
a missing index, and the answer is the same whether it takes two milliseconds
today or two seconds in 2031.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator

import pytest

from gemwalk.model.reading import Reading
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, bare, sink

WELLS = 40
MONTHS = 18


def plan(book: Book, sql: str, params: tuple[object, ...] = ()) -> str:
    """What sqlite says it intends to do, as one line of text."""
    rows = book.all(f"EXPLAIN QUERY PLAN {sql}", params)
    return " | ".join(str(row["detail"]) for row in rows)


@pytest.fixture(scope="module")
def filled(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Book]:
    """A book with forty wells read every month for a year and a half."""
    book = Book.open(tmp_path_factory.mktemp("scale") / "big.sqlite3")
    from gemwalk.store.migrations import migrate

    migrate(book)
    office = bare(book)
    devices = sink(office, WELLS)
    with book.writing():
        for month in range(MONTHS):
            day = dt.date(2024, 1, 8) + dt.timedelta(days=30 * month)
            run = office.monitoring.open_run(SITE, day, monitor="D. Kasprzak", meter="GEM-1").label
            for index, device in enumerate(devices):
                office.monitoring.readings.add(
                    Reading(
                        run=run,
                        device=device,
                        taken_on=day,
                        methane=50.0 + index % 7,
                        carbon=35.0,
                        oxygen=0.5,
                        balance=14.5 - index % 7,
                        temperature=110.0 + index % 20,
                        static=-1.4,
                        applied=-12.0,
                        flow=40.0 + index,
                        valve_before=3.0,
                        valve_after=3.0,
                    )
                )
            office.monitoring.runs.put(office.monitoring.runs.get(run).close(day))
    yield book
    book.close()


def test_the_book_holds_what_it_was_told_to(filled: Book) -> None:
    assert filled.count("reading") == WELLS * MONTHS
    assert filled.count("device") == WELLS
    assert filled.count("run") == MONTHS


def test_one_well_s_history_is_found_by_an_index(filled: Book) -> None:
    said = plan(filled, "SELECT * FROM reading WHERE device = ? ORDER BY taken_on, id", ("VW-001",))
    assert "USING INDEX reading_by_device" in said
    assert "SCAN reading" not in said


def test_one_run_s_readings_are_found_by_an_index(filled: Book) -> None:
    said = plan(filled, "SELECT * FROM reading WHERE run = ?", ("MR-2024-01-01",))
    assert "USING INDEX reading_by_run" in said


def test_the_devices_of_a_site_are_found_by_an_index(filled: Book) -> None:
    said = plan(filled, "SELECT * FROM device WHERE site = ?", (SITE,))
    assert "USING INDEX device_by_site" in said


def test_the_devices_in_a_state_are_found_by_an_index(filled: Book) -> None:
    said = plan(filled, "SELECT * FROM device WHERE site = ? AND state = ?", (SITE, "connected"))
    assert "USING INDEX" in said


def test_a_range_of_days_is_found_by_an_index(filled: Book) -> None:
    said = plan(
        filled,
        "SELECT * FROM reading WHERE device = ? AND taken_on >= ? AND taken_on <= ?",
        ("VW-001", "2024-01-01", "2024-12-31"),
    )
    assert "USING INDEX" in said


def test_reading_one_well_s_history_gives_every_month(filled: Book) -> None:
    office = Office(filled)
    history = office.monitoring.readings.of_device("VW-001")
    assert len(history) == MONTHS
    assert history == sorted(history, key=lambda r: (r.taken_on, r.id))


def test_the_shape_of_a_big_run_reads_the_whole_field(filled: Book) -> None:
    office = Office(filled)
    run = office.monitoring.runs.of_site(SITE)[0].label
    shape = office.monitoring.shape_of(run, "methane")
    assert shape is not None
    assert shape.count == WELLS


def test_the_latest_reading_is_found_without_reading_them_all(filled: Book) -> None:
    said = plan(
        filled,
        "SELECT * FROM reading WHERE device = ? AND taken_on <= ? "
        "ORDER BY taken_on DESC, id DESC LIMIT 1",
        ("VW-001", "2025-01-01"),
    )
    assert "SCAN reading" not in said


def test_every_index_the_schema_declares_is_still_there(filled: Book) -> None:
    names = {
        str(row["name"])
        for row in filled.all(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'"
        )
    }
    for wanted in (
        "reading_by_device",
        "reading_by_run",
        "device_by_site",
        "exceedance_by_device",
        "hit_by_site",
        "work_order_by_site",
    ):
        assert wanted in names

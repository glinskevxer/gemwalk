"""Every repository is named here, and the base they share behaves.

The suites next to this one drive each table through its own desk. This one
imports the repository modules directly, so a table whose repository stops
being used anywhere still has something written about it.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest

from gemwalk.errors import UnknownError
from gemwalk.ids import Labels
from gemwalk.model.landfill import Site
from gemwalk.store import (
    devices,
    exceedances,
    labels,
    liquids,
    piping,
    plant,
    readings,
    surface,
    work,
)
from gemwalk.store import sites as site_store
from gemwalk.store.book import Book
from gemwalk.store.repo import Repository

REPOSITORIES: list[type[Repository[Any]]] = [
    site_store.SiteRepository,
    site_store.AreaRepository,
    devices.DeviceRepository,
    piping.HeaderRepository,
    piping.LateralRepository,
    readings.RunRepository,
    readings.ReadingRepository,
    exceedances.ExceedanceRepository,
    exceedances.RecheckRepository,
    surface.WalkRepository,
    surface.HitRepository,
    plant.ControlRepository,
    plant.OperationRepository,
    plant.OutageRepository,
    liquids.SumpRepository,
    liquids.LevelRepository,
    liquids.PumpoutRepository,
    work.WorkOrderRepository,
]


@pytest.mark.parametrize("kind", REPOSITORIES, ids=lambda k: k.__name__)
def test_every_repository_names_its_table_and_its_columns(
    kind: type[Repository[Any]],
) -> None:
    assert kind.table
    assert kind.kind
    assert kind.columns
    assert kind.key in kind.columns


@pytest.mark.parametrize("kind", REPOSITORIES, ids=lambda k: k.__name__)
def test_every_repository_points_at_a_table_the_schema_has(
    kind: type[Repository[Any]], book: Book
) -> None:
    assert kind.table in book.tables()


@pytest.mark.parametrize("kind", REPOSITORIES, ids=lambda k: k.__name__)
def test_every_column_a_repository_names_is_in_its_table(
    kind: type[Repository[Any]], book: Book
) -> None:
    columns = {str(row["name"]) for row in book.all(f"PRAGMA table_info('{kind.table}')")}
    assert set(kind.columns) <= columns


@pytest.mark.parametrize("kind", REPOSITORIES, ids=lambda k: k.__name__)
def test_every_repository_is_empty_to_start_with(kind: type[Repository[Any]], book: Book) -> None:
    assert kind(book).count() == 0
    assert kind(book).all() == []


def test_a_repository_with_no_reader_says_so(book: Book) -> None:
    class Bare(Repository[Any]):
        table = "site"
        kind = "site"
        columns = ("label",)

    with pytest.raises(NotImplementedError):
        Bare(book).read(book.all("PRAGMA table_info('site')")[0])


def test_the_base_refuses_a_label_the_book_never_issued(book: Book) -> None:
    store = site_store.SiteRepository(book)
    with pytest.raises(UnknownError, match="SOUTHFORK"):
        store.get("SOUTHFORK")
    with pytest.raises(UnknownError):
        store.remove("SOUTHFORK")
    assert not store.exists("SOUTHFORK")


def test_the_base_writes_a_row_back_over_itself(book: Book) -> None:
    store = site_store.SiteRepository(book)
    store.add(
        Site(
            label="NORTHRIDGE",
            name="Northridge",
            standard="XXX",
            permit="MSW-1188-04",
            zone="America/Chicago",
            design_capacity=8_400_000.0,
            opened_on=dt.date(1998, 6, 1),
        )
    )
    store.put(store.get("NORTHRIDGE").close(dt.date(2025, 12, 31)))
    assert store.get("NORTHRIDGE").is_closed
    assert store.labels() == ["NORTHRIDGE"]


def test_the_label_table_hands_out_numbers_and_remembers_them(book: Book) -> None:
    rows = labels.LabelRepository(book)
    assert rows.last("device", "-") == 0
    assert rows.take("device", "-") == 1
    assert rows.take("device", "-") == 2
    rows.set("device", "-", 40)
    assert rows.take("device", "-") == 41
    assert rows.buckets("device") == [("-", 41)]


def test_the_counters_and_the_table_agree(book: Book) -> None:
    Labels(book).next("device", dt.date(2025, 4, 8))
    assert labels.LabelRepository(book).last("device", "-") == 1


def test_a_table_with_no_retirement_column_says_so(book: Book) -> None:
    with pytest.raises(UnknownError, match="retirement column"):
        site_store.AreaRepository(book).live("NORTHRIDGE")


def test_a_table_with_no_date_column_says_so(book: Book) -> None:
    with pytest.raises(UnknownError, match="date column"):
        devices.DeviceRepository(book).between_days("NORTHRIDGE", "2025-01-01", "2025-12-31")


def test_the_tables_that_can_be_retired_all_name_their_column() -> None:
    retire: list[type[Repository[Any]]] = [
        piping.HeaderRepository,
        piping.LateralRepository,
        plant.ControlRepository,
        liquids.SumpRepository,
    ]
    for kind in retire:
        assert kind.retired_column == "retired_on"


def test_the_tables_that_are_asked_about_by_day_name_their_column() -> None:
    dated: dict[type[Repository[Any]], str] = {
        surface.HitRepository: "found_on",
        exceedances.ExceedanceRepository: "opened_on",
        work.WorkOrderRepository: "raised_on",
    }
    for kind, column in dated.items():
        assert kind.day_column == column
        assert column in kind.columns


@pytest.mark.parametrize("kind", REPOSITORIES, ids=lambda k: k.__name__)
def test_a_repository_that_names_a_site_column_has_one(
    kind: type[Repository[Any]], book: Book
) -> None:
    columns = {str(row["name"]) for row in book.all(f"PRAGMA table_info('{kind.table}')")}
    if kind.site_column in columns:
        assert kind(book).of_site("NORTHRIDGE") == []

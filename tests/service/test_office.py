"""One office, one book, one of each desk."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pytest

from gemwalk.errors import StateError
from gemwalk.service.office import Office
from gemwalk.store.migrations import MIGRATIONS


@pytest.fixture
def office(tmp_path: Path) -> Office:
    return Office.open(tmp_path / "northridge.sqlite3")


def test_opening_an_office_brings_the_book_up_to_the_schema(office: Office) -> None:
    assert office.schema_version == MIGRATIONS[-1].number
    office.close()


def test_every_desk_is_on_the_same_book(office: Office) -> None:
    desks: list[Any] = [
        office.sites,
        office.wellfield,
        office.piping,
        office.monitoring,
        office.compliance,
        office.surface,
        office.plant,
        office.liquids,
        office.work,
    ]
    assert all(desk.book is office.book for desk in desks)
    office.close()


def test_a_desk_is_made_once_and_handed_out_again(office: Office) -> None:
    assert office.sites is office.sites
    assert office.wellfield is office.wellfield
    office.close()


def test_the_office_counts_every_table(office: Office) -> None:
    counts = office.counts()
    assert counts["site"] == 0
    assert "device" in counts
    assert "exceedance" in counts
    office.close()


def test_work_done_at_one_desk_is_visible_at_another(office: Office) -> None:
    office.sites.open_site(
        "NORTHRIDGE",
        "Northridge",
        subpart="XXX",
        permit="MSW-1188-04",
        zone="America/Chicago",
        design_capacity=8_400_000.0,
        opened_on=dt.date(1998, 6, 1),
    )
    assert office.wellfield.sites.sites.get("NORTHRIDGE").permit == "MSW-1188-04"
    assert office.counts()["site"] == 1
    office.close()


def test_an_office_in_memory_works_the_same_way() -> None:
    with Office.memory() as office:
        assert office.schema_version == MIGRATIONS[-1].number
        assert office.counts()["site"] == 0


def test_closing_the_office_shuts_the_book(office: Office) -> None:
    office.close()
    assert office.book.closed
    with pytest.raises(StateError):
        office.counts()


def test_the_office_can_be_used_as_a_context(tmp_path: Path) -> None:
    with Office.open(tmp_path / "one.sqlite3") as office:
        office.sites.open_site(
            "NORTHRIDGE",
            "Northridge",
            subpart="XXX",
            permit="MSW-1188-04",
            zone="America/Chicago",
            design_capacity=8_400_000.0,
            opened_on=dt.date(1998, 6, 1),
        )
    assert office.book.closed
    with Office.open(tmp_path / "one.sqlite3") as again:
        assert again.counts()["site"] == 1

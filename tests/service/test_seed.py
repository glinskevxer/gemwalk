"""The seeded book, which is the same book every time."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Month, Quarter
from gemwalk.quality import Character
from gemwalk.service.office import Office
from gemwalk.service.seed import SITE, WELLS, seed
from gemwalk.store.book import Book


@pytest.fixture
def office(book: Book) -> Office:
    seed(Office(book))
    return Office(book)


def test_the_seeded_book_has_the_whole_field_in_it(office: Office) -> None:
    counts = office.counts()
    assert counts["device"] == WELLS
    assert counts["area"] == 2
    assert counts["run"] == 6
    assert counts["reading"] == WELLS * 6


def test_the_same_seed_makes_the_same_book(office: Office) -> None:
    from gemwalk.store.migrations import migrate

    with Book.memory() as other:
        migrate(other)
        second = Office(other)
        seed(second)
        assert office.counts() == second.counts()


def test_a_wellhead_runs_hot_for_three_months_and_comes_back(office: Office) -> None:
    history = office.compliance.exceedances.of_device("VW-004")
    assert history
    assert history[0].opened_on == dt.date(2025, 3, 11)
    assert not history[0].is_open


def test_a_wellhead_reads_as_leaking_air(office: Office) -> None:
    run = office.monitoring.runs.of_site(SITE)[-1].label
    shapes = office.monitoring.characters(run)
    assert shapes["VW-007"] is Character.AIR


def test_a_wellhead_is_standing_full_of_water(office: Office) -> None:
    flooded = office.liquids.flooded(SITE, dt.date(2025, 6, 10))
    assert [w.device.label for w in flooded] == ["VW-011"]


def test_a_surface_spot_took_two_goes(office: Office) -> None:
    hit = office.surface.hits.get("SH-2025Q2-001")
    assert hit.attempt == 2
    assert hit.is_open


def test_a_flare_block_averaged_under_its_floor(office: Office) -> None:
    from gemwalk.clock import read_moment
    from gemwalk.service.seed import ZONE

    blocks = office.plant.deviations(
        "CD-01",
        read_moment("2025-06-11 09:00", ZONE),
        read_moment("2025-06-11 15:00", ZONE),
    )
    assert len(blocks) == 1


def test_an_area_is_short_of_collection_and_past_its_day(office: Office) -> None:
    short = office.wellfield.shortfalls(SITE, dt.date(2025, 6, 30))
    assert any(s.overdue for s in short)


def test_every_month_walked_has_a_run(office: Office) -> None:
    missed = office.monitoring.months_missed(SITE, Month(2025, 1), Month(2025, 6))
    assert missed == []


def test_the_first_quarter_and_the_second_were_both_walked(office: Office) -> None:
    missed = office.surface.quarters_missed(SITE, Quarter(2025, 1), Quarter(2025, 2))
    assert missed == []


def test_the_meters_were_calibrated_on_the_days_they_were_used(office: Office) -> None:
    assert office.instruments.standing("GEM5000-40912", dt.date(2025, 6, 10)).is_good
    assert office.instruments.standing("TVA1000B-8841", dt.date(2025, 5, 20)).is_good


def test_there_is_work_open_against_a_record(office: Office) -> None:
    orders = office.work.orders.open_at(SITE)
    assert orders
    assert any(order.because for order in orders)

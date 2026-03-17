"""The shape of a whole run, read through the desk."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, furnish, walk_wellfield

APRIL = dt.date(2025, 4, 8)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def test_a_run_with_no_readings_has_no_shape(office: Office) -> None:
    run = office.monitoring.open_run(
        SITE, APRIL, monitor="D. Kasprzak", meter="GEM5000-40912"
    ).label
    assert office.monitoring.shape_of(run, "methane") is None
    assert office.monitoring.column(run, "methane") == []
    assert office.monitoring.outliers(run, "methane") == []


def test_a_flat_field_reads_as_tight(office: Office) -> None:
    run = walk_wellfield(office, APRIL)
    shape = office.monitoring.shape_of(run, "methane")
    assert shape is not None
    assert shape.count == 4
    assert shape.is_tight
    assert shape.middle == pytest.approx(52.4)


def test_a_field_pulled_two_ways_is_not_tight(office: Office) -> None:
    run = walk_wellfield(
        office,
        APRIL,
        {
            "VW-001": {"methane": 30.0, "carbon": 22.0, "balance": 47.4},
            "VW-002": {"methane": 30.0, "carbon": 22.0, "balance": 47.4},
            "VW-003": {"methane": 68.0, "carbon": 26.0, "balance": 5.4},
            "VW-004": {"methane": 68.0, "carbon": 26.0, "balance": 5.4},
        },
    )
    shape = office.monitoring.shape_of(run, "methane")
    assert shape is not None
    assert not shape.is_tight


def test_the_corrected_column_takes_the_air_out(office: Office) -> None:
    leaking = {"methane": 41.0, "carbon": 30.0, "oxygen": 6.1, "balance": 22.8}
    run = walk_wellfield(office, APRIL, {"VW-001": leaking})
    raw = office.monitoring.column(run, "methane")
    corrected = office.monitoring.column(run, "corrected")
    assert corrected[0] > raw[0]


def test_one_dead_wellhead_shows_up_as_an_outlier(office: Office) -> None:
    dead = {"methane": 2.0, "carbon": 2.0, "oxygen": 0.5, "balance": 95.5}
    run = walk_wellfield(office, APRIL, {"VW-002": dead})
    assert office.monitoring.outliers(run, "methane") == ["VW-002"]


def test_a_field_with_nothing_odd_in_it_has_no_outliers(office: Office) -> None:
    run = walk_wellfield(office, APRIL)
    assert office.monitoring.outliers(run, "methane") == []


def test_the_share_of_the_field_under_a_threshold(office: Office) -> None:
    thin = {"methane": 20.0, "carbon": 15.0, "balance": 64.4}
    run = walk_wellfield(office, APRIL, {"VW-001": thin, "VW-002": thin})
    assert office.monitoring.share_of_field(run, "methane", 40.0, over=False) == pytest.approx(0.5)
    assert office.monitoring.share_of_field(run, "methane", 40.0, over=True) == pytest.approx(0.5)


def test_an_empty_run_has_no_share_either_way(office: Office) -> None:
    run = office.monitoring.open_run(
        SITE, APRIL, monitor="D. Kasprzak", meter="GEM5000-40912"
    ).label
    assert office.monitoring.share_of_field(run, "methane", 40.0, over=False) == 0.0

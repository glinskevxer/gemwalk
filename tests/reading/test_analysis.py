"""What a run's analyses say about the field."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.quality import Character
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import furnish, walk_wellfield

APRIL = dt.date(2025, 4, 8)
MAY = dt.date(2025, 5, 6)
JUNE = dt.date(2025, 6, 10)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def test_a_reading_hands_back_its_analysis(office: Office) -> None:
    run = walk_wellfield(office, APRIL)
    reading = office.monitoring.readings.on_run_for(run, "VW-001")
    assert reading is not None
    assert reading.analysis.character() is Character.SETTLED


def test_every_wellhead_on_a_run_is_read_for_its_shape(office: Office) -> None:
    run = walk_wellfield(
        office,
        APRIL,
        {"VW-002": {"methane": 41.0, "carbon": 30.0, "oxygen": 6.1, "balance": 22.8}},
    )
    shapes = office.monitoring.characters(run)
    assert shapes["VW-001"] is Character.SETTLED
    assert shapes["VW-002"] is Character.AIR


def test_the_wellheads_of_one_shape_come_back_together(office: Office) -> None:
    run = walk_wellfield(
        office,
        APRIL,
        {"VW-002": {"methane": 38.0, "carbon": 27.0, "oxygen": 0.4, "balance": 34.5}},
    )
    starved = office.monitoring.of_character(run, Character.STARVED)
    assert [r.device for r in starved] == ["VW-002"]


def test_the_field_flow_is_what_every_wellhead_gave(office: Office) -> None:
    run = walk_wellfield(office, APRIL)
    assert office.monitoring.field_flow(run) == pytest.approx(4 * 42.0)


def test_the_energy_follows_the_methane_and_the_flow(office: Office) -> None:
    run = walk_wellfield(office, APRIL)
    one = 0.524 * 1_012.0 * 42.0 * 60 / 1_000_000
    assert office.monitoring.energy(run) == pytest.approx(4 * one)


def test_a_wellhead_read_once_has_no_drift(office: Office) -> None:
    walk_wellfield(office, APRIL)
    assert office.monitoring.drifting("VW-001") is None


def test_a_wellhead_losing_gas_drifts_down(office: Office) -> None:
    walk_wellfield(office, APRIL)
    walk_wellfield(office, MAY, {"VW-001": {"methane": 44.0, "carbon": 32.0, "balance": 23.4}})
    moved = office.monitoring.drifting("VW-001")
    assert moved is not None
    assert moved < 0


def test_a_wellhead_that_only_started_leaking_does_not_drift(office: Office) -> None:
    walk_wellfield(
        office, APRIL, {"VW-001": {"methane": 52.0, "carbon": 38.0, "oxygen": 0.5, "balance": 9.5}}
    )
    walk_wellfield(
        office, MAY, {"VW-001": {"methane": 39.0, "carbon": 28.5, "oxygen": 5.6, "balance": 26.9}}
    )
    moved = office.monitoring.drifting("VW-001")
    assert moved is not None
    assert abs(moved) < 2.0


def test_the_drift_window_can_be_widened(office: Office) -> None:
    for day, methane in ((APRIL, 52.4), (MAY, 50.0), (JUNE, 48.0)):
        walk_wellfield(office, day, {"VW-001": {"methane": methane}})
    near = office.monitoring.drifting("VW-001", back=2)
    far = office.monitoring.drifting("VW-001", back=3)
    assert near is not None
    assert far is not None
    assert abs(far) > abs(near)

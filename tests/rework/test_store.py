"""Rework rows go into the book and come back out unchanged."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import DuplicateError
from gemwalk.model.rework import Job, Rework
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from gemwalk.store.rework import ReworkRepository
from tests.support import SITE, furnish

STARTED = dt.date(2025, 3, 1)


@pytest.fixture
def store(book: Book) -> ReworkRepository:
    furnish(Office(book))
    return ReworkRepository(book)


def a_job(store: ReworkRepository, label: str = "RW-001", device: str = "VW-001") -> Job:
    found = Office(store.book).wellfield.devices.get(device)
    return Job.opened(label, found, Rework.RAISE, STARTED)


def test_a_job_round_trips(store: ReworkRepository) -> None:
    job = a_job(store)
    store.add(job)
    assert store.get("RW-001") == job


def test_a_finished_job_round_trips_with_its_measurements(store: ReworkRepository) -> None:
    finished = a_job(store).finish(
        dt.date(2025, 3, 20), depth=122.0, screen_top=52.0, screen_bottom=116.0
    )
    store.add(finished)
    assert store.get("RW-001") == finished


def test_the_same_label_cannot_be_used_twice(store: ReworkRepository) -> None:
    store.add(a_job(store))
    with pytest.raises(DuplicateError):
        store.add(a_job(store))


def test_only_open_jobs_come_back_from_the_open_list(store: ReworkRepository) -> None:
    store.add(a_job(store))
    store.add(
        a_job(store, "RW-002", "VW-002").finish(
            dt.date(2025, 3, 20), depth=122.0, screen_top=52.0, screen_bottom=116.0
        )
    )
    assert [j.label for j in store.open_at(SITE)] == ["RW-001"]
    assert store.open_on("VW-002") is None
    open_one = store.open_on("VW-001")
    assert open_one is not None
    assert open_one.label == "RW-001"


def test_the_history_of_a_device_comes_back_oldest_first(store: ReworkRepository) -> None:
    later = a_job(store, "RW-002")
    store.add(
        Job(
            label="RW-002",
            device="VW-001",
            site=SITE,
            kind=Rework.REPAIR,
            started_on=dt.date(2025, 6, 1),
            before_depth=later.before_depth,
            before_top=later.before_top,
            before_bottom=later.before_bottom,
        )
    )
    store.add(a_job(store))
    assert [j.started_on for j in store.of_device("VW-001")] == [
        STARTED,
        dt.date(2025, 6, 1),
    ]


def test_jobs_come_back_by_a_range_of_days(store: ReworkRepository) -> None:
    store.add(a_job(store))
    inside = store.between_days(SITE, "2025-03-01", "2025-03-31")
    assert [j.label for j in inside] == ["RW-001"]
    assert store.between_days(SITE, "2025-04-01", "2025-04-30") == []

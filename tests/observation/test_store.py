"""Observations go into the book and come back out unchanged."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import DuplicateError
from gemwalk.model.observation import Observation
from gemwalk.model.plant import ControlKind
from gemwalk.store.book import Book
from gemwalk.store.observations import ObservationRepository
from tests.support import SITE, ZONE, bare


@pytest.fixture
def store(book: Book) -> ObservationRepository:
    office = bare(book, areas=False)
    office.plant.install(
        "CD-01",
        SITE,
        "west flare",
        kind=ControlKind.CANDLESTICK,
        capacity=900.0,
        on=dt.date(2019, 5, 1),
    )
    return ObservationRepository(book)


def a_watch(label: str = "VE-2025-001", at: str = "2025-06-11 09:00") -> Observation:
    return Observation(
        label=label,
        control="CD-01",
        site=SITE,
        started_at=read_moment(at, ZONE),
        watched=120.0,
        visible=2.0,
        observer="R. Bellingham",
    )


def test_an_observation_round_trips(store: ObservationRepository) -> None:
    store.add(a_watch())
    assert store.get("VE-2025-001") == a_watch()


def test_the_same_label_cannot_be_used_twice(store: ObservationRepository) -> None:
    store.add(a_watch())
    with pytest.raises(DuplicateError):
        store.add(a_watch())


def test_watches_come_back_in_clock_order(store: ObservationRepository) -> None:
    store.add(a_watch("VE-2025-002", "2025-06-12 09:00"))
    store.add(a_watch("VE-2025-001", "2025-06-11 09:00"))
    assert [w.label for w in store.of_control("CD-01")] == ["VE-2025-001", "VE-2025-002"]


def test_watches_come_back_by_site(store: ObservationRepository) -> None:
    store.add(a_watch())
    assert [w.label for w in store.of_site(SITE)] == ["VE-2025-001"]


def test_a_book_with_no_watches_has_none(store: ObservationRepository) -> None:
    assert store.of_control("CD-01") == []
    assert store.count() == 0

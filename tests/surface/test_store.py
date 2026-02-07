"""Walks and hits go into the book and come back out unchanged."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Quarter
from gemwalk.errors import DuplicateError
from gemwalk.model.landfill import Cover
from gemwalk.model.surface import Hit, Step, Walk
from gemwalk.rules import XXX
from gemwalk.store.book import Book
from gemwalk.store.surface import HitRepository, WalkRepository
from tests.support import bare

STARTED = dt.date(2025, 5, 13)


@pytest.fixture
def store(book: Book) -> tuple[WalkRepository, HitRepository]:
    bare(book)
    walks = WalkRepository(book)
    walks.add(a_walk())
    return walks, HitRepository(book)


def a_walk(label: str = "SW-2025Q2-01", **changes: object) -> Walk:
    fields: dict[str, object] = {
        "label": label,
        "site": "NORTHRIDGE",
        "quarter": Quarter(2025, 2),
        "started_on": STARTED,
        "monitor": "T. Wierzbicki",
        "instrument": "TVA1000B-8841",
        "background": 2.0,
        "wind_mean": 3.4,
        "wind_gust": 7.1,
        "spacing": 30.0,
    }
    fields.update(changes)
    return Walk(**fields)  # type: ignore[arg-type]


def a_hit(label: str = "SH-2025Q2-001", **changes: object) -> Hit:
    fields: dict[str, object] = {
        "label": label,
        "walk": "SW-2025Q2-01",
        "site": "NORTHRIDGE",
        "area": "A-03",
        "station": "grid 14-J",
        "reading": 720.0,
        "cover": Cover.INTERMEDIATE,
        "found_on": STARTED,
    }
    fields.update(changes)
    return Hit(**fields)  # type: ignore[arg-type]


def test_a_walk_round_trips(store: tuple[WalkRepository, HitRepository]) -> None:
    walks, _ = store
    assert walks.get("SW-2025Q2-01") == a_walk()


def test_a_finished_walk_round_trips(store: tuple[WalkRepository, HitRepository]) -> None:
    walks, _ = store
    walks.put(walks.get("SW-2025Q2-01").finish(dt.date(2025, 5, 15)))
    assert walks.get("SW-2025Q2-01").finished_on == dt.date(2025, 5, 15)
    assert walks.open_walks("NORTHRIDGE") == []


def test_walks_come_back_by_quarter(store: tuple[WalkRepository, HitRepository]) -> None:
    walks, _ = store
    walks.add(a_walk("SW-2025Q3-01", quarter=Quarter(2025, 3), started_on=dt.date(2025, 8, 5)))
    assert [w.label for w in walks.in_quarter("NORTHRIDGE", Quarter(2025, 2))] == ["SW-2025Q2-01"]
    assert len(walks.of_site("NORTHRIDGE")) == 2


def test_a_walk_label_cannot_be_used_twice(
    store: tuple[WalkRepository, HitRepository],
) -> None:
    walks, _ = store
    with pytest.raises(DuplicateError):
        walks.add(a_walk())


def test_a_hit_round_trips_through_every_step(
    store: tuple[WalkRepository, HitRepository],
) -> None:
    _, hits = store
    hits.add(a_hit())
    assert hits.get("SH-2025Q2-001") == a_hit()
    worked = a_hit().repair(dt.date(2025, 5, 16)).still_over(XXX, dt.date(2025, 5, 22))
    hits.put(worked)
    assert hits.get("SH-2025Q2-001") == worked
    assert hits.get("SH-2025Q2-001").attempt == 2


def test_only_open_spots_come_back_from_the_open_list(
    store: tuple[WalkRepository, HitRepository],
) -> None:
    _, hits = store
    hits.add(a_hit())
    hits.add(a_hit("SH-2025Q2-002").close(dt.date(2025, 5, 20)))
    assert [h.label for h in hits.open_at("NORTHRIDGE")] == ["SH-2025Q2-001"]


def test_spots_come_back_by_walk_by_area_and_by_step(
    store: tuple[WalkRepository, HitRepository],
) -> None:
    _, hits = store
    hits.add(a_hit())
    hits.add(a_hit("SH-2025Q2-002", area="A-04", station="grid 21-C"))
    assert len(hits.of_walk("SW-2025Q2-01")) == 2
    assert [h.label for h in hits.of_area("A-04")] == ["SH-2025Q2-002"]
    assert len(hits.at_step("NORTHRIDGE", Step.REPAIR)) == 2


def test_spots_come_back_by_a_range_of_days(
    store: tuple[WalkRepository, HitRepository],
) -> None:
    _, hits = store
    hits.add(a_hit())
    hits.add(a_hit("SH-2025Q3-001", found_on=dt.date(2025, 8, 6)))
    inside = hits.between_days("NORTHRIDGE", "2025-05-01", "2025-05-31")
    assert [h.label for h in inside] == ["SH-2025Q2-001"]


def test_the_history_of_one_place_on_the_cover_comes_back_oldest_first(
    store: tuple[WalkRepository, HitRepository],
) -> None:
    _, hits = store
    hits.add(a_hit("SH-2025Q3-001", found_on=dt.date(2025, 8, 6)))
    hits.add(a_hit("SH-2025Q2-001"))
    walked = hits.at_station("NORTHRIDGE", "grid 14-J")
    assert [h.found_on for h in walked] == [STARTED, dt.date(2025, 8, 6)]

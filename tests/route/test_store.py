"""The pattern goes into the book and comes back out unchanged."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Quarter
from gemwalk.errors import DuplicateError
from gemwalk.model.route import Covered, Leg
from gemwalk.model.surface import Walk
from gemwalk.store.book import Book
from gemwalk.store.route import CoveredRepository, LegRepository
from gemwalk.store.surface import WalkRepository
from tests.support import SITE, bare


@pytest.fixture
def store(book: Book) -> tuple[LegRepository, CoveredRepository]:
    bare(book)
    WalkRepository(book).add(
        Walk(
            label="SW-2025Q2-01",
            site=SITE,
            quarter=Quarter(2025, 2),
            started_on=dt.date(2025, 5, 13),
            monitor="T. Wierzbicki",
            instrument="TVA1000B-8841",
            background=2.0,
            wind_mean=3.4,
            wind_gust=7.1,
            spacing=30.0,
        )
    )
    return LegRepository(book), CoveredRepository(book)


def a_leg(label: str = "LG-01", area: str = "A-03") -> Leg:
    return Leg(label=label, site=SITE, area=area, name=f"line {label}", metres=200.0)


def test_a_leg_round_trips(store: tuple[LegRepository, CoveredRepository]) -> None:
    legs, _ = store
    legs.add(a_leg())
    assert legs.get("LG-01") == a_leg()


def test_a_retired_leg_leaves_the_live_list(
    store: tuple[LegRepository, CoveredRepository],
) -> None:
    legs, _ = store
    legs.add(a_leg())
    legs.put(legs.get("LG-01").retire(dt.date(2025, 6, 1)))
    assert legs.live_in("A-03") == []
    assert len(legs.of_area("A-03")) == 1


def test_legs_come_back_by_area(store: tuple[LegRepository, CoveredRepository]) -> None:
    legs, _ = store
    legs.add(a_leg("LG-01", "A-03"))
    legs.add(a_leg("LG-02", "A-04"))
    assert [leg.label for leg in legs.of_area("A-04")] == ["LG-02"]
    assert len(legs.of_site(SITE)) == 2


def test_a_covered_leg_round_trips(store: tuple[LegRepository, CoveredRepository]) -> None:
    legs, covered = store
    legs.add(a_leg())
    stored = covered.add(Covered(walk="SW-2025Q2-01", leg="LG-01", note="wet"))
    assert stored.id > 0
    assert covered.get(str(stored.id)) == stored


def test_a_leg_cannot_be_crossed_twice_on_one_walk(
    store: tuple[LegRepository, CoveredRepository],
) -> None:
    legs, covered = store
    legs.add(a_leg())
    covered.add(Covered(walk="SW-2025Q2-01", leg="LG-01"))
    with pytest.raises(DuplicateError):
        covered.add(Covered(walk="SW-2025Q2-01", leg="LG-01"))


def test_the_legs_a_walk_crossed_come_back_as_labels(
    store: tuple[LegRepository, CoveredRepository],
) -> None:
    legs, covered = store
    legs.add(a_leg("LG-01"))
    legs.add(a_leg("LG-02"))
    covered.add(Covered(walk="SW-2025Q2-01", leg="LG-02"))
    assert covered.labels_of("SW-2025Q2-01") == {"LG-02"}
    assert len(covered.of_walk("SW-2025Q2-01")) == 1


def test_a_walk_that_crossed_nothing_has_no_legs(
    store: tuple[LegRepository, CoveredRepository],
) -> None:
    _, covered = store
    assert covered.labels_of("SW-2025Q2-01") == set()

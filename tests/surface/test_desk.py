"""Running a walkover through the desk."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Quarter
from gemwalk.errors import RuleError, StateError
from gemwalk.model.surface import Step
from gemwalk.service.sites import SiteDesk
from gemwalk.service.surface import SurfaceDesk
from gemwalk.store.book import Book

MAY = dt.date(2025, 5, 13)


@pytest.fixture
def desk(book: Book) -> SurfaceDesk:
    sites = SiteDesk(book)
    sites.open_site(
        "NORTHRIDGE",
        "Northridge",
        subpart="XXX",
        permit="MSW-1188-04",
        zone="America/Chicago",
        design_capacity=8_400_000.0,
        opened_on=dt.date(1998, 6, 1),
    )
    sites.add_area("A-03", "NORTHRIDGE", "phase 3", acres=12.4, first_waste=dt.date(2019, 4, 15))
    sites.open_site(
        "SOUTHFORK",
        "Southfork",
        subpart="WWW",
        permit="MSW-2011-09",
        zone="America/Chicago",
        design_capacity=3_100_000.0,
        opened_on=dt.date(1994, 2, 1),
    )
    sites.add_area("B-01", "SOUTHFORK", "cell one", acres=6.0, first_waste=dt.date(1994, 3, 1))
    return SurfaceDesk(book)


def a_walk(desk: SurfaceDesk, on: dt.date = MAY, background: float = 2.0) -> str:
    return desk.open_walk(
        "NORTHRIDGE",
        on,
        monitor="T. Wierzbicki",
        instrument="TVA1000B-8841",
        background=background,
        wind_mean=3.4,
        wind_gust=7.1,
    ).label


def test_a_walk_takes_the_label_of_its_quarter(desk: SurfaceDesk) -> None:
    assert a_walk(desk) == "SW-2025Q2-01"


def test_two_walks_cannot_be_open_at_one_site(desk: SurfaceDesk) -> None:
    a_walk(desk)
    with pytest.raises(RuleError, match="still open"):
        a_walk(desk)


def test_a_reading_over_the_floor_is_marked(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    hit = desk.mark(walk, "A-03", "grid 14-J", 720.0, on=MAY)
    assert hit.label == "SH-2025Q2-001"
    assert hit.step is Step.REPAIR


def test_a_reading_under_the_floor_is_not_a_hit(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    with pytest.raises(RuleError, match="under the"):
        desk.mark(walk, "A-03", "grid 14-J", 480.0, on=MAY)


def test_the_background_moves_what_counts_as_a_hit(desk: SurfaceDesk) -> None:
    calm = a_walk(desk, background=2.0)
    desk.mark(calm, "A-03", "grid 14-J", 505.0, on=MAY)
    desk.finish_walk(calm, MAY)
    dirty = a_walk(desk, on=dt.date(2025, 8, 5), background=60.0)
    with pytest.raises(RuleError, match="under the"):
        desk.mark(dirty, "A-03", "grid 14-J", 505.0, on=dt.date(2025, 8, 5))


def test_a_finished_walk_takes_no_more_marks(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    desk.finish_walk(walk, dt.date(2025, 5, 15))
    with pytest.raises(StateError):
        desk.mark(walk, "A-03", "grid 14-J", 720.0, on=dt.date(2025, 5, 16))


def test_a_mark_in_another_site_s_area_is_refused(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    with pytest.raises(RuleError, match="not an area"):
        desk.mark(walk, "B-01", "grid 14-J", 720.0, on=MAY)


def test_a_mark_before_the_walk_started_is_refused(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    with pytest.raises(RuleError, match="did not start"):
        desk.mark(walk, "A-03", "grid 14-J", 720.0, on=dt.date(2025, 5, 1))


def test_a_clean_remonitor_closes_a_spot(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    hit = desk.mark(walk, "A-03", "grid 14-J", 720.0, on=MAY).label
    desk.repair(hit, dt.date(2025, 5, 16))
    closed = desk.remonitor(hit, dt.date(2025, 5, 20), 180.0)
    assert not closed.is_open
    assert desk.board("NORTHRIDGE", dt.date(2025, 5, 21)) == []


def test_a_remonitor_still_over_starts_a_second_attempt(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    hit = desk.mark(walk, "A-03", "grid 14-J", 720.0, on=MAY).label
    desk.repair(hit, dt.date(2025, 5, 16))
    again = desk.remonitor(hit, dt.date(2025, 5, 20), 640.0)
    assert again.attempt == 2
    assert again.step is Step.REPAIR


def test_a_second_failed_remonitor_means_more_collection(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    hit = desk.mark(walk, "A-03", "grid 14-J", 720.0, on=MAY).label
    desk.repair(hit, dt.date(2025, 5, 16))
    desk.remonitor(hit, dt.date(2025, 5, 20), 640.0)
    desk.repair(hit, dt.date(2025, 5, 22))
    last = desk.remonitor(hit, dt.date(2025, 5, 28), 610.0)
    assert last.step is Step.EXPANSION
    assert last.due(desk.sites.standard_of("NORTHRIDGE")) == dt.date(2025, 9, 10)


def test_the_board_puts_the_least_time_left_first(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    first = desk.mark(walk, "A-03", "grid 14-J", 720.0, on=MAY).label
    second = desk.mark(walk, "A-03", "grid 21-C", 900.0, on=dt.date(2025, 5, 19)).label
    board = desk.board("NORTHRIDGE", dt.date(2025, 5, 20))
    assert [m.hit.label for m in board] == [first, second]
    assert board[0].days_left == 3


def test_only_late_spots_are_overdue(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    desk.mark(walk, "A-03", "grid 14-J", 720.0, on=MAY)
    assert desk.overdue("NORTHRIDGE", dt.date(2025, 5, 23)) == []
    assert len(desk.overdue("NORTHRIDGE", dt.date(2025, 5, 24))) == 1


def test_a_windy_walk_is_listed_as_invalid(desk: SurfaceDesk) -> None:
    desk.open_walk(
        "NORTHRIDGE",
        MAY,
        monitor="T. Wierzbicki",
        instrument="TVA1000B-8841",
        background=2.0,
        wind_mean=8.0,
        wind_gust=14.0,
    )
    assert [w.label for w in desk.invalid_walks("NORTHRIDGE")] == ["SW-2025Q2-01"]


def test_a_quarter_with_no_valid_finished_walk_is_missed(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    desk.finish_walk(walk, dt.date(2025, 5, 15))
    missed = desk.quarters_missed("NORTHRIDGE", Quarter(2025, 1), Quarter(2025, 3))
    assert [str(q) for q in missed] == ["2025Q1", "2025Q3"]


def test_an_unfinished_walk_does_not_cover_its_quarter(desk: SurfaceDesk) -> None:
    a_walk(desk)
    missed = desk.quarters_missed("NORTHRIDGE", Quarter(2025, 2), Quarter(2025, 2))
    assert [str(q) for q in missed] == ["2025Q2"]


def test_a_place_marked_twice_is_listed(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    desk.mark(walk, "A-03", "grid 14-J", 720.0, on=MAY)
    desk.mark(walk, "A-03", "grid 21-C", 900.0, on=MAY)
    desk.finish_walk(walk, dt.date(2025, 5, 15))
    later = a_walk(desk, on=dt.date(2025, 8, 5))
    desk.mark(later, "A-03", "grid 14-J", 610.0, on=dt.date(2025, 8, 5))
    repeats = desk.repeat_stations("NORTHRIDGE", dt.date(2025, 1, 1))
    assert repeats == {"grid 14-J": 2}


def test_spots_come_back_by_the_work_they_are_waiting_on(desk: SurfaceDesk) -> None:
    walk = a_walk(desk)
    hit = desk.mark(walk, "A-03", "grid 14-J", 720.0, on=MAY).label
    assert len(desk.waiting_on("NORTHRIDGE", Step.REPAIR)) == 1
    desk.repair(hit, dt.date(2025, 5, 16))
    assert len(desk.waiting_on("NORTHRIDGE", Step.REMONITOR)) == 1

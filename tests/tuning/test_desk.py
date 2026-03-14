"""Tuning a whole run through the desk."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Month
from gemwalk.report.monthly import monthly_report
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from gemwalk.tuning import Move
from tests.support import SITE, furnish, walk_wellfield

APRIL = dt.date(2025, 4, 8)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def moves(office: Office, run: str) -> dict[str, Move]:
    return {advice.device: advice.move for advice in office.monitoring.tuning(run)}


def test_a_clean_run_wants_nothing_touched(office: Office) -> None:
    run = walk_wellfield(office, APRIL)
    assert office.monitoring.to_touch(run) == []
    assert set(moves(office, run).values()) == {Move.HOLD}


def test_a_hot_wellhead_is_told_to_close_in(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    assert moves(office, run)["VW-002"] is Move.CLOSE
    assert [a.device for a in office.monitoring.to_touch(run)] == ["VW-002"]


def test_a_wellhead_at_atmosphere_is_told_to_open_up(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-003": {"static": 0.4}})
    assert moves(office, run)["VW-003"] is Move.OPEN


def test_a_dead_wellhead_with_no_tape_gets_a_valve_answer(office: Office) -> None:
    dead = {"methane": 1.0, "carbon": 1.0, "oxygen": 0.5, "balance": 97.5}
    run = walk_wellfield(office, APRIL, {"VW-001": dead})
    assert moves(office, run)["VW-001"] is Move.SHUT


def test_a_dead_wellhead_standing_full_is_told_to_dewater(office: Office) -> None:
    office.liquids.tape("VW-001", dt.date(2025, 4, 7), 20.0)
    dead = {"methane": 1.0, "carbon": 1.0, "oxygen": 0.5, "balance": 97.5}
    run = walk_wellfield(office, APRIL, {"VW-001": dead})
    advice = next(a for a in office.monitoring.tuning(run) if a.device == "VW-001")
    assert advice.move is Move.NONE
    assert "dewater" in advice.because


def test_the_wellheads_that_need_touching_come_first(office: Office) -> None:
    run = walk_wellfield(
        office,
        APRIL,
        {"VW-004": {"temperature": 138.0}, "VW-002": {"static": 0.4}},
    )
    given = office.monitoring.tuning(run)
    assert given[0].device == "VW-004"
    assert given[1].device == "VW-002"


def test_a_tape_drop_after_the_reading_does_not_change_the_advice(office: Office) -> None:
    dead = {"methane": 1.0, "carbon": 1.0, "oxygen": 0.5, "balance": 97.5}
    run = walk_wellfield(office, APRIL, {"VW-001": dead})
    office.liquids.tape("VW-001", dt.date(2025, 4, 20), 20.0)
    assert moves(office, run)["VW-001"] is Move.SHUT


def test_the_monthly_report_carries_what_to_turn(office: Office) -> None:
    walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    section = monthly_report(office, SITE, Month(2025, 4)).find("what to turn")
    assert section is not None
    body = "\n".join(section.lines())
    assert "VW-002" in body
    assert "close in" in body


def test_a_clean_month_says_nothing_wants_touching(office: Office) -> None:
    walk_wellfield(office, APRIL)
    section = monthly_report(office, SITE, Month(2025, 4)).find("what to turn")
    assert section is not None
    assert "nothing on the field wants touching" in "\n".join(section.lines())

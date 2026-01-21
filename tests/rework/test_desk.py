"""Raising a well through the desk."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import RuleError, StateError
from gemwalk.model.device import State
from gemwalk.model.rework import Rework
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, furnish, walk_wellfield

STARTED = dt.date(2025, 3, 1)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def test_starting_work_takes_the_device_off_the_run(office: Office) -> None:
    job = office.wellfield.start_rework("VW-001", Rework.RAISE, STARTED)
    assert job.label == "RW-2025-001"
    assert office.wellfield.devices.get("VW-001").state is State.OFFLINE
    assert [d.label for d in office.wellfield.roster(SITE)] == ["VW-002", "VW-003", "VW-004"]


def test_a_device_with_work_open_cannot_start_more(office: Office) -> None:
    office.wellfield.start_rework("VW-001", Rework.RAISE, STARTED)
    with pytest.raises(RuleError, match="already has work open"):
        office.wellfield.start_rework("VW-001", Rework.DEEPEN, dt.date(2025, 3, 5))


def test_an_abandoned_device_takes_no_work(office: Office) -> None:
    office.wellfield.abandon("VW-001", dt.date(2025, 2, 1))
    with pytest.raises(StateError):
        office.wellfield.start_rework("VW-001", Rework.RAISE, STARTED)


def test_finishing_a_raise_remeasures_the_device_and_puts_it_back(office: Office) -> None:
    job = office.wellfield.start_rework("VW-001", Rework.RAISE, STARTED)
    office.wellfield.finish_rework(
        job.label, dt.date(2025, 3, 20), depth=122.0, screen_top=52.0, screen_bottom=116.0
    )
    device = office.wellfield.devices.get("VW-001")
    assert device.state is State.CONNECTED
    assert device.total_depth == pytest.approx(122.0)
    assert device.screen_top == pytest.approx(52.0)


def test_a_finished_raise_puts_the_device_back_on_the_roster(office: Office) -> None:
    job = office.wellfield.start_rework("VW-001", Rework.RAISE, STARTED)
    office.wellfield.finish_rework(
        job.label, dt.date(2025, 3, 20), depth=122.0, screen_top=52.0, screen_bottom=116.0
    )
    assert len(office.wellfield.roster(SITE)) == 4


def test_a_repair_leaves_the_device_the_shape_it_was(office: Office) -> None:
    before = office.wellfield.devices.get("VW-001")
    job = office.wellfield.start_rework("VW-001", Rework.REPAIR, STARTED)
    office.wellfield.finish_rework(job.label, dt.date(2025, 3, 5), note="seal replaced")
    after = office.wellfield.devices.get("VW-001")
    assert after.total_depth == pytest.approx(before.total_depth)
    assert after.state is State.CONNECTED


def test_a_raise_finished_without_measurements_is_refused(office: Office) -> None:
    job = office.wellfield.start_rework("VW-001", Rework.RAISE, STARTED)
    with pytest.raises(RuleError, match="measured afterwards"):
        office.wellfield.finish_rework(job.label, dt.date(2025, 3, 20))


def test_work_past_the_window_is_listed(office: Office) -> None:
    office.wellfield.start_rework("VW-001", Rework.RAISE, STARTED)
    assert office.wellfield.overdue_rework(SITE, dt.date(2025, 4, 30)) == []
    late = office.wellfield.overdue_rework(SITE, dt.date(2025, 5, 1))
    assert [job.device for job in late] == ["VW-001"]


def test_a_run_can_be_closed_while_a_well_is_being_raised(office: Office) -> None:
    office.wellfield.start_rework("VW-001", Rework.RAISE, STARTED)
    run = walk_wellfield(office, dt.date(2025, 4, 8))
    assert office.monitoring.missing(run) == []


def test_the_history_of_a_device_carries_both_measurements(office: Office) -> None:
    job = office.wellfield.start_rework("VW-001", Rework.RAISE, STARTED)
    office.wellfield.finish_rework(
        job.label, dt.date(2025, 3, 20), depth=122.0, screen_top=52.0, screen_bottom=116.0
    )
    history = office.wellfield.rework_history("VW-001")
    assert len(history) == 1
    assert history[0].before_depth == pytest.approx(92.0)
    assert history[0].after_depth == pytest.approx(122.0)


def test_a_device_nothing_was_done_to_has_no_history(office: Office) -> None:
    assert office.wellfield.rework_history("VW-002") == []

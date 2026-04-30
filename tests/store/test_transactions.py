"""What happens to a book when work goes wrong half way through.

Every desk writes inside a transaction, and the reason is not tidiness. Posting
a run opens records, writes rechecks and moves stages, and a failure in the
middle of that leaves a book where a recheck exists against a record that was
never opened. Nothing later would notice.

These tests break each of those on purpose, in the middle, and then read the
book back to see what survived.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from gemwalk.errors import RuleError, StateError
from gemwalk.model.work import Job
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, furnish, walk_wellfield

APRIL = dt.date(2025, 4, 8)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


CLEAN: dict[str, float] = {
    "methane": 52.4,
    "carbon": 38.1,
    "oxygen": 0.6,
    "balance": 8.9,
    "temperature": 118.2,
    "static": -1.4,
    "applied": -12.0,
    "flow": 42.0,
    "valve_before": 3.0,
    "valve_after": 3.0,
}


def test_a_failure_part_way_through_a_run_leaves_no_readings(office: Office) -> None:
    run = office.monitoring.open_run(SITE, APRIL, monitor="D. Kasprzak", meter="GEM-1").label

    def half(fail: bool) -> None:
        with office.book.writing():
            office.monitoring.record(run, "VW-001", on=APRIL, **CLEAN)  # type: ignore[arg-type]
            if fail:
                office.wellfield.take_offline("VW-002", APRIL)
            office.monitoring.record(run, "VW-002", on=APRIL, **CLEAN)  # type: ignore[arg-type]

    with pytest.raises(StateError):
        half(True)
    assert office.monitoring.readings.of_run(run) == []
    assert office.wellfield.devices.get("VW-002").is_connected


def test_a_failed_intake_writes_nothing_at_all(office: Office) -> None:
    from gemwalk.service.intake import REQUIRED

    run = office.monitoring.open_run(SITE, APRIL, monitor="D. Kasprzak", meter="GEM-1").label
    heading = ",".join(("taken_on", *REQUIRED, "note"))
    sheet = (
        heading
        + "\n2025-04-08,VW-001,52.4,38.1,0.6,8.9,118.2,-1.4,-12.0,42.0,3.0,3.0,\n"
        + "2025-04-08,VW-999,52.4,38.1,0.6,8.9,118.2,-1.4,-12.0,42.0,3.0,3.0,\n"
    )
    with pytest.raises(RuleError):
        office.intake.take(run, sheet, on=APRIL, all_or_nothing=True)
    assert office.monitoring.readings.of_run(run) == []


def test_a_second_office_on_the_same_book_sees_committed_work(book: Book) -> None:
    first = furnish(Office(book))
    second = Office(book)
    assert second.wellfield.devices.count() == first.wellfield.devices.count()
    first.wellfield.abandon("VW-001", APRIL)
    assert not second.wellfield.devices.get("VW-001").is_connected


def test_work_survives_the_book_being_shut_and_opened(tmp_path: Path) -> None:
    path = tmp_path / "northridge.sqlite3"
    with Office.open(path) as office:
        furnish(office)
        run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
        office.compliance.post_run(run)
    with Office.open(path) as again:
        assert [e.label for e in again.compliance.exceedances.open_at(SITE)] == ["EX-2025-001"]
        assert again.monitoring.readings.of_run(run) != []


def test_a_nested_write_across_two_desks_lands_together(office: Office) -> None:
    with office.book.writing():
        office.work.raise_order(SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13))
        office.memos.write(
            "VW-001",
            dt.datetime(2025, 4, 8, 16, 20, tzinfo=dt.UTC),
            by_whom="D. K.",
            body="ticket raised",
        )
    assert office.work.orders.count() == 1
    assert len(office.memos.about("VW-001")) == 1


def test_a_nested_write_that_fails_takes_both_desks_back(office: Office) -> None:
    def both(fail: bool) -> None:
        with office.book.writing():
            office.work.raise_order(SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13))
            office.memos.write(
                "VW-001",
                dt.datetime(2025, 4, 8, 16, 20, tzinfo=dt.UTC),
                by_whom="D. K.",
                body="ticket raised",
            )
            if fail:
                raise RuleError("the crew", "went home")

    with pytest.raises(RuleError):
        both(True)
    assert office.work.orders.count() == 0
    assert office.memos.about("VW-001") == []


def test_a_label_handed_out_inside_a_failed_block_is_handed_out_again(
    office: Office,
) -> None:
    def raise_one(fail: bool) -> None:
        with office.book.writing():
            office.work.raise_order(SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13))
            if fail:
                raise RuleError("the crew", "went home")

    with pytest.raises(RuleError):
        raise_one(True)
    raise_one(False)
    assert office.work.orders.labels() == ["WO-2025-0001"]


def test_posting_a_run_twice_is_refused_and_changes_nothing(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    office.compliance.post_run(run)
    before = office.compliance.exceedances.count()
    posting = office.compliance.post_run(run)
    assert posting.opened == []
    assert office.compliance.exceedances.count() == before


def test_the_book_is_not_left_in_a_transaction_after_a_failure(office: Office) -> None:
    def fail(should: bool) -> None:
        with office.book.writing():
            if should:
                raise RuleError("the crew", "went home")

    with pytest.raises(RuleError):
        fail(True)
    assert not office.book.in_transaction
    office.wellfield.abandon("VW-001", APRIL)
    assert office.wellfield.devices.get("VW-001").abandoned_on == APRIL

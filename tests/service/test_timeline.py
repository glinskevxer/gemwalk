"""Everything that ever happened to one well, in the order it happened."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import UnknownError
from gemwalk.model.rework import Rework
from gemwalk.model.work import Job
from gemwalk.service.office import Office
from gemwalk.service.timeline import Event, TimelineDesk
from gemwalk.store.book import Book
from gemwalk.units import Temperature
from tests.support import SITE, ZONE, furnish, walk_wellfield

APRIL = dt.date(2025, 4, 8)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def kinds(events: list[Event]) -> list[str]:
    return [event.kind for event in events]


def test_a_new_well_has_been_drilled_and_wired(office: Office) -> None:
    story = office.timeline.of_device("VW-001")
    assert kinds(story) == ["drilled", "connected"]
    assert "vertical well into A-03" in story[0].said


def test_the_story_is_in_date_order(office: Office) -> None:
    walk_wellfield(office, APRIL)
    story = office.timeline.of_device("VW-001")
    assert [event.on for event in story] == sorted(event.on for event in story)


def test_a_reading_is_on_the_story(office: Office) -> None:
    walk_wellfield(office, APRIL)
    story = office.timeline.of_device("VW-001")
    assert "read" in kinds(story)
    assert any("52.4% methane" in event.said for event in story)


def test_a_finding_and_its_recheck_are_both_on_it(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    office.compliance.post_run(run)
    office.compliance.recheck("EX-2025-001", dt.date(2025, 4, 10), 128.0, clear=True)
    story = office.timeline.of_device("VW-002")
    assert "finding" in kinds(story)
    assert "recheck" in kinds(story)
    assert "closed" in kinds(story)


def test_a_tape_drop_says_how_much_of_the_screen_was_under(office: Office) -> None:
    office.liquids.tape("VW-001", APRIL, 54.0)
    story = office.timeline.of_device("VW-001")
    assert any("50% of the screen under" in event.said for event in story)


def test_a_raise_is_on_the_story_at_both_ends(office: Office) -> None:
    job = office.wellfield.start_rework("VW-001", Rework.RAISE, dt.date(2025, 3, 1))
    office.wellfield.finish_rework(
        job.label, dt.date(2025, 3, 20), depth=122.0, screen_top=52.0, screen_bottom=116.0
    )
    story = office.timeline.of_device("VW-001")
    said = [event.said for event in story if event.kind == "work"]
    assert said == ["raise started", "raise finished, 30 ft taller"]


def test_an_order_is_on_the_story(office: Office) -> None:
    office.work.raise_order(SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13))
    office.work.finish("WO-2025-0001", dt.date(2025, 4, 11))
    story = office.timeline.of_device("VW-001")
    assert kinds(story).count("order") == 2


def test_a_note_is_on_the_story(office: Office) -> None:
    office.memos.write(
        "VW-001", read_moment("2025-04-08 16:20", ZONE), by_whom="D. K.", body="valve seized"
    )
    story = office.timeline.of_device("VW-001")
    assert any("D. K.: valve seized" in event.said for event in story)


def test_an_approval_and_an_abandonment_are_on_it(office: Office) -> None:
    office.wellfield.approve_higher_temperature("VW-001", Temperature(145.0), APRIL)
    office.wellfield.abandon("VW-001", dt.date(2026, 1, 8))
    story = office.timeline.of_device("VW-001")
    assert "approval" in kinds(story)
    assert "abandoned" in kinds(story)


def test_the_story_can_be_narrowed_to_a_range(office: Office) -> None:
    walk_wellfield(office, APRIL)
    inside = office.timeline.between("VW-001", APRIL, APRIL)
    assert kinds(inside) == ["read"]
    assert office.timeline.between("VW-001", dt.date(2030, 1, 1), dt.date(2030, 12, 31)) == []


def test_the_kinds_come_back_most_first(office: Office) -> None:
    walk_wellfield(office, APRIL)
    walk_wellfield(office, dt.date(2025, 5, 6))
    tally = office.timeline.kinds("VW-001")
    assert next(iter(tally)) == "read"
    assert tally["read"] == 2


def test_the_story_of_something_that_is_not_a_device_is_refused(office: Office) -> None:
    with pytest.raises(UnknownError, match="area"):
        office.timeline.of_subject("A-03")


def test_the_story_of_a_label_the_book_never_issued_is_refused(office: Office) -> None:
    with pytest.raises(UnknownError):
        office.timeline.of_subject("VW-999")


def test_a_device_label_finds_its_own_story(office: Office) -> None:
    assert office.timeline.of_subject("VW-001") == office.timeline.of_device("VW-001")


def test_an_event_prints_the_line_the_report_uses(office: Office) -> None:
    story = office.timeline.of_device("VW-001")
    assert str(story[0]).startswith("2021-05-12  drilled")


def test_the_office_makes_one_timeline_desk(office: Office) -> None:
    assert isinstance(office.timeline, TimelineDesk)
    assert office.timeline is office.timeline


def test_a_tally_counts_only_the_events_it_was_given(office: Office) -> None:
    from gemwalk.service.timeline import count_kinds

    walk_wellfield(office, APRIL)
    whole = office.timeline.of_device("VW-001")
    part = office.timeline.between("VW-001", APRIL, APRIL)
    assert count_kinds(part) == {"read": 1}
    assert count_kinds(whole) != count_kinds(part)

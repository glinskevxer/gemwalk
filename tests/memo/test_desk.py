"""Writing a note and finding it again."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import UnknownError
from gemwalk.model.memo import About
from gemwalk.report.device import device_report
from gemwalk.service.memos import MemoDesk
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, ZONE, furnish, walk_wellfield

AT = read_moment("2025-04-08 16:20", ZONE)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def test_a_label_the_book_never_issued_is_not_about_anything(office: Office) -> None:
    with pytest.raises(UnknownError, match="VW-999"):
        office.memos.kind_of("VW-999")


def test_the_desk_works_out_what_a_label_is(office: Office) -> None:
    assert office.memos.kind_of("VW-001") == (About.DEVICE, SITE)
    assert office.memos.kind_of("A-03") == (About.AREA, SITE)
    assert office.memos.kind_of("CD-01") == (About.CONTROL, SITE)
    assert office.memos.kind_of(SITE) == (About.SITE, SITE)


def test_a_record_and_a_run_are_told_apart(office: Office) -> None:
    run = walk_wellfield(office, dt.date(2025, 4, 8), {"VW-002": {"temperature": 138.0}})
    record = office.compliance.post_run(run).opened[0]
    assert office.memos.kind_of(run) == (About.RUN, SITE)
    assert office.memos.kind_of(record) == (About.RECORD, SITE)


def test_a_note_takes_the_kind_from_the_label(office: Office) -> None:
    memo = office.memos.write("VW-001", AT, by_whom="D. Kasprzak", body="valve seized")
    assert memo.about is About.DEVICE
    assert memo.site == SITE


def test_notes_about_one_thing_come_back_oldest_first(office: Office) -> None:
    office.memos.write("VW-001", AT, by_whom="D. K.", body="first")
    office.memos.write(
        "VW-001", read_moment("2025-05-08 09:00", ZONE), by_whom="D. K.", body="second"
    )
    assert [m.body for m in office.memos.about("VW-001")] == ["first", "second"]


def test_a_thing_nobody_wrote_about_has_no_notes(office: Office) -> None:
    assert office.memos.about("VW-002") == []


def test_a_note_is_found_by_a_word_it_says(office: Office) -> None:
    office.memos.write("VW-001", AT, by_whom="D. K.", body="valve seized, freed with a wrench")
    office.memos.write("A-03", AT, by_whom="D. K.", body="ponding after the storm")
    assert [m.subject for m in office.memos.find(SITE, "WRENCH")] == ["VW-001"]
    assert [m.subject for m in office.memos.find(SITE, "storm")] == ["A-03"]
    assert office.memos.find(SITE, "badger") == []


def test_the_recent_notes_come_back_newest_first(office: Office) -> None:
    office.memos.write("VW-001", AT, by_whom="D. K.", body="first")
    office.memos.write(
        "A-03", read_moment("2025-05-08 09:00", ZONE), by_whom="D. K.", body="second"
    )
    assert [m.body for m in office.memos.recent(SITE)] == ["second", "first"]
    assert [m.body for m in office.memos.recent(SITE, 1)] == ["second"]


def test_a_site_with_no_notes_has_no_counts(office: Office) -> None:
    assert office.memos.counts(SITE) == {}
    assert office.memos.recent(SITE) == []


def test_the_counts_only_name_the_kinds_that_have_notes(office: Office) -> None:
    office.memos.write("VW-001", AT, by_whom="D. K.", body="one")
    office.memos.write("A-03", AT, by_whom="D. K.", body="two")
    assert office.memos.counts(SITE) == {"device": 1, "area": 1}


def test_the_notes_of_one_kind_come_back_together(office: Office) -> None:
    office.memos.write("VW-001", AT, by_whom="D. K.", body="one")
    office.memos.write("A-03", AT, by_whom="D. K.", body="two")
    assert [m.subject for m in office.memos.of_kind(SITE, About.AREA)] == ["A-03"]


def test_the_well_card_carries_the_notes(office: Office) -> None:
    office.memos.write("VW-001", AT, by_whom="D. Kasprzak", body="valve seized")
    section = device_report(office, "VW-001", on=dt.date(2025, 4, 30)).find(
        "what anybody wrote down about it"
    )
    assert section is not None
    body = "\n".join(section.lines())
    assert "valve seized" in body
    assert "D. Kasprzak" in body


def test_a_well_nobody_wrote_about_says_so(office: Office) -> None:
    section = device_report(office, "VW-001", on=dt.date(2025, 4, 30)).find(
        "what anybody wrote down about it"
    )
    assert section is not None
    assert "nobody has written anything down" in "\n".join(section.lines())


def test_the_office_makes_one_note_desk(office: Office) -> None:
    assert isinstance(office.memos, MemoDesk)
    assert office.memos is office.memos
    assert office.memos.book is office.book

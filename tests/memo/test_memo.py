"""A note against anything in the book."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import RuleError
from gemwalk.model.memo import About, Memo
from gemwalk.store.book import Book
from gemwalk.store.memos import MemoRepository
from tests.support import SITE, ZONE, bare

AT = "2025-04-08 16:20"


def a_memo(**changes: object) -> Memo:
    fields: dict[str, object] = {
        "site": SITE,
        "about": About.DEVICE,
        "subject": "VW-001",
        "at": read_moment(AT, ZONE),
        "by_whom": "D. Kasprzak",
        "body": "valve seized, freed with a wrench\nwants a new stem next visit",
    }
    fields.update(changes)
    return Memo(**fields)  # type: ignore[arg-type]


@pytest.fixture
def memos(book: Book) -> MemoRepository:
    bare(book)
    return MemoRepository(book)


def test_a_note_is_about_something_and_says_something() -> None:
    with pytest.raises(RuleError, match="about something"):
        a_memo(subject="  ")
    with pytest.raises(RuleError, match="written by somebody"):
        a_memo(by_whom="")
    with pytest.raises(RuleError, match="not a note"):
        a_memo(body="   ")


def test_a_note_is_stamped_with_an_offset() -> None:
    with pytest.raises(RuleError, match="offset"):
        a_memo(at=dt.datetime(2025, 4, 8, 16, 20))  # noqa: DTZ001


def test_a_note_hands_back_its_first_line() -> None:
    assert a_memo().first_line == "valve seized, freed with a wrench"


def test_a_note_prints_what_it_is_about() -> None:
    assert str(a_memo()).startswith("device VW-001: valve seized")


def test_a_note_finds_a_word_whatever_case_it_was_written_in() -> None:
    memo = a_memo()
    assert memo.mentions("WRENCH")
    assert memo.mentions("vw-001")
    assert not memo.mentions("badger")


def test_a_note_round_trips(memos: MemoRepository) -> None:
    stored = memos.add(a_memo())
    assert stored.id > 0
    assert memos.get(str(stored.id)) == stored


def test_notes_about_one_thing_come_back_oldest_first(memos: MemoRepository) -> None:
    memos.add(a_memo(at=read_moment("2025-05-08 09:00", ZONE), body="second"))
    memos.add(a_memo(body="first"))
    assert [m.body for m in memos.about_subject("VW-001")] == ["first", "second"]


def test_notes_come_back_by_the_kind_of_thing(memos: MemoRepository) -> None:
    memos.add(a_memo())
    memos.add(a_memo(about=About.AREA, subject="A-03", body="ponding after the storm"))
    assert [m.subject for m in memos.of_kind(SITE, About.AREA)] == ["A-03"]
    assert len(memos.of_site(SITE)) == 2


def test_notes_come_back_by_a_word_they_say(memos: MemoRepository) -> None:
    memos.add(a_memo())
    memos.add(a_memo(subject="A-03", about=About.AREA, body="ponding after the storm"))
    assert [m.subject for m in memos.saying(SITE, "PONDING")] == ["A-03"]
    assert [m.subject for m in memos.saying(SITE, "vw-001")] == ["VW-001"]
    assert memos.saying(SITE, "badger") == []


def test_two_notes_can_say_the_same_thing(memos: MemoRepository) -> None:
    memos.add(a_memo())
    memos.add(a_memo())
    assert memos.count() == 2


def test_a_note_about_a_site_is_allowed(memos: MemoRepository) -> None:
    stored = memos.add(a_memo(about=About.SITE, subject=SITE, body="called the state"))
    assert stored.about is About.SITE


def test_every_kind_of_thing_a_note_can_be_about_prints(memos: MemoRepository) -> None:
    assert str(About.ORDER) == "work order"
    assert len({str(kind) for kind in About}) == len(About)
    del memos


def test_each_note_gets_a_number_of_its_own(memos: MemoRepository) -> None:
    first = memos.add(a_memo())
    second = memos.add(a_memo())
    assert first.id != second.id
    assert memos.count() == 2

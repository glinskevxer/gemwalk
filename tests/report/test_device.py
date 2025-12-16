"""The well card."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.model.work import Job
from gemwalk.report.device import device_report
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from gemwalk.units import Temperature
from tests.support import furnish, walk_wellfield

APRIL = dt.date(2025, 4, 8)
MAY = dt.date(2025, 5, 6)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def text_of(office: Office, heading: str, label: str = "VW-002") -> str:
    section = device_report(office, label, on=dt.date(2025, 5, 10)).find(heading)
    assert section is not None
    return "\n".join(section.lines())


def test_the_card_names_the_device_and_its_standard(office: Office) -> None:
    report = device_report(office, "VW-001", on=APRIL)
    assert report.title == "VW-001 well card"
    assert "subpart XXX" in report.subtitle
    assert "vertical well" in report.subtitle


def test_the_construction_is_at_the_top(office: Office) -> None:
    body = text_of(office, "how it was built", "VW-001")
    assert "64.0 ft of slot" in body
    assert "screened from 22.0 to 86.0 ft" in body
    assert "held to the standard's 131.0 F" in body


def test_an_approval_shows_on_the_card(office: Office) -> None:
    office.wellfield.approve_higher_temperature("VW-001", Temperature(145.0), APRIL)
    body = text_of(office, "how it was built", "VW-001")
    assert "held to 145.0 F by an approval dated 2025-04-08" in body


def test_a_device_off_the_run_says_how_long_it_has(office: Office) -> None:
    office.wellfield.take_offline("VW-001", dt.date(2025, 4, 20))
    body = text_of(office, "how it was built", "VW-001")
    assert "off the run since 2025-04-20" in body
    assert "60 day window" in body


def test_a_wellhead_never_read_says_so(office: Office) -> None:
    assert "never been read" in text_of(office, "what it has read", "VW-001")


def test_every_reading_is_on_the_card_oldest_first(office: Office) -> None:
    walk_wellfield(office, APRIL)
    walk_wellfield(office, MAY, {"VW-002": {"temperature": 138.0}})
    body = text_of(office, "what it has read")
    assert body.index("2025-04-08") < body.index("2025-05-06")
    assert "temperature" in body


def test_the_card_says_which_way_the_well_has_been_going(office: Office) -> None:
    walk_wellfield(office, APRIL)
    walk_wellfield(office, MAY, {"VW-002": {"methane": 44.0, "flow": 18.0}})
    body = text_of(office, "what it has read")
    assert "methane has gone from 52.4% to 44.0%" in body
    assert "flow from 42.0 scfm to 18.0 scfm" in body


def test_one_reading_is_not_a_trend(office: Office) -> None:
    walk_wellfield(office, APRIL)
    assert "has gone from" not in text_of(office, "what it has read")


def test_a_wellhead_never_written_up_says_so(office: Office) -> None:
    assert "never been written up" in text_of(office, "what it has been written up for")


def test_a_finding_is_on_the_card_with_its_window(office: Office) -> None:
    office.compliance.post_run(walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}}))
    body = text_of(office, "what it has been written up for")
    assert "EX-2025-001" in body
    assert "138.0" in body
    assert "131.0" in body
    assert "2025-04-13" in body


def test_the_card_counts_what_is_open_and_late(office: Office) -> None:
    office.compliance.post_run(walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}}))
    body = text_of(office, "what it has been written up for")
    assert "1 open, 1 of them past their window" in body


def test_a_closed_finding_shows_the_day_it_closed(office: Office) -> None:
    office.compliance.post_run(walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}}))
    office.compliance.recheck("EX-2025-001", dt.date(2025, 4, 10), 128.0, clear=True)
    body = text_of(office, "what it has been written up for")
    assert "2025-04-10" in body
    assert "1 open" not in body


def test_a_wellhead_never_tapped_says_so(office: Office) -> None:
    assert "no tape drop on file" in text_of(office, "what has been standing in it")


def test_a_tape_drop_is_on_the_card(office: Office) -> None:
    office.liquids.tape("VW-002", dt.date(2025, 4, 7), 54.0, pumped=True)
    body = text_of(office, "what has been standing in it")
    assert "50%" in body
    assert "yes" in body


def test_a_wellhead_nobody_was_sent_to_says_so(office: Office) -> None:
    assert "nobody has ever been sent" in text_of(office, "who has been sent to it")


def test_an_order_is_on_the_card_with_the_record_behind_it(office: Office) -> None:
    office.compliance.post_run(walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}}))
    office.work.raise_for_exceedance("EX-2025-001", Job.WELLHEAD, dt.date(2025, 4, 9))
    body = text_of(office, "who has been sent to it")
    assert "WO-2025-0001" in body
    assert "EX-2025-001" in body
    assert "repair the wellhead" in body


def test_the_whole_card_renders(office: Office) -> None:
    walk_wellfield(office, APRIL)
    text = device_report(office, "VW-001", on=APRIL).render()
    assert text.endswith("\n")
    for heading in (
        "how it was built",
        "what it has read",
        "what it has been written up for",
        "what has been standing in it",
        "who has been sent to it",
    ):
        assert heading in text

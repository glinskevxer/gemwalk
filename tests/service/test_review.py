"""Reading a book for what is true of it and should not be."""

from __future__ import annotations

import datetime as dt
from dataclasses import replace

import pytest

from gemwalk.errors import UnknownError
from gemwalk.model.work import Job
from gemwalk.service.office import Office
from gemwalk.service.review import Weight, review, serious
from gemwalk.store.book import Book
from tests.support import SITE, bare, furnish, walk_wellfield

APRIL = dt.date(2025, 4, 8)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def about(office: Office) -> set[str]:
    return {finding.about for finding in review(office, SITE)}


def said(office: Office) -> str:
    return "\n".join(str(finding) for finding in review(office, SITE))


def test_a_furnished_site_with_a_flare_looks_right(office: Office) -> None:
    assert review(office, SITE) == []


def test_a_site_the_book_never_issued_is_refused(office: Office) -> None:
    with pytest.raises(UnknownError):
        review(office, "SOUTHFORK")


def test_a_bare_site_is_short_of_nearly_everything(book: Book) -> None:
    bare(book, areas=False)
    found = review(Office(book), SITE)
    assert {finding.about for finding in found} == {SITE}
    assert len(found) == 3


def test_a_site_with_nothing_to_burn_the_gas_is_serious(book: Book) -> None:
    office = furnish(Office(book))
    office.plant.retire("CD-01", dt.date(2026, 1, 1))
    assert any(
        finding.weight is Weight.SERIOUS and "burn the gas" in finding.said
        for finding in review(office, SITE)
    )


def test_a_wellhead_on_the_run_piped_to_nothing_is_serious(office: Office) -> None:
    made = office.wellfield.drill(
        SITE,
        "A-03",
        station="N 20+00",
        total_depth=90.0,
        screen_top=20.0,
        screen_bottom=84.0,
        on=dt.date(2025, 4, 2),
    )
    office.wellfield.connect(made.label, dt.date(2025, 4, 3))
    assert made.label in about(office)
    assert "piped to nothing" in said(office)


def test_a_reading_before_the_well_was_wired_is_odd(office: Office) -> None:
    run = office.monitoring.open_run(SITE, APRIL, monitor="D. K.", meter="GEM-1").label
    office.monitoring.record(
        run,
        "VW-001",
        on=APRIL,
        methane=52.4,
        carbon=38.1,
        oxygen=0.6,
        balance=8.9,
        temperature=118.2,
        static=-1.4,
        applied=-12.0,
        flow=42.0,
        valve_before=3.0,
        valve_after=3.0,
    )
    office.monitoring.close_run(run, APRIL, note="the rest another day")
    device = office.wellfield.devices.get("VW-001")
    office.wellfield.devices.put(replace(device, connected_on=dt.date(2025, 5, 1)))
    assert "before it was wired up" in said(office)


def test_a_record_open_against_an_abandoned_well_is_serious(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    record = office.compliance.post_run(run).opened[0]
    office.wellfield.abandon("VW-002", dt.date(2025, 4, 20))
    assert record in about(office)
    assert "which was abandoned" in said(office)


def test_an_order_still_open_against_a_closed_record_is_odd(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    record = office.compliance.post_run(run).opened[0]
    office.work.raise_for_exceedance(record, Job.WELLHEAD, dt.date(2025, 4, 9))
    office.compliance.recheck(record, dt.date(2025, 4, 10), 128.0, clear=True)
    assert "which closed on" in said(office)
    assert serious(office, SITE) == []


def test_an_order_raised_off_something_that_is_gone_is_serious(office: Office) -> None:
    office.work.raise_order(
        SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13), because="EX-1999-001"
    )
    assert "which is gone" in said(office)
    assert len(serious(office, SITE)) == 1


def test_an_open_run_and_an_open_walk_are_both_odd(office: Office) -> None:
    office.monitoring.open_run(SITE, APRIL, monitor="D. K.", meter="GEM-1")
    office.surface.open_walk(
        SITE,
        APRIL,
        monitor="T. W.",
        instrument="TVA-1",
        background=2.0,
        wind_mean=3.4,
        wind_gust=7.1,
    )
    body = said(office)
    assert "still open since" in body
    assert len([f for f in review(office, SITE) if f.weight is Weight.ODD]) == 2


def test_the_serious_findings_come_first(office: Office) -> None:
    office.monitoring.open_run(SITE, APRIL, monitor="D. K.", meter="GEM-1")
    office.work.raise_order(
        SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13), because="EX-1999-001"
    )
    found = review(office, SITE)
    assert found[0].weight is Weight.SERIOUS


def test_a_finding_prints_the_line_the_desk_reads(office: Office) -> None:
    office.work.raise_order(
        SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13), because="EX-1999-001"
    )
    assert str(review(office, SITE)[0]).startswith("serious: WO-2025-0001")


def test_a_weight_prints_the_word_the_report_uses() -> None:
    assert str(Weight.SERIOUS) == "serious"
    assert str(Weight.ODD) == "odd"

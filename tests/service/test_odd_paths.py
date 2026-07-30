"""The paths a tidy site never takes.

Everything here is a branch that only runs when something has gone wrong, been
typed in off old paper, or been fixed in one place and not another. They are
the branches that run on the worst day, so they are the ones worth being sure
about.
"""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import RuleError, StateError, UnknownError
from gemwalk.model.fault import Damage
from gemwalk.model.instrument import Meter
from gemwalk.model.memo import About
from gemwalk.model.rework import Job as ReworkJob
from gemwalk.model.rework import Rework
from gemwalk.model.work import Job
from gemwalk.service.office import Office
from gemwalk.service.review import Weight, review
from gemwalk.store.book import Book
from gemwalk.store.plant import stamp, unstamp
from tests.support import SITE, ZONE, furnish, walk_cover, walk_wellfield

APRIL = dt.date(2025, 4, 8)
MAY = dt.date(2025, 5, 13)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def test_a_note_can_land_against_a_run_a_walk_and_an_order(office: Office) -> None:
    run = walk_wellfield(office, APRIL)
    walk = walk_cover(office, MAY, finish=False)
    order = office.work.raise_order(
        SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13)
    ).label
    assert office.memos.kind_of(run) == (About.RUN, SITE)
    assert office.memos.kind_of(walk) == (About.WALK, SITE)
    assert office.memos.kind_of(order) == (About.ORDER, SITE)


def test_a_note_can_land_against_a_surface_spot(office: Office) -> None:
    walk_cover(office, MAY, (("A-03", "grid 14-J", 720.0),))
    assert office.memos.kind_of("SH-2025Q2-001") == (About.SPOT, SITE)


def test_an_order_off_a_spot_with_no_window_left_is_refused(office: Office) -> None:
    walk_cover(office, MAY, (("A-03", "grid 14-J", 720.0),))
    office.surface.repair("SH-2025Q2-001", dt.date(2025, 5, 16))
    office.surface.remonitor("SH-2025Q2-001", dt.date(2025, 5, 20), 180.0)
    with pytest.raises(RuleError, match="closed"):
        office.work.raise_for_hit("SH-2025Q2-001", Job.COVER, dt.date(2025, 5, 21))


def test_a_cancelled_order_leaves_the_crew_load(office: Office) -> None:
    order = office.work.raise_order(
        SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13)
    ).label
    office.work.assign(order, "north crew", APRIL)
    assert office.work.crew_load(SITE, APRIL) == {"north crew": 1}
    office.work.cancel(order, dt.date(2025, 4, 9), "not needed")
    assert office.work.crew_load(SITE, APRIL) == {}


def test_an_order_assigned_after_the_day_asked_about_is_not_counted(office: Office) -> None:
    order = office.work.raise_order(
        SITE, Job.VALVE, "VW-001", on=dt.date(2025, 6, 1), due=dt.date(2025, 6, 10)
    ).label
    office.work.assign(order, "north crew", dt.date(2025, 6, 1))
    assert office.work.crew_load(SITE, APRIL) == {}


def test_a_rework_job_measured_but_not_finished_is_refused() -> None:
    with pytest.raises(RuleError, match="when the work is finished"):
        ReworkJob(
            label="RW-1",
            device="VW-001",
            site=SITE,
            kind=Rework.RAISE,
            started_on=APRIL,
            before_depth=92.0,
            before_top=22.0,
            before_bottom=86.0,
            after_depth=122.0,
        )


def test_a_moment_that_cannot_be_blank_refuses_to_be(office: Office) -> None:
    from gemwalk.errors import DesignError

    with pytest.raises(DesignError, match="was blank"):
        stamp(None)  # type: ignore[arg-type]
    with pytest.raises(DesignError, match="is not a moment"):
        unstamp("half nine")
    assert unstamp(stamp(read_moment("2025-04-08 06:30", ZONE))) is not None


def test_a_lateral_of_a_site_that_is_not_its_own_is_refused(office: Office) -> None:
    office.sites.open_site(
        "SOUTHFORK",
        "Southfork",
        subpart="WWW",
        permit="MSW-2",
        zone=ZONE,
        design_capacity=3_100_000.0,
        opened_on=dt.date(1994, 2, 1),
    )
    other = office.piping.lay_header(
        "SOUTHFORK",
        "south trunk",
        diameter=18.0,
        material="HDPE SDR17",
        length_feet=100.0,
        on=dt.date(2019, 9, 3),
    ).label
    with pytest.raises(RuleError, match="not a header at"):
        office.piping.lay_lateral(
            SITE,
            other,
            diameter=8.0,
            material="HDPE SDR17",
            length_feet=1.0,
            on=dt.date(2019, 9, 3),
        )


def test_a_lateral_off_a_pulled_header_is_refused(office: Office) -> None:
    header = office.piping.lay_header(
        SITE,
        "spare",
        diameter=18.0,
        material="HDPE SDR17",
        length_feet=100.0,
        on=dt.date(2019, 9, 3),
    ).label
    office.piping.retire_header(header, dt.date(2024, 6, 1))
    with pytest.raises(StateError):
        office.piping.lay_lateral(
            SITE,
            header,
            diameter=8.0,
            material="HDPE SDR17",
            length_feet=1.0,
            on=dt.date(2024, 7, 1),
        )


def test_a_record_open_against_a_device_that_is_gone_is_serious(office: Office) -> None:
    run = walk_wellfield(office, APRIL, {"VW-002": {"temperature": 138.0}})
    record = office.compliance.post_run(run).opened[0]
    office.compliance.exceedances.book.execute("PRAGMA foreign_keys = OFF")
    office.compliance.exceedances.book.execute(
        "UPDATE exceedance SET device = 'VW-999' WHERE label = ?", (record,)
    )
    office.compliance.exceedances.book.execute("PRAGMA foreign_keys = ON")
    said = [str(finding) for finding in review(office, SITE)]
    assert any("open against no device" in line for line in said)


def test_a_fault_in_an_area_that_is_gone_is_serious(office: Office) -> None:
    office.surface.find_fault(
        "A-03", Damage.CRACK, "grid 14-J", extent=2.0, on=MAY, found_by="T. W."
    )
    office.surface.faults.book.execute("PRAGMA foreign_keys = OFF")
    office.surface.faults.book.execute("UPDATE fault SET area = 'A-99'")
    office.surface.faults.book.execute("PRAGMA foreign_keys = ON")
    found = [f for f in review(office, SITE) if f.weight is Weight.SERIOUS]
    assert any("which is gone" in str(f) for f in found)


def test_a_reading_before_the_well_was_drilled_is_serious(office: Office) -> None:
    run = walk_wellfield(office, APRIL)
    office.monitoring.readings.book.execute(
        "UPDATE reading SET taken_on = '2019-01-01' WHERE device = 'VW-001'"
    )
    del run
    said = [str(finding) for finding in review(office, SITE)]
    assert any("before it was drilled" in line for line in said)


def test_a_tape_below_the_bottom_of_the_hole_is_serious(office: Office) -> None:
    office.liquids.tape("VW-001", APRIL, 80.0)
    office.liquids.levels.book.execute("UPDATE level SET depth = 400.0")
    said = [str(finding) for finding in review(office, SITE)]
    assert any("below the bottom" in line for line in said)


def test_a_meter_that_was_never_in_service_on_the_day_is_not_due(office: Office) -> None:
    office.instruments.add(
        "GEM-2",
        SITE,
        kind=Meter.ANALYSER,
        maker="Verrick",
        model="GEM5000",
        serial="2",
        on=dt.date(2026, 1, 1),
    )
    assert office.instruments.due(SITE, APRIL) == []


def test_a_label_the_book_never_issued_is_about_nothing(office: Office) -> None:
    with pytest.raises(UnknownError):
        office.memos.kind_of("QQ-404")

"""Posting a run into the compliance records."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import RuleError, StateError
from gemwalk.model.exceedance import Stage
from gemwalk.rules import Finding
from gemwalk.service.compliance import ComplianceDesk
from gemwalk.service.monitoring import MonitoringDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.store.book import Book

APRIL = dt.date(2025, 4, 8)


@pytest.fixture
def desk(book: Book) -> ComplianceDesk:
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
    wells = WellfieldDesk(book)
    for _ in range(2):
        made = wells.drill(
            "NORTHRIDGE",
            "A-03",
            station="N 12+40",
            total_depth=92.0,
            screen_top=22.0,
            screen_bottom=86.0,
            on=dt.date(2021, 5, 12),
        )
        wells.connect(made.label, dt.date(2021, 6, 2))
    return ComplianceDesk(book)


def walk(desk: ComplianceDesk, on: dt.date, **readings: dict[str, float]) -> str:
    monitoring: MonitoringDesk = desk.monitoring
    run = monitoring.open_run("NORTHRIDGE", on, monitor="D. Kasprzak", meter="GEM-40912").label
    for device, changes in readings.items():
        fields: dict[str, float] = {
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
        fields.update(changes)
        monitoring.record(run, device, on=on, **fields)  # type: ignore[arg-type]
    monitoring.close_run(run, on, note="only the wellheads on this sheet")
    return run


def test_a_hot_wellhead_opens_one_record(desk: ComplianceDesk) -> None:
    run = walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}})
    posting = desk.post_run(run)
    assert posting.opened == ["EX-2025-001"]
    found = desk.exceedances.get("EX-2025-001")
    assert found.kind is Finding.TEMPERATURE
    assert found.opened_on == APRIL
    assert found.value == pytest.approx(138.0)


def test_a_clean_run_opens_nothing(desk: ComplianceDesk) -> None:
    run = walk(desk, APRIL, **{"VW-001": {}})
    posting = desk.post_run(run)
    assert posting.opened == []
    assert posting.touched == 0


def test_a_second_hot_reading_does_not_open_a_second_record(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    later = walk(desk, dt.date(2025, 5, 6), **{"VW-001": {"temperature": 136.0}})
    posting = desk.post_run(later)
    assert posting.opened == []
    assert posting.continued == ["EX-2025-001"]
    assert desk.exceedances.count() == 1


def test_the_clock_still_runs_off_the_first_reading(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    desk.post_run(walk(desk, dt.date(2025, 4, 12), **{"VW-001": {"temperature": 136.0}}))
    assert desk.exceedances.get("EX-2025-001").opened_on == APRIL


def test_a_reading_past_the_first_window_moves_the_record_on(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    posting = desk.post_run(walk(desk, dt.date(2025, 4, 20), **{"VW-001": {"temperature": 136.0}}))
    assert posting.escalated == ["EX-2025-001"]
    assert desk.exceedances.get("EX-2025-001").stage is Stage.ACTION


def test_a_clean_reading_closes_the_record(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    posting = desk.post_run(walk(desk, dt.date(2025, 4, 12), **{"VW-001": {}}))
    assert posting.closed == ["EX-2025-001"]
    found = desk.exceedances.get("EX-2025-001")
    assert not found.is_open
    assert found.closed_on == dt.date(2025, 4, 12)


def test_every_recheck_is_written_down(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    desk.post_run(walk(desk, dt.date(2025, 4, 12), **{"VW-001": {"temperature": 134.0}}))
    desk.post_run(walk(desk, dt.date(2025, 4, 20), **{"VW-001": {}}))
    walked = desk.rechecks.of_exceedance("EX-2025-001")
    assert [r.clear for r in walked] == [False, True]
    assert [r.value for r in walked] == pytest.approx([134.0, 118.2])


def test_two_wellheads_over_open_two_records(desk: ComplianceDesk) -> None:
    run = walk(
        desk,
        APRIL,
        **{"VW-001": {"temperature": 138.0}, "VW-002": {"static": 0.4}},
    )
    posting = desk.post_run(run)
    assert sorted(posting.opened) == ["EX-2025-001", "EX-2025-002"]
    assert desk.open_kinds("NORTHRIDGE")["temperature"] == 1
    assert desk.open_kinds("NORTHRIDGE")["pressure"] == 1


def test_one_wellhead_over_on_two_limits_opens_two_records(desk: ComplianceDesk) -> None:
    run = walk(desk, APRIL, **{"VW-001": {"temperature": 138.0, "oxygen": 7.0, "balance": 2.5}})
    posting = desk.post_run(run)
    assert len(posting.opened) == 2
    kinds = {e.kind for e in desk.exceedances.open_on_device("VW-001")}
    assert kinds == {Finding.TEMPERATURE, Finding.OXYGEN}


def test_a_clean_nitrogen_reading_closes_an_open_oxygen_clock(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"oxygen": 7.0, "balance": 2.5}}))
    desk.sites.elect("NORTHRIDGE", dt.date(2025, 4, 20), nitrogen_alternative=True)
    posting = desk.post_run(
        walk(desk, dt.date(2025, 5, 6), **{"VW-001": {"oxygen": 7.0, "balance": 12.0}})
    )
    assert posting.closed == ["EX-2025-001"]


def test_a_field_recheck_off_a_run_closes_the_record(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    closed = desk.recheck("EX-2025-001", dt.date(2025, 4, 11), 128.0, clear=True, note="turned in")
    assert not closed.is_open
    assert closed.note == "turned in"


def test_a_field_recheck_that_is_still_over_moves_the_stage(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    after = desk.recheck("EX-2025-001", dt.date(2025, 4, 20), 136.0, clear=False)
    assert after.stage is Stage.ACTION


def test_a_recheck_against_a_closed_record_is_refused(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    desk.recheck("EX-2025-001", dt.date(2025, 4, 11), 128.0, clear=True)
    with pytest.raises(StateError):
        desk.recheck("EX-2025-001", dt.date(2025, 4, 12), 128.0, clear=True)


def test_a_recheck_before_the_reading_that_opened_it_is_refused(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    with pytest.raises(RuleError, match="was opened"):
        desk.recheck("EX-2025-001", dt.date(2025, 4, 1), 128.0, clear=True)


def test_the_board_puts_the_least_time_left_first(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    desk.post_run(walk(desk, dt.date(2025, 5, 6), **{"VW-002": {"static": 0.4}}))
    board = desk.board("NORTHRIDGE", dt.date(2025, 5, 8))
    assert [s.exceedance.label for s in board] == ["EX-2025-001", "EX-2025-002"]
    assert board[0].late
    assert not board[1].late


def test_catching_up_moves_records_the_calendar_passed(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    assert desk.exceedances.get("EX-2025-001").stage is Stage.CORRECT
    assert desk.catch_up("NORTHRIDGE", dt.date(2025, 9, 1)) == ["EX-2025-001"]
    assert desk.exceedances.get("EX-2025-001").stage is Stage.EXPANSION
    assert desk.catch_up("NORTHRIDGE", dt.date(2025, 9, 2)) == []


def test_only_late_records_are_on_the_overdue_list(desk: ComplianceDesk) -> None:
    desk.post_run(walk(desk, APRIL, **{"VW-001": {"temperature": 138.0}}))
    assert desk.overdue("NORTHRIDGE", dt.date(2025, 4, 13)) == []
    assert len(desk.overdue("NORTHRIDGE", dt.date(2025, 4, 14))) == 1

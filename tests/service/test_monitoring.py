"""Opening a run, reading the field, and closing it."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Month
from gemwalk.errors import RuleError, StateError
from gemwalk.rules import Finding
from gemwalk.service.monitoring import MonitoringDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.store.book import Book

APRIL = dt.date(2025, 4, 8)


@pytest.fixture
def desk(book: Book) -> MonitoringDesk:
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
    return MonitoringDesk(book)


def a_run(desk: MonitoringDesk, on: dt.date = APRIL) -> str:
    return desk.open_run("NORTHRIDGE", on, monitor="D. Kasprzak", meter="GEM5000-40912").label


def a_reading(desk: MonitoringDesk, run: str, device: str, **changes: float) -> None:
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
    desk.record(run, device, on=APRIL, **fields)  # type: ignore[arg-type]


def test_a_run_takes_the_label_of_its_month(desk: MonitoringDesk) -> None:
    assert a_run(desk) == "MR-2025-04-01"


def test_two_runs_cannot_be_open_at_one_site(desk: MonitoringDesk) -> None:
    a_run(desk)
    with pytest.raises(RuleError, match="still open"):
        a_run(desk)


def test_a_closed_run_takes_no_more_readings(desk: MonitoringDesk) -> None:
    run = a_run(desk)
    a_reading(desk, run, "VW-001")
    a_reading(desk, run, "VW-002")
    desk.close_run(run, dt.date(2025, 4, 10))
    with pytest.raises(StateError):
        a_reading(desk, run, "VW-001")


def test_a_device_off_the_run_cannot_be_read(desk: MonitoringDesk) -> None:
    wells = desk.wellfield
    wells.take_offline("VW-002", dt.date(2025, 3, 1))
    run = a_run(desk)
    with pytest.raises(StateError):
        a_reading(desk, run, "VW-002")


def test_a_reading_cannot_predate_the_run_it_is_on(desk: MonitoringDesk) -> None:
    run = a_run(desk)
    with pytest.raises(RuleError, match="did not start"):
        desk.record(
            run,
            "VW-001",
            on=dt.date(2025, 4, 1),
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


def test_a_run_with_a_wellhead_unread_cannot_be_closed(desk: MonitoringDesk) -> None:
    run = a_run(desk)
    a_reading(desk, run, "VW-001")
    assert [d.label for d in desk.missing(run)] == ["VW-002"]
    with pytest.raises(RuleError, match="VW-002"):
        desk.close_run(run, dt.date(2025, 4, 10))


def test_a_reason_lets_a_short_run_close(desk: MonitoringDesk) -> None:
    run = a_run(desk)
    a_reading(desk, run, "VW-001")
    closed = desk.close_run(run, dt.date(2025, 4, 10), note="VW-002 under water")
    assert not closed.is_open
    assert closed.note == "VW-002 under water"


def test_a_full_run_closes_with_no_reason(desk: MonitoringDesk) -> None:
    run = a_run(desk)
    a_reading(desk, run, "VW-001")
    a_reading(desk, run, "VW-002")
    assert desk.missing(run) == []
    assert not desk.close_run(run, dt.date(2025, 4, 10)).is_open


def test_a_device_wired_up_mid_pass_joins_the_roster(desk: MonitoringDesk) -> None:
    run = a_run(desk)
    a_reading(desk, run, "VW-001")
    a_reading(desk, run, "VW-002")
    late = desk.wellfield.drill(
        "NORTHRIDGE",
        "A-03",
        station="N 14+00",
        total_depth=80.0,
        screen_top=20.0,
        screen_bottom=74.0,
        on=dt.date(2025, 4, 2),
    )
    desk.wellfield.connect(late.label, dt.date(2025, 4, 3))
    assert [d.label for d in desk.missing(run)] == [late.label]


def test_every_reading_on_a_run_is_read_against_the_standard(desk: MonitoringDesk) -> None:
    run = a_run(desk)
    a_reading(desk, run, "VW-001")
    a_reading(desk, run, "VW-002", temperature=139.0)
    results = desk.assessments(run)
    assert [a.device for a in results] == ["VW-001", "VW-002"]
    assert [a.device for a in desk.exceedances(run)] == ["VW-002"]
    assert desk.assessment(run, "VW-002").kinds == (Finding.TEMPERATURE,)


def test_a_wellhead_that_was_not_read_has_no_assessment(desk: MonitoringDesk) -> None:
    run = a_run(desk)
    with pytest.raises(RuleError, match="was not read"):
        desk.assessment(run, "VW-001")


def test_the_election_reaches_the_assessment(desk: MonitoringDesk) -> None:
    desk.sites.elect("NORTHRIDGE", dt.date(2025, 3, 1), nitrogen_alternative=True)
    run = a_run(desk)
    a_reading(desk, run, "VW-001", oxygen=1.0, balance=26.0, methane=45.0, carbon=28.0)
    assert desk.assessment(run, "VW-001").kinds == (Finding.NITROGEN,)


def test_a_month_with_no_run_is_a_month_missed(desk: MonitoringDesk) -> None:
    run = a_run(desk)
    a_reading(desk, run, "VW-001")
    a_reading(desk, run, "VW-002")
    desk.close_run(run, dt.date(2025, 4, 10))
    missed = desk.months_missed("NORTHRIDGE", Month(2025, 3), Month(2025, 6))
    assert [str(m) for m in missed] == ["2025-03", "2025-05", "2025-06"]
    assert len(desk.runs_in("NORTHRIDGE", Month(2025, 4))) == 1

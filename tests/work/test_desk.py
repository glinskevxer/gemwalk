"""Work orders raised off records, handed out and closed."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import RuleError
from gemwalk.model.work import Job, Standing
from gemwalk.service.compliance import ComplianceDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.service.surface import SurfaceDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.service.work import WorkDesk
from gemwalk.store.book import Book

APRIL = dt.date(2025, 4, 8)
MAY = dt.date(2025, 5, 13)


@pytest.fixture
def desk(book: Book) -> WorkDesk:
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
    return WorkDesk(book)


def an_exceedance(desk: WorkDesk) -> str:
    compliance: ComplianceDesk = desk.compliance
    run = compliance.monitoring.open_run(
        "NORTHRIDGE", APRIL, monitor="D. Kasprzak", meter="GEM-40912"
    ).label
    compliance.monitoring.record(
        run,
        "VW-001",
        on=APRIL,
        methane=52.4,
        carbon=38.1,
        oxygen=0.6,
        balance=8.9,
        temperature=138.0,
        static=-1.4,
        applied=-12.0,
        flow=42.0,
        valve_before=3.0,
        valve_after=3.0,
    )
    compliance.monitoring.close_run(run, APRIL)
    return compliance.post_run(run).opened[0]


def a_hit(desk: WorkDesk) -> str:
    surface: SurfaceDesk = desk.surface
    walk = surface.open_walk(
        "NORTHRIDGE",
        MAY,
        monitor="T. Wierzbicki",
        instrument="TVA1000B-8841",
        background=2.0,
        wind_mean=3.4,
        wind_gust=7.1,
    ).label
    return surface.mark(walk, "A-03", "grid 14-J", 720.0, on=MAY).label


def test_an_order_takes_the_label_of_its_year(desk: WorkDesk) -> None:
    order = desk.raise_order("NORTHRIDGE", Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13))
    assert order.label == "WO-2025-0001"


def test_an_order_off_a_record_takes_that_record_s_deadline(desk: WorkDesk) -> None:
    record = an_exceedance(desk)
    order = desk.raise_for_exceedance(record, Job.VALVE, dt.date(2025, 4, 11))
    assert order.due_on == dt.date(2025, 4, 13)
    assert order.days_allowed == 2
    assert order.because == record


def test_writing_the_order_later_does_not_move_the_deadline(desk: WorkDesk) -> None:
    record = an_exceedance(desk)
    early = desk.raise_for_exceedance(record, Job.VALVE, APRIL)
    late = desk.raise_for_exceedance(record, Job.WELLHEAD, dt.date(2025, 4, 12))
    assert early.due_on == late.due_on


def test_an_order_off_a_closed_record_is_refused(desk: WorkDesk) -> None:
    record = an_exceedance(desk)
    desk.compliance.recheck(record, dt.date(2025, 4, 10), 128.0, clear=True)
    with pytest.raises(RuleError, match="closed"):
        desk.raise_for_exceedance(record, Job.VALVE, dt.date(2025, 4, 11))


def test_an_order_off_a_surface_spot_takes_that_spot_s_deadline(desk: WorkDesk) -> None:
    hit = a_hit(desk)
    order = desk.raise_for_hit(hit, Job.COVER, MAY)
    assert order.due_on == dt.date(2025, 5, 23)
    assert order.target == "grid 14-J"


def test_an_order_off_a_closed_spot_is_refused(desk: WorkDesk) -> None:
    hit = a_hit(desk)
    desk.surface.repair(hit, dt.date(2025, 5, 16))
    desk.surface.remonitor(hit, dt.date(2025, 5, 20), 180.0)
    with pytest.raises(RuleError, match="closed"):
        desk.raise_for_hit(hit, Job.COVER, dt.date(2025, 5, 21))


def test_closing_the_order_does_not_close_the_record(desk: WorkDesk) -> None:
    record = an_exceedance(desk)
    order = desk.raise_for_exceedance(record, Job.VALVE, APRIL).label
    desk.finish(order, dt.date(2025, 4, 10), "opened a half turn")
    assert desk.compliance.exceedances.get(record).is_open


def test_the_board_puts_the_least_time_left_first(desk: WorkDesk) -> None:
    first = desk.raise_order(
        "NORTHRIDGE", Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13)
    ).label
    second = desk.raise_order(
        "NORTHRIDGE", Job.PIPE, "LT-004", on=APRIL, due=dt.date(2025, 5, 1)
    ).label
    board = desk.board("NORTHRIDGE", dt.date(2025, 4, 12))
    assert [t.order.label for t in board] == [first, second]
    assert board[0].days_left == 1


def test_only_late_orders_are_overdue(desk: WorkDesk) -> None:
    desk.raise_order("NORTHRIDGE", Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13))
    assert desk.overdue("NORTHRIDGE", dt.date(2025, 4, 13)) == []
    assert len(desk.overdue("NORTHRIDGE", dt.date(2025, 4, 14))) == 1


def test_a_finished_order_leaves_the_board(desk: WorkDesk) -> None:
    order = desk.raise_order(
        "NORTHRIDGE", Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13)
    ).label
    desk.finish(order, dt.date(2025, 4, 10))
    assert desk.board("NORTHRIDGE", dt.date(2025, 4, 12)) == []


def test_a_record_with_nobody_sent_to_it_is_listed(desk: WorkDesk) -> None:
    record = an_exceedance(desk)
    assert desk.unhandled("NORTHRIDGE", dt.date(2025, 4, 11)) == [record]
    desk.raise_for_exceedance(record, Job.VALVE, dt.date(2025, 4, 11))
    assert desk.unhandled("NORTHRIDGE", dt.date(2025, 4, 11)) == []


def test_a_surface_spot_with_nobody_sent_to_it_is_listed_too(desk: WorkDesk) -> None:
    hit = a_hit(desk)
    assert desk.unhandled("NORTHRIDGE", MAY) == [hit]


def test_crews_come_back_busiest_first(desk: WorkDesk) -> None:
    for target in ("VW-001", "LT-004", "HD-01"):
        order = desk.raise_order(
            "NORTHRIDGE", Job.OTHER, target, on=APRIL, due=dt.date(2025, 4, 20)
        ).label
        crew = "north crew" if target != "HD-01" else "pipe crew"
        desk.assign(order, crew, APRIL)
    load = desk.crew_load("NORTHRIDGE", APRIL)
    assert list(load) == ["north crew", "pipe crew"]
    assert load["north crew"] == 2


def test_an_assigned_order_stays_on_the_board(desk: WorkDesk) -> None:
    order = desk.raise_order(
        "NORTHRIDGE", Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13)
    ).label
    desk.assign(order, "north crew", APRIL)
    assert desk.orders.get(order).state is Standing.ASSIGNED
    assert len(desk.board("NORTHRIDGE", dt.date(2025, 4, 12))) == 1


def test_a_cancelled_order_leaves_the_board(desk: WorkDesk) -> None:
    order = desk.raise_order(
        "NORTHRIDGE", Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13)
    ).label
    desk.cancel(order, dt.date(2025, 4, 9), "well abandoned instead")
    assert desk.board("NORTHRIDGE", dt.date(2025, 4, 12)) == []


def test_the_history_of_a_place_comes_back_oldest_first(desk: WorkDesk) -> None:
    late = desk.raise_order(
        "NORTHRIDGE", Job.VALVE, "VW-001", on=dt.date(2025, 6, 2), due=dt.date(2025, 6, 9)
    ).label
    early = desk.raise_order(
        "NORTHRIDGE", Job.WELLHEAD, "VW-001", on=APRIL, due=dt.date(2025, 4, 13)
    ).label
    assert [o.label for o in desk.history("VW-001")] == [early, late]


def test_orders_finished_after_their_date_are_listed(desk: WorkDesk) -> None:
    order = desk.raise_order(
        "NORTHRIDGE", Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13)
    ).label
    desk.finish(order, dt.date(2025, 4, 20))
    late = desk.finished_late("NORTHRIDGE", dt.date(2025, 4, 1), dt.date(2025, 4, 30))
    assert [o.label for o in late] == [order]


def test_a_date_before_the_day_the_order_was_written_is_refused(desk: WorkDesk) -> None:
    from gemwalk.errors import OrderError

    with pytest.raises(OrderError):
        desk.raise_order("NORTHRIDGE", Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 1))


def test_an_order_off_a_record_may_already_be_past_its_date(desk: WorkDesk) -> None:
    record = an_exceedance(desk)
    desk.compliance.catch_up("NORTHRIDGE", dt.date(2025, 9, 1))
    order = desk.raise_for_exceedance(record, Job.VALVE, dt.date(2025, 9, 2))
    assert order.born_late
    assert order.due_on == dt.date(2025, 8, 6)


def test_orders_come_back_by_the_state_they_are_in(desk: WorkDesk) -> None:
    from gemwalk.model.work import Standing

    order = desk.raise_order(
        "NORTHRIDGE", Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13)
    ).label
    assert [o.label for o in desk.orders.in_state("NORTHRIDGE", Standing.OPEN)] == [order]
    desk.assign(order, "north crew", APRIL)
    assert desk.orders.in_state("NORTHRIDGE", Standing.OPEN) == []
    assert len(desk.orders.in_state("NORTHRIDGE", Standing.ASSIGNED)) == 1


def test_the_orders_raised_off_one_record_come_back_together(desk: WorkDesk) -> None:
    record = an_exceedance(desk)
    desk.raise_for_exceedance(record, Job.VALVE, dt.date(2025, 4, 9))
    desk.raise_for_exceedance(record, Job.WELLHEAD, dt.date(2025, 4, 10))
    assert len(desk.orders.of_record(record)) == 2
    assert desk.orders.of_record("EX-1999-001") == []

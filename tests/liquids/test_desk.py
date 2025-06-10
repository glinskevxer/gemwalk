"""Dewatering through the desk, and what the water explains."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.assess import Concern
from gemwalk.clock import read_moment
from gemwalk.errors import RuleError, StateError
from gemwalk.model.liquids import SumpKind
from gemwalk.service.liquids import LiquidsDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book

ZONE = "America/Chicago"
JUNE = dt.date(2025, 6, 3)


@pytest.fixture
def desk(book: Book) -> LiquidsDesk:
    sites = SiteDesk(book)
    sites.open_site(
        "NORTHRIDGE",
        "Northridge",
        subpart="XXX",
        permit="MSW-1188-04",
        zone=ZONE,
        design_capacity=8_400_000.0,
        opened_on=dt.date(1998, 6, 1),
    )
    sites.add_area("A-03", "NORTHRIDGE", "phase 3", acres=12.4, first_waste=dt.date(2019, 4, 15))
    made = LiquidsDesk(book)
    for _ in range(3):
        made.wellfield.drill(
            "NORTHRIDGE",
            "A-03",
            station="N 12+40",
            total_depth=92.0,
            screen_top=22.0,
            screen_bottom=86.0,
            on=dt.date(2021, 5, 12),
        )
    return made


def test_a_tape_below_the_bottom_of_the_hole_is_refused(desk: LiquidsDesk) -> None:
    with pytest.raises(RuleError, match="bottom of a"):
        desk.tape("VW-001", JUNE, 140.0)


def test_a_tape_before_the_well_was_drilled_is_refused(desk: LiquidsDesk) -> None:
    with pytest.raises(RuleError, match="not drilled"):
        desk.tape("VW-001", dt.date(2019, 1, 1), 70.0)


def test_an_abandoned_well_takes_no_tape(desk: LiquidsDesk) -> None:
    desk.wellfield.abandon("VW-001", dt.date(2025, 5, 1))
    with pytest.raises(StateError):
        desk.tape("VW-001", JUNE, 70.0)


def test_a_well_never_tapped_has_nothing_standing_in_it(desk: LiquidsDesk) -> None:
    assert desk.water_in("VW-001", JUNE) is None
    assert desk.standing("NORTHRIDGE", JUNE) == []


def test_the_wettest_well_comes_first(desk: LiquidsDesk) -> None:
    desk.tape("VW-001", JUNE, 80.0)
    desk.tape("VW-002", JUNE, 20.0)
    desk.tape("VW-003", JUNE, 50.0)
    assert [w.device.label for w in desk.standing("NORTHRIDGE", JUNE)] == [
        "VW-002",
        "VW-003",
        "VW-001",
    ]


def test_a_flooded_well_is_listed_and_a_damp_one_is_not(desk: LiquidsDesk) -> None:
    desk.tape("VW-001", JUNE, 20.0)
    desk.tape("VW-002", JUNE, 80.0)
    assert [w.device.label for w in desk.flooded("NORTHRIDGE", JUNE)] == ["VW-001"]


def test_a_well_half_under_water_is_on_the_dewater_list(desk: LiquidsDesk) -> None:
    desk.tape("VW-001", JUNE, 54.0)
    desk.tape("VW-002", JUNE, 80.0)
    wanted = desk.dewater_list("NORTHRIDGE", JUNE)
    assert [w.device.label for w in wanted] == ["VW-001"]
    assert wanted[0].share == pytest.approx(0.5)


def test_an_abandoned_well_leaves_the_standing_list(desk: LiquidsDesk) -> None:
    desk.tape("VW-001", JUNE, 20.0)
    desk.wellfield.abandon("VW-001", dt.date(2025, 6, 4))
    assert desk.standing("NORTHRIDGE", dt.date(2025, 6, 5)) == []


def test_a_clean_reading_needs_no_explanation(desk: LiquidsDesk) -> None:
    assert desk.explains("VW-001", JUNE, ()) is None


def test_a_dead_wellhead_with_no_tape_is_unexplained(desk: LiquidsDesk) -> None:
    answer = desk.explains("VW-001", JUNE, (Concern.NO_FLOW,))
    assert answer is not None
    assert "no tape drop" in answer


def test_a_dead_wellhead_under_water_is_explained(desk: LiquidsDesk) -> None:
    desk.tape("VW-001", JUNE, 20.0)
    answer = desk.explains("VW-001", JUNE, (Concern.NO_FLOW, Concern.DEAD))
    assert answer is not None
    assert "under water" in answer


def test_a_part_flooded_wellhead_says_how_much(desk: LiquidsDesk) -> None:
    desk.tape("VW-001", JUNE, 54.0)
    answer = desk.explains("VW-001", JUNE, (Concern.RICH_AIR,))
    assert answer is not None
    assert "50%" in answer


def test_a_dry_wellhead_reading_air_points_at_the_fittings(desk: LiquidsDesk) -> None:
    desk.tape("VW-001", JUNE, 90.0)
    answer = desk.explains("VW-001", JUNE, (Concern.RICH_AIR,))
    assert answer is not None
    assert "seal" in answer


def test_a_load_comes_off_a_live_sump_only(desk: LiquidsDesk) -> None:
    sump = desk.add_sump(
        "NORTHRIDGE", "HD-01 low point", kind=SumpKind.KNOCKOUT, capacity=550.0, on=JUNE
    )
    assert sump.label == "CS-001"
    desk.retire_sump(sump.label, dt.date(2025, 7, 1))
    with pytest.raises(StateError):
        desk.pump(
            sump.label,
            read_moment("2025-07-02 10:20", ZONE),
            410.0,
            hauler="Vestermark Vacuum",
            bound_for="leachate pretreatment",
        )


def test_gallons_add_up_across_every_sump_at_a_site(desk: LiquidsDesk) -> None:
    first = desk.add_sump("NORTHRIDGE", "HD-01 low point", capacity=550.0, on=JUNE).label
    second = desk.add_sump("NORTHRIDGE", "HD-02 low point", capacity=300.0, on=JUNE).label
    desk.pump(
        first,
        read_moment("2025-06-10 10:20", ZONE),
        410.0,
        hauler="Vestermark Vacuum",
        bound_for="leachate pretreatment",
    )
    desk.pump(
        second,
        read_moment("2025-06-19 09:00", ZONE),
        260.0,
        hauler="Kroon Environmental",
        bound_for="leachate pretreatment",
    )
    total = desk.hauled(
        "NORTHRIDGE", read_moment("2025-06-01 00:00", ZONE), read_moment("2025-07-01 00:00", ZONE)
    )
    assert total == pytest.approx(670.0)


def test_haulers_come_back_biggest_first(desk: LiquidsDesk) -> None:
    sump = desk.add_sump("NORTHRIDGE", "HD-01 low point", capacity=550.0, on=JUNE).label
    for at, gallons, hauler in (
        ("2025-06-10 10:20", 410.0, "Vestermark Vacuum"),
        ("2025-06-19 09:00", 260.0, "Kroon Environmental"),
        ("2025-06-24 09:00", 300.0, "Kroon Environmental"),
    ):
        desk.pump(
            sump,
            read_moment(at, ZONE),
            gallons,
            hauler=hauler,
            bound_for="leachate pretreatment",
        )
    tally = desk.by_hauler(
        read_moment("2025-06-01 00:00", ZONE), read_moment("2025-07-01 00:00", ZONE)
    )
    assert list(tally) == ["Kroon Environmental", "Vestermark Vacuum"]
    assert tally["Kroon Environmental"] == pytest.approx(560.0)

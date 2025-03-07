"""Drilling, connecting and retiring devices through the desk."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import RuleError
from gemwalk.model.device import Kind, State
from gemwalk.service.sites import SiteDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.store.book import Book
from gemwalk.units import Temperature

DRILLED = dt.date(2021, 5, 12)


@pytest.fixture
def desk(book: Book) -> WellfieldDesk:
    sites = SiteDesk(book)
    sites.open_site(
        "NORTHRIDGE",
        "Northridge Sanitary Landfill",
        subpart="XXX",
        permit="MSW-1188-04",
        zone="America/Chicago",
        design_capacity=8_400_000.0,
        opened_on=dt.date(1998, 6, 1),
    )
    sites.add_area("A-03", "NORTHRIDGE", "phase 3", acres=12.4, first_waste=dt.date(2019, 4, 15))
    sites.open_site(
        "SOUTHFORK",
        "Southfork Landfill",
        subpart="WWW",
        permit="MSW-2011-09",
        zone="America/Chicago",
        design_capacity=3_100_000.0,
        opened_on=dt.date(1994, 2, 1),
    )
    sites.add_area("B-01", "SOUTHFORK", "cell one", acres=6.0, first_waste=dt.date(1994, 3, 1))
    return WellfieldDesk(book)


def drill(desk: WellfieldDesk, on: dt.date = DRILLED, area: str = "A-03") -> str:
    return desk.drill(
        "NORTHRIDGE",
        area,
        station="N 12+40 E 3+15",
        total_depth=92.0,
        screen_top=22.0,
        screen_bottom=86.0,
        on=on,
    ).label


def test_the_first_device_takes_the_first_label(desk: WellfieldDesk) -> None:
    assert drill(desk) == "VW-001"
    assert drill(desk) == "VW-002"


def test_a_device_cannot_go_into_an_area_of_another_site(desk: WellfieldDesk) -> None:
    with pytest.raises(RuleError, match="not an area"):
        desk.drill(
            "NORTHRIDGE",
            "B-01",
            station="x",
            total_depth=50.0,
            screen_top=10.0,
            screen_bottom=45.0,
            on=DRILLED,
        )


def test_a_device_cannot_be_drilled_before_its_area_took_waste(desk: WellfieldDesk) -> None:
    with pytest.raises(RuleError, match="no waste"):
        drill(desk, dt.date(2018, 1, 1))


def test_a_device_can_be_given_a_label_off_the_old_paper_records(desk: WellfieldDesk) -> None:
    made = desk.drill(
        "NORTHRIDGE",
        "A-03",
        kind=Kind.HORIZONTAL,
        station="N 9+00",
        total_depth=40.0,
        screen_top=8.0,
        screen_bottom=38.0,
        on=DRILLED,
        label="HC-007",
    )
    assert made.label == "HC-007"
    assert made.kind is Kind.HORIZONTAL


def test_only_connected_devices_are_on_the_roster(desk: WellfieldDesk) -> None:
    first = drill(desk)
    drill(desk)
    desk.connect(first, dt.date(2021, 6, 2))
    assert [d.label for d in desk.roster("NORTHRIDGE")] == [first]


def test_a_device_off_the_run_leaves_the_roster_and_comes_back(desk: WellfieldDesk) -> None:
    label = drill(desk)
    desk.connect(label, dt.date(2021, 6, 2))
    desk.take_offline(label, dt.date(2025, 3, 1))
    assert desk.roster("NORTHRIDGE") == []
    assert [d.label for d in desk.offline("NORTHRIDGE")] == [label]
    desk.put_online(label, dt.date(2025, 4, 2))
    assert [d.label for d in desk.roster("NORTHRIDGE")] == [label]


def test_a_raise_that_runs_past_the_window_is_listed(desk: WellfieldDesk) -> None:
    label = drill(desk)
    desk.connect(label, dt.date(2021, 6, 2))
    desk.take_offline(label, dt.date(2025, 3, 1))
    assert desk.overdue_offline("NORTHRIDGE", dt.date(2025, 4, 30)) == []
    assert [d.label for d in desk.overdue_offline("NORTHRIDGE", dt.date(2025, 5, 1))] == [label]


def test_devices_waiting_to_be_wired_come_back_oldest_first(desk: WellfieldDesk) -> None:
    late = drill(desk, dt.date(2023, 9, 1))
    early = drill(desk, dt.date(2021, 5, 12))
    waiting = desk.unconnected("NORTHRIDGE", dt.date(2025, 1, 1))
    assert [d.label for d in waiting] == [early, late]


def test_a_device_drilled_after_the_day_asked_about_is_not_waiting(desk: WellfieldDesk) -> None:
    drill(desk, dt.date(2023, 9, 1))
    assert desk.unconnected("NORTHRIDGE", dt.date(2022, 1, 1)) == []


def test_an_abandoned_device_is_off_every_list(desk: WellfieldDesk) -> None:
    label = drill(desk)
    desk.connect(label, dt.date(2021, 6, 2))
    desk.abandon(label, dt.date(2026, 1, 8))
    assert desk.roster("NORTHRIDGE") == []
    assert desk.count_by_state("NORTHRIDGE")[str(State.ABANDONED)] == 1


def test_the_state_tally_names_every_state_even_at_zero(desk: WellfieldDesk) -> None:
    drill(desk)
    tally = desk.count_by_state("NORTHRIDGE")
    assert tally == {"drilled": 1, "connected": 0, "offline": 0, "abandoned": 0}


def test_a_higher_operating_value_has_to_be_higher(desk: WellfieldDesk) -> None:
    label = drill(desk)
    with pytest.raises(RuleError, match="not higher"):
        desk.approve_higher_temperature(label, Temperature(125.0), dt.date(2025, 3, 1))


def test_an_approved_value_is_written_against_the_one_device(desk: WellfieldDesk) -> None:
    label = drill(desk)
    other = drill(desk)
    desk.approve_higher_temperature(label, Temperature(145.0), dt.date(2025, 3, 1))
    subpart = desk.sites.standard_of("NORTHRIDGE")
    day = dt.date(2025, 4, 8)
    assert desk.devices.get(label).temperature_limit(subpart, day).fahrenheit == 145.0
    assert desk.devices.get(other).temperature_limit(subpart, day).fahrenheit == 131.0

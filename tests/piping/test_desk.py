"""Laying pipe and taking it back out, leaves first."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import RuleError, StateError
from gemwalk.service.piping import PipingDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.store.book import Book

LAID = dt.date(2019, 9, 3)
DRILLED = dt.date(2021, 5, 12)


@pytest.fixture
def desks(book: Book) -> tuple[PipingDesk, WellfieldDesk]:
    sites = SiteDesk(book)
    for label, subpart in (("NORTHRIDGE", "XXX"), ("SOUTHFORK", "WWW")):
        sites.open_site(
            label,
            label.title(),
            subpart=subpart,
            permit=f"MSW-{label}",
            zone="America/Chicago",
            design_capacity=8_400_000.0,
            opened_on=dt.date(1998, 6, 1),
        )
    sites.add_area("A-03", "NORTHRIDGE", "phase 3", acres=12.4, first_waste=dt.date(2019, 4, 15))
    return PipingDesk(book), WellfieldDesk(book)


def a_header(desk: PipingDesk, site: str = "NORTHRIDGE", diameter: float = 18.0) -> str:
    return desk.lay_header(
        site,
        "north trunk",
        diameter=diameter,
        material="HDPE SDR17",
        length_feet=2_140.0,
        on=LAID,
    ).label


def a_lateral(desk: PipingDesk, header: str, diameter: float = 8.0) -> str:
    return desk.lay_lateral(
        "NORTHRIDGE",
        header,
        diameter=diameter,
        material="HDPE SDR17",
        length_feet=460.0,
        on=LAID,
    ).label


def a_device(wells: WellfieldDesk) -> str:
    return wells.drill(
        "NORTHRIDGE",
        "A-03",
        station="N 12+40",
        total_depth=92.0,
        screen_top=22.0,
        screen_bottom=86.0,
        on=DRILLED,
    ).label


def test_pipe_takes_its_label_from_the_counter(desks: tuple[PipingDesk, WellfieldDesk]) -> None:
    desk, _ = desks
    header = a_header(desk)
    assert header == "HD-01"
    assert a_lateral(desk, header) == "LT-001"


def test_a_lateral_bigger_than_its_header_is_refused(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, _ = desks
    header = a_header(desk, diameter=12.0)
    with pytest.raises(RuleError, match="does not tie into"):
        a_lateral(desk, header, diameter=18.0)


def test_a_lateral_off_another_site_s_header_is_refused(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, _ = desks
    header = a_header(desk, site="SOUTHFORK")
    with pytest.raises(RuleError, match="not a header"):
        a_lateral(desk, header)


def test_a_device_tied_in_appears_on_its_lateral(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, wells = desks
    header = a_header(desk)
    lateral = a_lateral(desk, header)
    device = a_device(wells)
    desk.tie_in(device, lateral)
    assert [d.label for d in desk.branch(lateral).devices] == [device]
    assert desk.unpiped("NORTHRIDGE") == []


def test_an_untied_device_is_pulling_on_nothing(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, wells = desks
    device = a_device(wells)
    assert [d.label for d in desk.unpiped("NORTHRIDGE")] == [device]


def test_an_abandoned_device_cannot_be_tied_in(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, wells = desks
    lateral = a_lateral(desk, a_header(desk))
    device = a_device(wells)
    wells.abandon(device, dt.date(2026, 1, 8))
    with pytest.raises(StateError):
        desk.tie_in(device, lateral)


def test_a_retired_lateral_takes_nothing_new(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, wells = desks
    lateral = a_lateral(desk, a_header(desk))
    desk.retire_lateral(lateral, dt.date(2024, 6, 1))
    with pytest.raises(StateError):
        desk.tie_in(a_device(wells), lateral)


def test_a_lateral_with_a_device_on_the_run_cannot_be_pulled(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, wells = desks
    lateral = a_lateral(desk, a_header(desk))
    device = a_device(wells)
    desk.tie_in(device, lateral)
    wells.connect(device, dt.date(2021, 6, 2))
    with pytest.raises(RuleError, match=device):
        desk.retire_lateral(lateral, dt.date(2024, 6, 1))


def test_a_lateral_whose_devices_are_off_the_run_can_be_pulled(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, wells = desks
    lateral = a_lateral(desk, a_header(desk))
    device = a_device(wells)
    desk.tie_in(device, lateral)
    wells.connect(device, dt.date(2021, 6, 2))
    wells.abandon(device, dt.date(2024, 5, 1))
    assert not desk.retire_lateral(lateral, dt.date(2024, 6, 1)).is_live


def test_a_header_with_a_live_lateral_cannot_be_pulled(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, _ = desks
    header = a_header(desk)
    lateral = a_lateral(desk, header)
    with pytest.raises(RuleError, match=lateral):
        desk.retire_header(header, dt.date(2024, 6, 1))


def test_the_tree_carries_every_device_under_a_header(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, wells = desks
    header = a_header(desk)
    first = a_lateral(desk, header)
    second = a_lateral(desk, header)
    one = a_device(wells)
    two = a_device(wells)
    desk.tie_in(one, first)
    desk.tie_in(two, second)
    wells.connect(one, dt.date(2021, 6, 2))

    tree = desk.tree("NORTHRIDGE")
    assert len(tree) == 1
    assert tree[0].device_count == 2
    assert [d.label for d in desk.devices_on_header(header)] == sorted([one, two])
    assert [b.lateral.label for b in tree[0].branches] == [first, second]
    assert [d.label for d in desk.branch(first).live_devices] == [one]
    assert desk.branch(second).live_devices == ()


def test_a_lateral_bigger_than_its_header_is_refused_by_the_desk(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, _ = desks
    header = a_header(desk, diameter=8.0)
    with pytest.raises(RuleError, match="does not tie into"):
        desk.lay_lateral(
            "NORTHRIDGE",
            header,
            diameter=18.0,
            material="HDPE SDR17",
            length_feet=100.0,
            on=LAID,
        )


def test_a_device_of_another_site_cannot_be_tied_in(
    desks: tuple[PipingDesk, WellfieldDesk],
) -> None:
    desk, wells = desks
    lateral = a_lateral(desk, a_header(desk))
    device = a_device(wells)
    desk.devices.book.execute("PRAGMA foreign_keys = OFF")
    desk.devices.book.execute("UPDATE device SET site = 'SOUTHFORK' WHERE label = ?", (device,))
    desk.devices.book.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(RuleError, match="is not pipe at"):
        desk.tie_in(device, lateral)

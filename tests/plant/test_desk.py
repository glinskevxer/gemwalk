"""Block averages, outages and availability through the plant desk."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import RuleError, StateError
from gemwalk.model.plant import ControlKind
from gemwalk.service.plant import PlantDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book

ZONE = "America/Chicago"


@pytest.fixture
def desk(book: Book) -> PlantDesk:
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
    made = PlantDesk(book)
    made.install(
        "CD-01",
        "NORTHRIDGE",
        "west flare",
        kind=ControlKind.ENCLOSED_FLARE,
        capacity=2_400.0,
        on=dt.date(2016, 4, 1),
        minimum_temp=1_400.0,
    )
    return made


def at(text: str) -> dt.datetime:
    return read_moment(text, "UTC")


def log(
    desk: PlantDesk, moment: str, temperature: float | None = 1_512.0, **changes: object
) -> None:
    fields: dict[str, object] = {"running": True, "flow": 1_180.0, "methane": 49.2}
    fields.update(changes)
    desk.log("CD-01", at(moment), temperature=temperature, **fields)  # type: ignore[arg-type]


def test_a_candlestick_takes_no_chamber_temperature(desk: PlantDesk) -> None:
    desk.install(
        "CD-02",
        "NORTHRIDGE",
        "east stick",
        kind=ControlKind.CANDLESTICK,
        capacity=900.0,
        on=dt.date(2019, 5, 1),
    )
    with pytest.raises(RuleError, match="no chamber"):
        desk.log(
            "CD-02",
            at("2025-06-11 09:00"),
            running=True,
            flow=200.0,
            methane=48.0,
            temperature=1_400.0,
        )


def test_a_running_flare_has_to_be_measured(desk: PlantDesk) -> None:
    with pytest.raises(RuleError, match="measured"):
        desk.log("CD-01", at("2025-06-11 09:00"), running=True, flow=1_180.0, methane=49.2)


def test_a_flare_that_is_down_needs_no_temperature(desk: PlantDesk) -> None:
    record = desk.log("CD-01", at("2025-06-11 09:00"), running=False, flow=0.0, methane=0.0)
    assert not record.running


def test_a_block_is_the_average_of_what_was_recorded_in_it(desk: PlantDesk) -> None:
    for moment, temp in (
        ("2025-06-11 09:00", 1_500.0),
        ("2025-06-11 10:00", 1_460.0),
        ("2025-06-11 11:00", 1_420.0),
    ):
        log(desk, moment, temp)
    blocks = desk.blocks("CD-01", at("2025-06-11 09:00"), at("2025-06-11 12:00"))
    assert len(blocks) == 1
    assert blocks[0].average == pytest.approx(1_460.0)
    assert not blocks[0].below


def test_a_block_can_be_a_deviation_with_every_reading_looking_ordinary(
    desk: PlantDesk,
) -> None:
    for moment, temp in (
        ("2025-06-11 09:00", 1_398.0),
        ("2025-06-11 10:00", 1_396.0),
        ("2025-06-11 11:00", 1_399.0),
    ):
        log(desk, moment, temp)
    deviations = desk.deviations("CD-01", at("2025-06-11 09:00"), at("2025-06-11 12:00"))
    assert len(deviations) == 1
    assert deviations[0].average == pytest.approx(1_397.666, rel=1e-4)


def test_a_dip_that_recovers_inside_a_block_is_not_a_deviation(desk: PlantDesk) -> None:
    for moment, temp in (
        ("2025-06-11 09:00", 1_520.0),
        ("2025-06-11 10:00", 1_180.0),
        ("2025-06-11 11:00", 1_530.0),
    ):
        log(desk, moment, temp)
    assert desk.deviations("CD-01", at("2025-06-11 09:00"), at("2025-06-11 12:00")) == []


def test_the_blocks_are_pinned_to_the_clock_and_not_to_the_first_reading(
    desk: PlantDesk,
) -> None:
    log(desk, "2025-06-11 08:40", 1_500.0)
    log(desk, "2025-06-11 09:10", 1_500.0)
    blocks = desk.blocks("CD-01", at("2025-06-11 08:40"), at("2025-06-11 12:00"))
    assert [b.start.hour for b in blocks] == [6, 9]
    assert [b.readings for b in blocks] == [1, 1]


def test_a_block_with_the_device_down_has_no_average(desk: PlantDesk) -> None:
    desk.log("CD-01", at("2025-06-11 09:00"), running=False, flow=0.0, methane=0.0)
    blocks = desk.blocks("CD-01", at("2025-06-11 09:00"), at("2025-06-11 12:00"))
    assert blocks[0].average is None
    assert blocks[0].is_empty
    assert not blocks[0].below


def test_a_block_ignores_the_hours_the_device_was_off(desk: PlantDesk) -> None:
    log(desk, "2025-06-11 09:00", 1_520.0)
    desk.log("CD-01", at("2025-06-11 10:00"), running=False, flow=0.0, methane=0.0)
    desk.log("CD-01", at("2025-06-11 11:00"), running=False, flow=0.0, methane=0.0)
    blocks = desk.blocks("CD-01", at("2025-06-11 09:00"), at("2025-06-11 12:00"))
    assert blocks[0].average == pytest.approx(1_520.0)
    assert blocks[0].running == 1


def test_an_outage_takes_a_label_and_closes_once(desk: PlantDesk) -> None:
    outage = desk.start_outage("CD-01", at("2025-06-11 09:00"), "blower bearing")
    assert outage.label == "OT-2025-001"
    assert [o.label for o in desk.down_now("NORTHRIDGE")] == [outage.label]
    desk.end_outage(outage.label, at("2025-06-12 15:00"), "bearing replaced")
    assert desk.down_now("NORTHRIDGE") == []


def test_a_device_already_down_cannot_go_down_again(desk: PlantDesk) -> None:
    desk.start_outage("CD-01", at("2025-06-11 09:00"), "blower bearing")
    with pytest.raises(StateError, match="already down"):
        desk.start_outage("CD-01", at("2025-06-11 10:00"), "again")


def test_an_outage_past_the_shutdown_window_is_listed(desk: PlantDesk) -> None:
    desk.start_outage("CD-01", at("2025-06-11 09:00"), "flame arrestor")
    assert desk.long_outages("NORTHRIDGE", at("2025-06-16 08:00")) == []
    assert len(desk.long_outages("NORTHRIDGE", at("2025-06-16 10:00"))) == 1


def test_a_device_with_an_outage_open_cannot_be_retired(desk: PlantDesk) -> None:
    desk.start_outage("CD-01", at("2025-06-11 09:00"), "blower bearing")
    with pytest.raises(RuleError, match="outage open"):
        desk.retire("CD-01", dt.date(2026, 3, 1))


def test_availability_is_the_share_of_records_that_ran(desk: PlantDesk) -> None:
    log(desk, "2025-06-11 09:00", 1_500.0)
    desk.log("CD-01", at("2025-06-11 10:00"), running=False, flow=0.0, methane=0.0)
    share = desk.availability("CD-01", at("2025-06-11 09:00"), at("2025-06-11 12:00"))
    assert share == pytest.approx(0.5)


def test_availability_with_no_records_at_all_is_nothing(desk: PlantDesk) -> None:
    assert desk.availability("CD-01", at("2025-06-11 09:00"), at("2025-06-11 12:00")) == 0.0
    assert desk.throughput("CD-01", at("2025-06-11 09:00"), at("2025-06-11 12:00")) == 0.0


def test_downtime_is_clipped_to_the_range_asked_about(desk: PlantDesk) -> None:
    outage = desk.start_outage("CD-01", at("2025-06-11 09:00"), "blower bearing")
    desk.end_outage(outage.label, at("2025-06-12 15:00"))
    hours = desk.downtime_hours("CD-01", at("2025-06-12 00:00"), at("2025-06-13 00:00"))
    assert hours == pytest.approx(15.0)


def test_throughput_is_the_methane_that_went_through(desk: PlantDesk) -> None:
    log(desk, "2025-06-11 09:00", 1_500.0)
    log(desk, "2025-06-11 10:00", 1_500.0, flow=1_000.0, methane=50.0)
    assert desk.throughput(
        "CD-01", at("2025-06-11 09:00"), at("2025-06-11 12:00")
    ) == pytest.approx((1_180.0 * 0.492 + 500.0) / 2)

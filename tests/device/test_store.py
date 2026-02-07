"""Devices go into the book and come back out unchanged."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import DuplicateError, UnknownError
from gemwalk.model.device import Device, Kind, State
from gemwalk.store.book import Book
from gemwalk.store.devices import DeviceRepository
from gemwalk.units import Temperature
from tests.support import bare


@pytest.fixture
def devices(book: Book) -> DeviceRepository:
    bare(book)
    return DeviceRepository(book)


def a_device(label: str = "VW-041", area: str = "A-03") -> Device:
    return Device(
        label=label,
        site="NORTHRIDGE",
        area=area,
        kind=Kind.VERTICAL,
        station="N 12+40 E 3+15",
        total_depth=92.0,
        screen_top=22.0,
        screen_bottom=86.0,
        drilled_on=dt.date(2021, 5, 12),
    )


def test_a_device_round_trips_through_the_book(devices: DeviceRepository) -> None:
    devices.add(a_device())
    assert devices.get("VW-041") == a_device()


def test_every_field_survives_the_trip(devices: DeviceRepository) -> None:
    built = (
        a_device()
        .connect(dt.date(2021, 6, 2))
        .approve_higher_temperature(Temperature(145.0), dt.date(2025, 3, 1))
    )
    devices.add(built)
    assert devices.get("VW-041") == built


def test_the_same_label_cannot_be_drilled_twice(devices: DeviceRepository) -> None:
    devices.add(a_device())
    with pytest.raises(DuplicateError):
        devices.add(a_device())


def test_a_label_the_book_never_issued_is_refused(devices: DeviceRepository) -> None:
    with pytest.raises(UnknownError, match="VW-999"):
        devices.get("VW-999")
    assert devices.find("VW-999") is None


def test_a_device_written_back_replaces_itself(devices: DeviceRepository) -> None:
    devices.add(a_device())
    devices.put(devices.get("VW-041").connect(dt.date(2021, 6, 2)))
    assert devices.get("VW-041").state is State.CONNECTED
    assert devices.count() == 1


def test_a_device_that_is_not_there_cannot_be_written_back(devices: DeviceRepository) -> None:
    with pytest.raises(UnknownError):
        devices.put(a_device("VW-999"))


def test_only_connected_devices_go_on_the_run(devices: DeviceRepository) -> None:
    devices.add(a_device("VW-041").connect(dt.date(2021, 6, 2)))
    devices.add(a_device("VW-042"))
    assert [d.label for d in devices.monitored("NORTHRIDGE")] == ["VW-041"]


def test_devices_come_back_by_area_and_by_state(devices: DeviceRepository) -> None:
    devices.add(a_device("VW-041", "A-03"))
    devices.add(a_device("VW-042", "A-04"))
    assert [d.label for d in devices.of_area("A-04")] == ["VW-042"]
    assert len(devices.in_state("NORTHRIDGE", State.DRILLED)) == 2
    assert devices.labels() == ["VW-041", "VW-042"]


def test_a_device_can_be_taken_back_out_of_the_book(devices: DeviceRepository) -> None:
    devices.add(a_device())
    devices.remove("VW-041")
    assert devices.count() == 0
    with pytest.raises(UnknownError):
        devices.remove("VW-041")

"""The plant records go into the book and come back out unchanged."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import DuplicateError
from gemwalk.model.plant import Control, ControlKind, Operation, Outage
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book
from gemwalk.store.plant import (
    ControlRepository,
    OperationRepository,
    OutageRepository,
    stamp,
    unstamp,
)

ZONE = "America/Chicago"


@pytest.fixture
def store(book: Book) -> tuple[ControlRepository, OperationRepository, OutageRepository]:
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
    controls = ControlRepository(book)
    controls.add(a_control())
    return controls, OperationRepository(book), OutageRepository(book)


def a_control(label: str = "CD-01", **changes: object) -> Control:
    fields: dict[str, object] = {
        "label": label,
        "site": "NORTHRIDGE",
        "name": "west flare",
        "kind": ControlKind.ENCLOSED_FLARE,
        "capacity": 2_400.0,
        "installed_on": dt.date(2016, 4, 1),
        "floor_degrees": 1_400.0,
    }
    fields.update(changes)
    return Control(**fields)  # type: ignore[arg-type]


def an_operation(at: str, **changes: object) -> Operation:
    fields: dict[str, object] = {
        "control": "CD-01",
        "at": read_moment(at, ZONE),
        "running": True,
        "flow": 1_180.0,
        "methane": 49.2,
        "temperature": 1_512.0,
    }
    fields.update(changes)
    return Operation(**fields)  # type: ignore[arg-type]


def test_a_moment_survives_the_trip_through_the_book() -> None:
    moment = read_moment("2025-06-11 09:00", ZONE)
    assert unstamp(stamp(moment)) == moment


def test_a_control_device_round_trips(
    store: tuple[ControlRepository, OperationRepository, OutageRepository],
) -> None:
    controls, _, _ = store
    assert controls.get("CD-01") == a_control()


def test_a_candlestick_with_no_floor_round_trips(
    store: tuple[ControlRepository, OperationRepository, OutageRepository],
) -> None:
    controls, _, _ = store
    stick = a_control("CD-02", kind=ControlKind.CANDLESTICK, floor_degrees=None)
    controls.add(stick)
    assert controls.get("CD-02") == stick
    assert len(controls.live("NORTHRIDGE")) == 2


def test_a_retired_device_leaves_the_live_list(
    store: tuple[ControlRepository, OperationRepository, OutageRepository],
) -> None:
    controls, _, _ = store
    controls.put(controls.get("CD-01").retire(dt.date(2026, 3, 1)))
    assert controls.live("NORTHRIDGE") == []
    assert len(controls.of_site("NORTHRIDGE")) == 1


def test_an_operating_record_round_trips_with_its_moment(
    store: tuple[ControlRepository, OperationRepository, OutageRepository],
) -> None:
    _, operations, _ = store
    stored = operations.add(an_operation("2025-06-11 09:00"))
    assert stored.id > 0
    assert operations.get(str(stored.id)) == stored


def test_a_device_cannot_have_two_records_at_one_moment(
    store: tuple[ControlRepository, OperationRepository, OutageRepository],
) -> None:
    _, operations, _ = store
    operations.add(an_operation("2025-06-11 09:00"))
    with pytest.raises(DuplicateError):
        operations.add(an_operation("2025-06-11 09:00"))


def test_records_come_back_in_clock_order(
    store: tuple[ControlRepository, OperationRepository, OutageRepository],
) -> None:
    _, operations, _ = store
    for at in ("2025-06-11 11:00", "2025-06-11 09:00", "2025-06-11 10:00"):
        operations.add(an_operation(at))
    walked = operations.of_control("CD-01")
    assert [o.at.hour for o in walked] == [14, 15, 16]


def test_a_range_takes_the_first_moment_and_not_the_last(
    store: tuple[ControlRepository, OperationRepository, OutageRepository],
) -> None:
    _, operations, _ = store
    for at in ("2025-06-11 09:00", "2025-06-11 10:00", "2025-06-11 12:00"):
        operations.add(an_operation(at))
    inside = operations.between(
        "CD-01", read_moment("2025-06-11 09:00", ZONE), read_moment("2025-06-11 12:00", ZONE)
    )
    assert len(inside) == 2


def test_the_latest_record_is_the_last_one_on_the_clock(
    store: tuple[ControlRepository, OperationRepository, OutageRepository],
) -> None:
    _, operations, _ = store
    assert operations.latest("CD-01") is None
    for at in ("2025-06-11 09:00", "2025-06-11 12:00"):
        operations.add(an_operation(at))
    latest = operations.latest("CD-01")
    assert latest is not None
    assert latest.at == read_moment("2025-06-11 12:00", ZONE)


def test_an_outage_round_trips_open_and_closed(
    store: tuple[ControlRepository, OperationRepository, OutageRepository],
) -> None:
    _, _, outages = store
    outage = Outage(
        label="OT-2025-004",
        control="CD-01",
        site="NORTHRIDGE",
        started_at=read_moment("2025-06-11 09:00", ZONE),
        reason="blower bearing",
    )
    outages.add(outage)
    assert outages.get("OT-2025-004") == outage
    assert [o.label for o in outages.open_at("NORTHRIDGE")] == ["OT-2025-004"]
    closed = outage.close(read_moment("2025-06-12 15:00", ZONE))
    outages.put(closed)
    assert outages.get("OT-2025-004") == closed
    assert outages.open_at("NORTHRIDGE") == []


def test_an_outage_that_touches_a_range_comes_back(
    store: tuple[ControlRepository, OperationRepository, OutageRepository],
) -> None:
    _, _, outages = store
    outages.add(
        Outage(
            label="OT-2025-004",
            control="CD-01",
            site="NORTHRIDGE",
            started_at=read_moment("2025-06-11 09:00", ZONE),
            ended_at=read_moment("2025-06-12 15:00", ZONE),
            reason="blower bearing",
        )
    )
    touching = outages.overlapping(
        "NORTHRIDGE", read_moment("2025-06-12 00:00", ZONE), read_moment("2025-06-13 00:00", ZONE)
    )
    assert [o.label for o in touching] == ["OT-2025-004"]
    apart = outages.overlapping(
        "NORTHRIDGE", read_moment("2025-06-13 00:00", ZONE), read_moment("2025-06-14 00:00", ZONE)
    )
    assert apart == []
    assert len(outages.of_control("CD-01")) == 1


def test_an_open_outage_touches_every_later_range(
    store: tuple[ControlRepository, OperationRepository, OutageRepository],
) -> None:
    _, _, outages = store
    outages.add(
        Outage(
            label="OT-2025-005",
            control="CD-01",
            site="NORTHRIDGE",
            started_at=read_moment("2025-06-11 09:00", ZONE),
            reason="flame arrestor",
        )
    )
    touching = outages.overlapping(
        "NORTHRIDGE", read_moment("2026-01-01 00:00", ZONE), read_moment("2026-01-02 00:00", ZONE)
    )
    assert [o.label for o in touching] == ["OT-2025-005"]

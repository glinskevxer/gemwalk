"""The liquid records go into the book and come back out unchanged."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import DuplicateError
from gemwalk.model.liquids import Level, Pumpout, Sump, SumpKind
from gemwalk.store.book import Book
from gemwalk.store.liquids import LevelRepository, PumpoutRepository, SumpRepository
from tests.support import ZONE, bare, sink

JUNE = dt.date(2025, 6, 3)


@pytest.fixture
def store(book: Book) -> tuple[SumpRepository, LevelRepository, PumpoutRepository]:
    sink(bare(book), 2, connect=False)
    sumps = SumpRepository(book)
    sumps.add(a_sump())
    return sumps, LevelRepository(book), PumpoutRepository(book)


def a_sump(label: str = "CS-004", **changes: object) -> Sump:
    fields: dict[str, object] = {
        "label": label,
        "site": "NORTHRIDGE",
        "station": "HD-01 low point",
        "kind": SumpKind.KNOCKOUT,
        "capacity": 550.0,
        "installed_on": dt.date(2019, 9, 3),
    }
    fields.update(changes)
    return Sump(**fields)  # type: ignore[arg-type]


def test_a_sump_round_trips_and_retires(
    store: tuple[SumpRepository, LevelRepository, PumpoutRepository],
) -> None:
    sumps, _, _ = store
    assert sumps.get("CS-004") == a_sump()
    sumps.put(sumps.get("CS-004").retire(dt.date(2026, 2, 1)))
    assert sumps.live("NORTHRIDGE") == []
    assert len(sumps.of_site("NORTHRIDGE")) == 1


def test_a_level_round_trips(
    store: tuple[SumpRepository, LevelRepository, PumpoutRepository],
) -> None:
    _, levels, _ = store
    stored = levels.add(Level(device="VW-001", taken_on=JUNE, depth=70.0, pumped=True))
    assert stored.id > 0
    assert levels.get(str(stored.id)) == stored


def test_a_well_cannot_be_tapped_twice_on_one_day(
    store: tuple[SumpRepository, LevelRepository, PumpoutRepository],
) -> None:
    _, levels, _ = store
    levels.add(Level(device="VW-001", taken_on=JUNE, depth=70.0))
    with pytest.raises(DuplicateError):
        levels.add(Level(device="VW-001", taken_on=JUNE, depth=71.0))


def test_the_history_of_a_well_comes_back_oldest_first(
    store: tuple[SumpRepository, LevelRepository, PumpoutRepository],
) -> None:
    _, levels, _ = store
    levels.add(Level(device="VW-001", taken_on=dt.date(2025, 7, 1), depth=68.0))
    levels.add(Level(device="VW-001", taken_on=JUNE, depth=70.0))
    assert [x.taken_on for x in levels.of_device("VW-001")] == [JUNE, dt.date(2025, 7, 1)]


def test_the_latest_level_is_the_one_on_or_before_the_day(
    store: tuple[SumpRepository, LevelRepository, PumpoutRepository],
) -> None:
    _, levels, _ = store
    levels.add(Level(device="VW-001", taken_on=JUNE, depth=70.0))
    levels.add(Level(device="VW-001", taken_on=dt.date(2025, 7, 1), depth=68.0))
    latest = levels.latest_for("VW-001", dt.date(2025, 6, 30))
    assert latest is not None
    assert latest.depth == pytest.approx(70.0)
    assert levels.latest_for("VW-001", dt.date(2025, 1, 1)) is None


def test_a_day_of_tape_drops_comes_back_in_well_order(
    store: tuple[SumpRepository, LevelRepository, PumpoutRepository],
) -> None:
    _, levels, _ = store
    levels.add(Level(device="VW-002", taken_on=JUNE, depth=64.0))
    levels.add(Level(device="VW-001", taken_on=JUNE, depth=70.0))
    assert [x.device for x in levels.on_day(JUNE)] == ["VW-001", "VW-002"]


def test_a_pumpout_round_trips_with_its_moment(
    store: tuple[SumpRepository, LevelRepository, PumpoutRepository],
) -> None:
    _, _, pumpouts = store
    load = Pumpout(
        sump="CS-004",
        at=read_moment("2025-06-03 10:20", ZONE),
        gallons=410.0,
        hauler="Vestermark Vacuum",
        bound_for="leachate pretreatment",
    )
    stored = pumpouts.add(load)
    assert pumpouts.get(str(stored.id)) == stored
    assert [p.gallons for p in pumpouts.of_sump("CS-004")] == pytest.approx([410.0])


def test_gallons_add_up_inside_a_range_and_not_outside_it(
    store: tuple[SumpRepository, LevelRepository, PumpoutRepository],
) -> None:
    _, _, pumpouts = store
    for at, gallons in (("2025-06-03 10:20", 410.0), ("2025-06-19 09:00", 520.0)):
        pumpouts.add(
            Pumpout(
                sump="CS-004",
                at=read_moment(at, ZONE),
                gallons=gallons,
                hauler="Vestermark Vacuum",
                bound_for="leachate pretreatment",
            )
        )
    june = pumpouts.gallons_between(
        "CS-004", read_moment("2025-06-01 00:00", ZONE), read_moment("2025-07-01 00:00", ZONE)
    )
    assert june == pytest.approx(930.0)
    early = pumpouts.gallons_between(
        "CS-004", read_moment("2025-06-01 00:00", ZONE), read_moment("2025-06-10 00:00", ZONE)
    )
    assert early == pytest.approx(410.0)


def test_a_sump_with_no_loads_has_pumped_nothing(
    store: tuple[SumpRepository, LevelRepository, PumpoutRepository],
) -> None:
    _, _, pumpouts = store
    assert pumpouts.gallons_between(
        "CS-004", read_moment("2025-06-01 00:00", ZONE), read_moment("2025-07-01 00:00", ZONE)
    ) == pytest.approx(0.0)
    assert (
        pumpouts.between(
            read_moment("2025-06-01 00:00", ZONE), read_moment("2025-07-01 00:00", ZONE)
        )
        == []
    )

"""Runs and readings go into the book and come back out unchanged."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import DuplicateError, UnknownError
from gemwalk.model.device import Kind
from gemwalk.model.reading import Reading, Run
from gemwalk.service.sites import SiteDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.store.book import Book
from gemwalk.store.readings import ReadingRepository, RunRepository

APRIL = dt.date(2025, 4, 8)
MAY = dt.date(2025, 5, 6)


@pytest.fixture
def store(book: Book) -> tuple[RunRepository, ReadingRepository]:
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
        wells.drill(
            "NORTHRIDGE",
            "A-03",
            kind=Kind.VERTICAL,
            station="N 12+40",
            total_depth=92.0,
            screen_top=22.0,
            screen_bottom=86.0,
            on=dt.date(2021, 5, 12),
        )
    runs = RunRepository(book)
    runs.add(
        Run(
            label="MR-2025-04-01",
            site="NORTHRIDGE",
            started_on=APRIL,
            monitor="D. Kasprzak",
            meter="GEM5000-40912",
        )
    )
    return runs, ReadingRepository(book)


def a_reading(device: str = "VW-001", run: str = "MR-2025-04-01", **changes: object) -> Reading:
    fields: dict[str, object] = {
        "run": run,
        "device": device,
        "taken_on": APRIL,
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
    return Reading(**fields)  # type: ignore[arg-type]


def test_a_reading_comes_back_with_the_number_the_book_chose(
    store: tuple[RunRepository, ReadingRepository],
) -> None:
    _, readings = store
    stored = readings.add(a_reading())
    assert stored.id > 0
    assert readings.get(str(stored.id)) == stored


def test_every_field_survives_the_trip(
    store: tuple[RunRepository, ReadingRepository],
) -> None:
    _, readings = store
    stored = readings.add(a_reading(note="valve seized, freed with a wrench"))
    assert readings.get(str(stored.id)).note == "valve seized, freed with a wrench"


def test_a_device_cannot_be_read_twice_on_one_run(
    store: tuple[RunRepository, ReadingRepository],
) -> None:
    _, readings = store
    readings.add(a_reading())
    with pytest.raises(DuplicateError):
        readings.add(a_reading())


def test_the_readings_of_a_run_come_back_in_device_order(
    store: tuple[RunRepository, ReadingRepository],
) -> None:
    _, readings = store
    readings.add(a_reading("VW-002"))
    readings.add(a_reading("VW-001"))
    assert [r.device for r in readings.of_run("MR-2025-04-01")] == ["VW-001", "VW-002"]


def test_one_device_on_one_run_is_one_reading(
    store: tuple[RunRepository, ReadingRepository],
) -> None:
    _, readings = store
    readings.add(a_reading("VW-001"))
    assert readings.on_run_for("MR-2025-04-01", "VW-001") is not None
    assert readings.on_run_for("MR-2025-04-01", "VW-002") is None


def test_the_history_of_a_wellhead_comes_back_oldest_first(
    store: tuple[RunRepository, ReadingRepository],
) -> None:
    runs, readings = store
    runs.add(
        Run(
            label="MR-2025-05-01",
            site="NORTHRIDGE",
            started_on=MAY,
            monitor="D. Kasprzak",
            meter="GEM5000-40912",
        )
    )
    readings.add(a_reading("VW-001", "MR-2025-05-01", taken_on=MAY))
    readings.add(a_reading("VW-001", "MR-2025-04-01", taken_on=APRIL))
    assert [r.taken_on for r in readings.of_device("VW-001")] == [APRIL, MAY]


def test_the_latest_reading_is_the_one_on_or_before_the_day_asked_about(
    store: tuple[RunRepository, ReadingRepository],
) -> None:
    runs, readings = store
    runs.add(
        Run(
            label="MR-2025-05-01",
            site="NORTHRIDGE",
            started_on=MAY,
            monitor="D. Kasprzak",
            meter="GEM5000-40912",
        )
    )
    readings.add(a_reading("VW-001", "MR-2025-04-01", taken_on=APRIL))
    readings.add(a_reading("VW-001", "MR-2025-05-01", taken_on=MAY))
    assert readings.latest_for("VW-001", "2025-04-30") is not None
    latest = readings.latest_for("VW-001", "2025-04-30")
    assert latest is not None
    assert latest.taken_on == APRIL
    assert readings.latest_for("VW-001", "2025-01-01") is None


def test_readings_come_back_by_a_range_of_days(
    store: tuple[RunRepository, ReadingRepository],
) -> None:
    runs, readings = store
    runs.add(
        Run(
            label="MR-2025-05-01",
            site="NORTHRIDGE",
            started_on=MAY,
            monitor="D. Kasprzak",
            meter="GEM5000-40912",
        )
    )
    readings.add(a_reading("VW-001", "MR-2025-04-01", taken_on=APRIL))
    readings.add(a_reading("VW-001", "MR-2025-05-01", taken_on=MAY))
    inside = readings.between("VW-001", "2025-04-01", "2025-04-30")
    assert [r.taken_on for r in inside] == [APRIL]


def test_a_run_round_trips_and_closes(
    store: tuple[RunRepository, ReadingRepository],
) -> None:
    runs, _ = store
    run = runs.get("MR-2025-04-01")
    assert run.monitor == "D. Kasprzak"
    assert [r.label for r in runs.open_runs("NORTHRIDGE")] == ["MR-2025-04-01"]
    runs.put(run.close(dt.date(2025, 4, 10)))
    assert runs.open_runs("NORTHRIDGE") == []
    assert [r.label for r in runs.of_site("NORTHRIDGE")] == ["MR-2025-04-01"]


def test_runs_come_back_by_a_range_of_days(
    store: tuple[RunRepository, ReadingRepository],
) -> None:
    runs, _ = store
    assert len(runs.between("NORTHRIDGE", "2025-04-01", "2025-04-30")) == 1
    assert runs.between("NORTHRIDGE", "2025-05-01", "2025-05-31") == []


def test_a_reading_number_the_book_never_issued_is_refused(
    store: tuple[RunRepository, ReadingRepository],
) -> None:
    _, readings = store
    with pytest.raises(UnknownError):
        readings.get("404")

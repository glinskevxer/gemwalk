"""Exceedances and rechecks go into the book and come back out unchanged."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import DuplicateError
from gemwalk.model.exceedance import Exceedance, Recheck, Stage
from gemwalk.model.reading import Reading, Run
from gemwalk.rules import Finding
from gemwalk.service.sites import SiteDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.store.book import Book
from gemwalk.store.exceedances import ExceedanceRepository, RecheckRepository
from gemwalk.store.readings import ReadingRepository, RunRepository

OPENED = dt.date(2025, 4, 8)


@pytest.fixture
def store(book: Book) -> tuple[ExceedanceRepository, RecheckRepository]:
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
    runs = RunRepository(book)
    runs.add(
        Run(
            label="MR-2025-04-01",
            site="NORTHRIDGE",
            started_on=OPENED,
            monitor="D. Kasprzak",
            meter="GEM5000-40912",
        )
    )
    readings = ReadingRepository(book)
    for device in ("VW-001", "VW-002"):
        readings.add(
            Reading(
                run="MR-2025-04-01",
                device=device,
                taken_on=OPENED,
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
        )
    return ExceedanceRepository(book), RecheckRepository(book)


def an_exceedance(
    label: str = "EX-2025-001", device: str = "VW-001", **changes: object
) -> Exceedance:
    fields: dict[str, object] = {
        "label": label,
        "site": "NORTHRIDGE",
        "device": device,
        "kind": Finding.TEMPERATURE,
        "opened_on": OPENED,
        "reading": 1,
        "value": 138.0,
        "limit_value": 131.0,
    }
    fields.update(changes)
    return Exceedance(**fields)  # type: ignore[arg-type]


def test_an_exceedance_round_trips(
    store: tuple[ExceedanceRepository, RecheckRepository],
) -> None:
    found, _ = store
    found.add(an_exceedance())
    assert found.get("EX-2025-001") == an_exceedance()


def test_a_closed_exceedance_round_trips(
    store: tuple[ExceedanceRepository, RecheckRepository],
) -> None:
    found, _ = store
    closed = an_exceedance().close(dt.date(2025, 4, 12), "valve turned in")
    found.add(closed)
    assert found.get("EX-2025-001") == closed


def test_the_same_label_cannot_be_opened_twice(
    store: tuple[ExceedanceRepository, RecheckRepository],
) -> None:
    found, _ = store
    found.add(an_exceedance())
    with pytest.raises(DuplicateError):
        found.add(an_exceedance())


def test_only_open_exceedances_come_back_from_the_open_list(
    store: tuple[ExceedanceRepository, RecheckRepository],
) -> None:
    found, _ = store
    found.add(an_exceedance())
    found.add(an_exceedance("EX-2025-002", "VW-002").close(dt.date(2025, 4, 12)))
    assert [e.label for e in found.open_at("NORTHRIDGE")] == ["EX-2025-001"]
    assert [e.label for e in found.open_on_device("VW-001")] == ["EX-2025-001"]
    assert found.open_on_device("VW-002") == []


def test_one_wellhead_has_at_most_one_open_exceedance_of_a_kind(
    store: tuple[ExceedanceRepository, RecheckRepository],
) -> None:
    found, _ = store
    found.add(an_exceedance())
    assert found.open_of_kind("VW-001", Finding.TEMPERATURE) is not None
    assert found.open_of_kind("VW-001", Finding.OXYGEN) is None


def test_the_history_of_a_wellhead_comes_back_oldest_first(
    store: tuple[ExceedanceRepository, RecheckRepository],
) -> None:
    found, _ = store
    found.add(an_exceedance("EX-2025-002", opened_on=dt.date(2025, 6, 3)))
    found.add(an_exceedance("EX-2025-001"))
    assert [e.label for e in found.of_device("VW-001")] == ["EX-2025-001", "EX-2025-002"]


def test_exceedances_come_back_by_a_range_of_days_and_by_reading(
    store: tuple[ExceedanceRepository, RecheckRepository],
) -> None:
    found, _ = store
    found.add(an_exceedance())
    found.add(an_exceedance("EX-2025-002", "VW-002", reading=2, opened_on=dt.date(2025, 6, 3)))
    inside = found.between_days("NORTHRIDGE", "2025-04-01", "2025-04-30")
    assert [e.label for e in inside] == ["EX-2025-001"]
    assert [e.label for e in found.for_reading(2)] == ["EX-2025-002"]


def test_an_exceedance_written_back_keeps_its_label(
    store: tuple[ExceedanceRepository, RecheckRepository],
) -> None:
    found, _ = store
    found.add(an_exceedance())
    found.put(found.get("EX-2025-001").escalate())
    assert found.get("EX-2025-001").stage is Stage.ACTION
    assert found.count() == 1


def test_a_recheck_round_trips_with_the_number_the_book_chose(
    store: tuple[ExceedanceRepository, RecheckRepository],
) -> None:
    found, rechecks = store
    found.add(an_exceedance())
    stored = rechecks.add(
        Recheck(
            exceedance="EX-2025-001",
            taken_on=dt.date(2025, 4, 12),
            value=134.0,
            clear=False,
            stage=Stage.CORRECT,
            note="valve opened a turn",
        )
    )
    assert stored.id > 0
    assert rechecks.get(str(stored.id)) == stored


def test_the_rechecks_of_an_exceedance_come_back_oldest_first(
    store: tuple[ExceedanceRepository, RecheckRepository],
) -> None:
    found, rechecks = store
    found.add(an_exceedance())
    for day, value in ((dt.date(2025, 4, 20), 129.0), (dt.date(2025, 4, 12), 134.0)):
        rechecks.add(
            Recheck(
                exceedance="EX-2025-001",
                taken_on=day,
                value=value,
                clear=value < 131.0,
                stage=Stage.CORRECT,
            )
        )
    walked = rechecks.of_exceedance("EX-2025-001")
    assert [r.taken_on for r in walked] == [dt.date(2025, 4, 12), dt.date(2025, 4, 20)]
    last = rechecks.last_for("EX-2025-001")
    assert last is not None
    assert last.clear


def test_an_exceedance_with_no_rechecks_has_no_last_one(
    store: tuple[ExceedanceRepository, RecheckRepository],
) -> None:
    found, rechecks = store
    found.add(an_exceedance())
    assert rechecks.last_for("EX-2025-001") is None
    assert rechecks.of_exceedance("EX-2025-001") == []

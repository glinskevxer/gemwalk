"""Faults go into the book and come back out unchanged."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import DuplicateError
from gemwalk.model.fault import Damage, Fault
from gemwalk.store.book import Book
from gemwalk.store.faults import FaultRepository
from tests.support import SITE, bare

FOUND = dt.date(2025, 5, 13)


@pytest.fixture
def faults(book: Book) -> FaultRepository:
    bare(book)
    return FaultRepository(book)


def a_fault(label: str = "CF-2025-001", area: str = "A-03", **changes: object) -> Fault:
    fields: dict[str, object] = {
        "label": label,
        "site": SITE,
        "area": area,
        "kind": Damage.SETTLEMENT,
        "station": "grid 14-J",
        "extent": 120.0,
        "found_on": FOUND,
        "found_by": "T. Wierzbicki",
    }
    fields.update(changes)
    return Fault(**fields)  # type: ignore[arg-type]


def test_a_fault_round_trips(faults: FaultRepository) -> None:
    faults.add(a_fault())
    assert faults.get("CF-2025-001") == a_fault()


def test_a_fixed_fault_round_trips(faults: FaultRepository) -> None:
    fixed = a_fault().fix(dt.date(2025, 5, 20), "regraded")
    faults.add(fixed)
    assert faults.get("CF-2025-001") == fixed


def test_the_same_label_cannot_be_used_twice(faults: FaultRepository) -> None:
    faults.add(a_fault())
    with pytest.raises(DuplicateError):
        faults.add(a_fault())


def test_only_open_faults_come_back_from_the_open_list(faults: FaultRepository) -> None:
    faults.add(a_fault())
    faults.add(a_fault("CF-2025-002").fix(dt.date(2025, 5, 20)))
    assert [f.label for f in faults.open_at(SITE)] == ["CF-2025-001"]


def test_faults_come_back_by_area_and_by_kind(faults: FaultRepository) -> None:
    faults.add(a_fault())
    faults.add(a_fault("CF-2025-002", area="A-04", kind=Damage.EROSION))
    assert [f.label for f in faults.of_area("A-04")] == ["CF-2025-002"]
    assert [f.label for f in faults.of_kind(SITE, Damage.EROSION)] == ["CF-2025-002"]
    assert len(faults.of_site(SITE)) == 2


def test_faults_come_back_by_a_range_of_days(faults: FaultRepository) -> None:
    faults.add(a_fault())
    faults.add(a_fault("CF-2025-002", found_on=dt.date(2025, 8, 6)))
    inside = faults.between_days(SITE, "2025-05-01", "2025-05-31")
    assert [f.label for f in inside] == ["CF-2025-001"]

"""One counter per kind, scoped the way the paperwork is filed."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import UnknownError
from gemwalk.ids import SERIES, Labels, Scope
from gemwalk.store.book import Book

APRIL = dt.date(2025, 4, 8)
MAY = dt.date(2025, 5, 6)
NEXT_YEAR = dt.date(2026, 1, 12)


@pytest.fixture
def labels(book: Book) -> Labels:
    return Labels(book)


def test_a_well_number_runs_for_the_life_of_the_site(labels: Labels) -> None:
    assert labels.next("device", APRIL) == "VW-001"
    assert labels.next("device", MAY) == "VW-002"
    assert labels.next("device", NEXT_YEAR) == "VW-003"


def test_a_monitoring_run_starts_again_every_month(labels: Labels) -> None:
    assert labels.next("run", APRIL) == "MR-2025-04-01"
    assert labels.next("run", APRIL) == "MR-2025-04-02"
    assert labels.next("run", MAY) == "MR-2025-05-01"


def test_a_walkover_starts_again_every_quarter(labels: Labels) -> None:
    assert labels.next("walk", APRIL) == "SW-2025Q2-01"
    assert labels.next("walk", dt.date(2025, 6, 30)) == "SW-2025Q2-02"
    assert labels.next("walk", dt.date(2025, 7, 1)) == "SW-2025Q3-01"


def test_a_work_order_starts_again_every_year(labels: Labels) -> None:
    assert labels.next("order", APRIL) == "WO-2025-0001"
    assert labels.next("order", NEXT_YEAR) == "WO-2026-0001"


def test_a_finding_is_numbered_inside_its_year(labels: Labels) -> None:
    assert labels.next("finding", APRIL) == "EX-2025-001"
    assert labels.next("finding", MAY) == "EX-2025-002"


def test_a_counter_survives_the_book_being_shut(tmp_path: object, book: Book) -> None:
    first = Labels(book)
    assert first.next("device", APRIL) == "VW-001"
    second = Labels(book)
    assert second.next("device", APRIL) == "VW-002"


def test_the_counter_says_how_far_it_has_got(labels: Labels) -> None:
    assert labels.peek("device", APRIL) == 0
    labels.next("device", APRIL)
    labels.next("device", APRIL)
    assert labels.peek("device", APRIL) == 2


def test_a_book_seeded_off_paper_can_push_the_counter_forward(labels: Labels) -> None:
    labels.reserve("device", APRIL, 40)
    assert labels.next("device", APRIL) == "VW-041"


def test_pushing_a_counter_backwards_does_nothing(labels: Labels) -> None:
    labels.reserve("device", APRIL, 40)
    labels.reserve("device", APRIL, 5)
    assert labels.peek("device", APRIL) == 40


def test_a_kind_nobody_labels_is_refused(labels: Labels) -> None:
    with pytest.raises(UnknownError):
        labels.next("badger", APRIL)
    with pytest.raises(UnknownError):
        labels.peek("badger", APRIL)


def test_every_series_has_its_own_prefix() -> None:
    prefixes = [series.prefix for series in SERIES.values()]
    assert len(prefixes) == len(set(prefixes))


def test_the_book_lists_the_kinds_it_labels(labels: Labels) -> None:
    assert "device" in labels.kinds()
    assert labels.kinds() == sorted(SERIES)


def test_a_scope_key_says_which_bucket_a_day_is_in() -> None:
    assert Scope.FOREVER.key(APRIL) == "-"
    assert Scope.YEAR.key(APRIL) == "2025"
    assert Scope.QUARTER.key(APRIL) == "2025Q2"
    assert Scope.MONTH.key(APRIL) == "2025-04"


def test_the_counters_say_which_buckets_they_have_used(labels: Labels) -> None:
    labels.next("run", APRIL)
    labels.next("run", MAY)
    labels.next("run", MAY)
    assert labels.buckets("run") == [("2025-04", 1), ("2025-05", 2)]


def test_a_kind_that_has_handed_nothing_out_has_no_buckets(labels: Labels) -> None:
    assert labels.buckets("device") == []


def test_a_kind_nobody_labels_has_no_buckets_either(labels: Labels) -> None:
    with pytest.raises(UnknownError):
        labels.buckets("badger")

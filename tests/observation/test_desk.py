"""Watching a flare through the plant desk."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Quarter, read_moment
from gemwalk.errors import RuleError
from gemwalk.model.plant import ControlKind
from gemwalk.report.compliance import compliance_report
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, ZONE, furnish

JUNE = "2025-06-11 09:00"


@pytest.fixture
def office(book: Book) -> Office:
    made = furnish(Office(book))
    made.plant.install(
        "CD-02",
        SITE,
        "east stick",
        kind=ControlKind.CANDLESTICK,
        capacity=900.0,
        on=dt.date(2019, 5, 1),
    )
    return made


def watch(office: Office, minutes: float, smoke: float, at: str = JUNE) -> str:
    return office.plant.watch(
        "CD-02",
        read_moment(at, ZONE),
        watched=minutes,
        visible=smoke,
        observer="R. Bellingham",
    ).label


def test_a_watch_takes_the_label_of_its_year(office: Office) -> None:
    assert watch(office, 120.0, 2.0) == "VE-2025-001"


def test_an_enclosed_flare_has_no_flame_to_watch(office: Office) -> None:
    with pytest.raises(RuleError, match="no flame to watch"):
        office.plant.watch(
            "CD-01", read_moment(JUNE, ZONE), watched=120.0, visible=2.0, observer="R. B."
        )


def test_a_clean_watch_finds_nothing(office: Office) -> None:
    watch(office, 120.0, 2.0)
    assert office.plant.smoking(SITE) == []
    assert office.plant.unfinished_watches(SITE) == []


def test_a_smoking_flare_is_listed(office: Office) -> None:
    label = watch(office, 120.0, 6.0)
    assert [w.label for w in office.plant.smoking(SITE)] == [label]


def test_a_short_watch_on_course_to_be_over_is_listed_separately(office: Office) -> None:
    label = watch(office, 20.0, 4.0)
    assert office.plant.smoking(SITE) == []
    assert [w.label for w in office.plant.unfinished_watches(SITE)] == [label]


def test_the_watches_of_one_flare_come_back_oldest_first(office: Office) -> None:
    watch(office, 120.0, 2.0, "2025-06-12 09:00")
    watch(office, 120.0, 1.0, "2025-06-11 09:00")
    watches = office.plant.watches("CD-02")
    assert [w.started_at.day for w in watches] == [11, 12]


def test_a_flare_nobody_watched_has_no_watches(office: Office) -> None:
    assert office.plant.watches("CD-02") == []


def test_the_compliance_report_names_a_smoking_flare(office: Office) -> None:
    watch(office, 120.0, 6.0)
    section = compliance_report(office, SITE, Quarter(2025, 2)).find("the plant")
    assert section is not None
    body = "\n".join(section.lines())
    assert "1 watches found more smoke" in body
    assert "VE-2025-001" in body


def test_the_compliance_report_counts_the_short_watches(office: Office) -> None:
    watch(office, 20.0, 4.0)
    section = compliance_report(office, SITE, Quarter(2025, 2)).find("the plant")
    assert section is not None
    assert any("stopped before they could say anything" in line for line in section.body)


def test_a_quarter_with_no_watches_says_nothing_about_them(office: Office) -> None:
    section = compliance_report(office, SITE, Quarter(2025, 2)).find("the plant")
    assert section is not None
    assert not any("smoke" in line for line in section.body)

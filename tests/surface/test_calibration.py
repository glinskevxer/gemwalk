"""A walkover made with an uncalibrated detector is not a walkover."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Quarter, read_moment
from gemwalk.errors import RuleError
from gemwalk.model.instrument import Meter
from gemwalk.report.compliance import compliance_report
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, furnish

ZONE = "America/Chicago"
MAY = dt.date(2025, 5, 13)


@pytest.fixture
def office(book: Book) -> Office:
    made = furnish(Office(book))
    made.instruments.add(
        "TVA1000B-8841",
        SITE,
        kind=Meter.DETECTOR,
        maker="Verrick Instruments",
        model="TVA1000B",
        serial="8841",
        on=dt.date(2022, 3, 1),
    )
    return made


def calibrate(office: Office, at: str, after: float = 500.0) -> None:
    office.instruments.calibrate(
        "TVA1000B-8841",
        read_moment(at, ZONE),
        standard="500 ppm methane in air",
        expected=500.0,
        before=496.0,
        after=after,
        by_whom="T. Wierzbicki",
    )


def walk(office: Office, on: dt.date = MAY) -> str:
    return office.surface.open_walk(
        SITE,
        on,
        monitor="T. Wierzbicki",
        instrument="TVA1000B-8841",
        background=2.0,
        wind_mean=3.4,
        wind_gust=7.1,
    ).label


def test_a_walk_on_an_uncalibrated_detector_is_refused(office: Office) -> None:
    with pytest.raises(RuleError, match="no calibration"):
        walk(office)


def test_a_walk_on_a_calibrated_detector_opens(office: Office) -> None:
    calibrate(office, "2025-05-13 06:10")
    assert walk(office) == "SW-2025Q2-01"


def test_yesterday_s_calibration_does_not_cover_today_s_walk(office: Office) -> None:
    calibrate(office, "2025-05-12 06:10")
    with pytest.raises(RuleError, match="does not cover"):
        walk(office)


def test_a_detector_that_failed_its_check_cannot_walk(office: Office) -> None:
    calibrate(office, "2025-05-13 06:10", after=560.0)
    with pytest.raises(RuleError, match="out after the check"):
        walk(office)


def test_a_detector_off_an_old_paper_sheet_is_taken_as_written(office: Office) -> None:
    made = office.surface.open_walk(
        SITE,
        MAY,
        monitor="T. Wierzbicki",
        instrument="TVA-OLD-002",
        background=2.0,
        wind_mean=3.4,
        wind_gust=7.1,
    )
    assert made.instrument == "TVA-OLD-002"


def test_the_compliance_report_lists_the_instruments(office: Office) -> None:
    calibrate(office, "2025-05-13 06:10")
    section = compliance_report(office, SITE, Quarter(2025, 2)).find("the instruments")
    assert section is not None
    body = "\n".join(section.lines())
    assert "TVA1000B-8841" in body
    assert "flame ionisation detector" in body
    assert "8841" in body


def test_a_meter_not_calibrated_for_the_last_day_is_named(office: Office) -> None:
    calibrate(office, "2025-05-13 06:10")
    section = compliance_report(office, SITE, Quarter(2025, 2)).find("the instruments")
    assert section is not None
    assert any("not calibrated" in line for line in section.body)


def test_a_site_with_no_instruments_says_so(book: Book) -> None:
    office = furnish(Office(book))
    section = compliance_report(office, SITE, Quarter(2025, 2)).find("the instruments")
    assert section is not None
    assert "no instrument on the books" in "\n".join(section.lines())

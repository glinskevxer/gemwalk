"""Whether a meter was fit to use, and what makes the answer no."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import RuleError, StateError
from gemwalk.model.instrument import Meter
from gemwalk.service.instruments import InstrumentDesk, Standing
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from gemwalk.store.instruments import CalibrationRepository, InstrumentRepository
from tests.support import SITE, furnish

ZONE = "America/Chicago"
APRIL = dt.date(2025, 4, 8)


@pytest.fixture
def office(book: Book) -> Office:
    made = furnish(Office(book))
    made.instruments.add(
        "GEM5000-40912",
        SITE,
        kind=Meter.ANALYSER,
        maker="Verrick Instruments",
        model="GEM5000",
        serial="40912",
        on=dt.date(2022, 3, 1),
    )
    return made


def calibrate(office: Office, at: str, before: float = 49.6, after: float = 50.1) -> None:
    office.instruments.calibrate(
        "GEM5000-40912",
        read_moment(at, ZONE),
        standard="50% CH4 / 35% CO2 / balance N2",
        expected=50.0,
        before=before,
        after=after,
        by_whom="D. Kasprzak",
    )


def test_a_meter_with_no_calibration_at_all_is_not_fit(office: Office) -> None:
    standing = office.instruments.standing("GEM5000-40912", APRIL)
    assert not standing.is_good
    assert "no calibration on file" in str(standing)


def test_a_meter_calibrated_that_morning_is_fit(office: Office) -> None:
    calibrate(office, "2025-04-08 05:40")
    standing = office.instruments.standing("GEM5000-40912", APRIL)
    assert standing.is_good
    assert "passed" in str(standing)


def test_yesterday_s_calibration_does_not_cover_today(office: Office) -> None:
    calibrate(office, "2025-04-07 05:40")
    standing = office.instruments.standing("GEM5000-40912", APRIL)
    assert not standing.is_good
    assert "does not cover" in str(standing)


def test_a_meter_still_out_after_the_check_is_not_fit(office: Office) -> None:
    calibrate(office, "2025-04-08 05:40", after=56.0)
    standing = office.instruments.standing("GEM5000-40912", APRIL)
    assert not standing.is_good
    assert "out after the check" in str(standing)


def test_a_meter_that_had_drifted_is_fit_and_says_so(office: Office) -> None:
    calibrate(office, "2025-04-08 05:40", before=40.0, after=50.2)
    standing = office.instruments.standing("GEM5000-40912", APRIL)
    assert standing.is_good
    assert standing.drifted
    assert "in doubt" in str(standing)


def test_a_meter_out_of_service_cannot_be_calibrated(office: Office) -> None:
    office.instruments.retire("GEM5000-40912", dt.date(2025, 3, 1))
    with pytest.raises(StateError):
        calibrate(office, "2025-04-08 05:40")


def test_a_meter_that_is_not_fit_can_be_refused_outright(office: Office) -> None:
    with pytest.raises(RuleError, match="no calibration"):
        office.instruments.must_be_good("GEM5000-40912", APRIL)
    calibrate(office, "2025-04-08 05:40")
    assert office.instruments.must_be_good("GEM5000-40912", APRIL).is_good


def test_the_meters_that_are_due_are_listed(office: Office) -> None:
    assert [m.label for m in office.instruments.due(SITE, APRIL)] == ["GEM5000-40912"]
    calibrate(office, "2025-04-08 05:40")
    assert office.instruments.due(SITE, APRIL) == []


def test_a_retired_meter_is_never_due(office: Office) -> None:
    office.instruments.retire("GEM5000-40912", dt.date(2025, 3, 1))
    assert office.instruments.due(SITE, APRIL) == []


def test_a_thermocouple_stays_fit_for_a_year(office: Office) -> None:
    office.instruments.add(
        "TC-114",
        SITE,
        kind=Meter.THERMOCOUPLE,
        maker="Verrick Instruments",
        model="K-114",
        serial="114",
        on=dt.date(2022, 3, 1),
    )
    office.instruments.calibrate(
        "TC-114",
        read_moment("2025-01-06 09:00", ZONE),
        standard="ice bath",
        expected=32.0,
        before=32.4,
        after=32.0,
        by_whom="D. Kasprzak",
    )
    assert office.instruments.standing("TC-114", APRIL).is_good


def test_the_history_of_a_meter_comes_back_oldest_first(office: Office) -> None:
    calibrate(office, "2025-04-08 05:40")
    calibrate(office, "2025-04-09 05:35")
    history = office.instruments.history("GEM5000-40912")
    assert [c.day for c in history] == [dt.date(2025, 4, 8), dt.date(2025, 4, 9)]


def test_the_calibrations_of_one_day_come_back_together(office: Office) -> None:
    calibrate(office, "2025-04-08 05:40")
    calibrate(office, "2025-04-08 16:20")
    calibrate(office, "2025-04-09 05:35")
    assert len(office.instruments.used_on("GEM5000-40912", dt.date(2025, 4, 8))) == 2


def test_the_meters_of_one_kind_come_back_together(office: Office) -> None:
    found = office.instruments.instruments.of_kind(SITE, Meter.ANALYSER)
    assert [m.label for m in found] == ["GEM5000-40912"]
    assert office.instruments.instruments.of_kind(SITE, Meter.DETECTOR) == []


def test_the_office_makes_one_instrument_desk(office: Office) -> None:
    assert isinstance(office.instruments, InstrumentDesk)
    assert isinstance(office.instruments.instruments, InstrumentRepository)
    assert isinstance(office.instruments.calibrations, CalibrationRepository)


def test_a_standing_with_no_calibration_is_not_good() -> None:
    standing = Standing("X", APRIL, None, covered=False, passed=False, drifted=False)
    assert not standing.is_good


def test_a_calibration_round_trips_through_the_book(office: Office) -> None:
    calibrate(office, "2025-04-08 05:40")
    stored = office.instruments.calibrations.of_instrument("GEM5000-40912")[0]
    assert office.instruments.calibrations.get(str(stored.id)) == stored


def test_an_instrument_round_trips_through_the_book(office: Office) -> None:
    meter = office.instruments.instruments.get("GEM5000-40912")
    assert meter.serial == "40912"
    assert meter.kind is Meter.ANALYSER
    assert office.instruments.instruments.live(SITE) == [meter]


def test_a_run_on_a_meter_the_book_knows_needs_a_calibration(office: Office) -> None:
    with pytest.raises(RuleError, match="no calibration"):
        office.monitoring.open_run(SITE, APRIL, monitor="D. Kasprzak", meter="GEM5000-40912")


def test_a_run_on_a_calibrated_meter_opens(office: Office) -> None:
    calibrate(office, "2025-04-08 05:40")
    run = office.monitoring.open_run(SITE, APRIL, monitor="D. Kasprzak", meter="GEM5000-40912")
    assert run.meter == "GEM5000-40912"


def test_a_meter_off_an_old_paper_sheet_is_taken_as_written(office: Office) -> None:
    run = office.monitoring.open_run(SITE, APRIL, monitor="D. Kasprzak", meter="GEM-OLD-114")
    assert run.meter == "GEM-OLD-114"


def test_a_run_is_refused_on_a_meter_that_failed_its_check(office: Office) -> None:
    calibrate(office, "2025-04-08 05:40", after=56.0)
    with pytest.raises(RuleError, match="out after the check"):
        office.monitoring.open_run(SITE, APRIL, monitor="D. Kasprzak", meter="GEM5000-40912")

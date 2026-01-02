"""The instruments and the calibrations behind every reading."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import read_moment
from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.instrument import Calibration, Instrument, Meter

ZONE = "America/Chicago"
IN_SERVICE = dt.date(2022, 3, 1)


def a_meter(**changes: object) -> Instrument:
    fields: dict[str, object] = {
        "label": "GEM5000-40912",
        "site": "NORTHRIDGE",
        "kind": Meter.ANALYSER,
        "maker": "Verrick Instruments",
        "model": "GEM5000",
        "serial": "40912",
        "in_service": IN_SERVICE,
    }
    fields.update(changes)
    return Instrument(**fields)  # type: ignore[arg-type]


def a_check(**changes: object) -> Calibration:
    fields: dict[str, object] = {
        "instrument": "GEM5000-40912",
        "at": read_moment("2025-04-08 05:40", ZONE),
        "standard": "50% CH4 / 35% CO2 / balance N2",
        "expected": 50.0,
        "before": 49.6,
        "after": 50.1,
        "by_whom": "D. Kasprzak",
    }
    fields.update(changes)
    return Calibration(**fields)  # type: ignore[arg-type]


def test_an_instrument_has_a_serial() -> None:
    with pytest.raises(RuleError, match="serial"):
        a_meter(serial="  ")


def test_an_instrument_cannot_retire_before_it_went_in() -> None:
    with pytest.raises(OrderError):
        a_meter(retired_on=dt.date(2020, 1, 1))


def test_an_instrument_is_in_service_between_the_two_dates() -> None:
    meter = a_meter(retired_on=dt.date(2026, 1, 31))
    assert not meter.in_service_on(dt.date(2022, 2, 28))
    assert meter.in_service_on(dt.date(2026, 1, 31))
    assert not meter.in_service_on(dt.date(2026, 2, 1))


def test_an_instrument_retires_once() -> None:
    meter = a_meter().retire(dt.date(2026, 1, 31))
    assert not meter.is_live
    with pytest.raises(StateError):
        meter.retire(dt.date(2026, 2, 1))


def test_a_calibration_is_stamped_and_signed() -> None:
    with pytest.raises(RuleError, match="offset"):
        a_check(at=dt.datetime(2025, 4, 8, 5, 40))  # noqa: DTZ001
    with pytest.raises(RuleError, match="by somebody"):
        a_check(by_whom="  ")


def test_a_calibration_gas_has_a_value_on_the_bottle() -> None:
    with pytest.raises(RuleError, match="bottle"):
        a_check(expected=0.0)


def test_a_meter_cannot_read_below_nothing() -> None:
    with pytest.raises(RuleError, match="below nothing"):
        a_check(before=-1.0)


def test_the_drift_is_what_the_meter_said_before_it_was_touched() -> None:
    check = a_check(before=45.0, after=50.0)
    assert check.drift == pytest.approx(10.0)
    assert check.error == pytest.approx(0.0)


def test_a_meter_that_had_drifted_puts_the_readings_since_in_doubt() -> None:
    assert not a_check(before=48.0).drifted
    assert a_check(before=40.0).drifted


def test_a_meter_still_out_after_adjustment_has_not_passed() -> None:
    assert a_check().passed
    assert not a_check(after=56.0).passed


def test_a_meter_that_drifted_and_was_fixed_still_passes() -> None:
    check = a_check(before=40.0, after=50.2)
    assert check.drifted
    assert check.passed


def test_an_analyser_calibration_lasts_the_day() -> None:
    meter = a_meter()
    check = a_check()
    assert meter.covers(check, dt.date(2025, 4, 8))
    assert not meter.covers(check, dt.date(2025, 4, 9))


def test_a_calibration_does_not_cover_a_day_before_it() -> None:
    assert not a_meter().covers(a_check(), dt.date(2025, 4, 7))


def test_a_thermocouple_is_good_for_a_year() -> None:
    meter = a_meter(kind=Meter.THERMOCOUPLE)
    check = a_check()
    assert meter.covers(check, dt.date(2026, 1, 1))
    assert not meter.covers(check, dt.date(2026, 5, 1))


def test_a_detector_is_calibrated_the_day_it_walks() -> None:
    assert Meter.DETECTOR.good_for_days == 1
    assert str(Meter.DETECTOR) == "flame ionisation detector"


def test_a_calibration_is_filed_under_the_day_it_was_made() -> None:
    assert a_check().day == dt.date(2025, 4, 8)

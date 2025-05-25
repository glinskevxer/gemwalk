"""The unit readers take what a field sheet actually says."""

from __future__ import annotations

import pytest

from gemwalk.errors import RangeError, UnitError
from gemwalk.units import Flow, Percent, Ppmv, Pressure, Temperature


@pytest.mark.parametrize(
    ("text", "value"),
    [("52.4", 52.4), ("52.4%", 52.4), ("52.4 %", 52.4), ("0 pct", 0.0), ("18 percent", 18.0)],
)
def test_percent_reads_the_forms_the_sheet_uses(text: str, value: float) -> None:
    assert Percent.parse(text).value == pytest.approx(value)


def test_percent_refuses_a_concentration_over_the_scale() -> None:
    with pytest.raises(RangeError):
        Percent(101.0)


def test_percent_refuses_a_unit_it_does_not_know() -> None:
    with pytest.raises(UnitError):
        Percent.parse("52 ppm")


def test_a_surface_reading_in_percent_becomes_parts_per_million() -> None:
    assert Ppmv.parse("2.5%").value == pytest.approx(25_000)


def test_a_surface_reading_reads_back_as_a_concentration() -> None:
    assert Ppmv(500).as_percent().value == pytest.approx(0.05)


def test_celsius_comes_in_and_fahrenheit_goes_out() -> None:
    assert Temperature.parse("55 C").fahrenheit == pytest.approx(131.0)


def test_the_regulation_reads_the_sheet_back_in_celsius() -> None:
    assert Temperature.parse("131 F").celsius == pytest.approx(55.0)


def test_a_flare_chamber_is_a_temperature_and_is_not_a_wellhead_one() -> None:
    chamber = Temperature.parse("1512 F")
    assert not chamber.is_wellhead_range
    assert Temperature.parse("131 F").is_wellhead_range


def test_pressure_keeps_its_sign() -> None:
    assert Pressure.parse("-1.40 in. w.c.").inches == pytest.approx(-1.4)


def test_a_wellhead_at_atmosphere_counts_as_positive() -> None:
    assert Pressure(0.0).is_positive
    assert not Pressure(-0.01).is_positive


def test_flow_an_hour_becomes_flow_a_minute() -> None:
    assert Flow.parse("2520 scfh").scfm == pytest.approx(42.0)


def test_flow_cannot_be_negative() -> None:
    with pytest.raises(RangeError):
        Flow(-1.0)


@pytest.mark.parametrize(
    ("quantity", "shown"),
    [
        (Percent(52.42), "52.4%"),
        (Ppmv(499.6), "500 ppmv"),
        (Temperature(118.25), "118.2 F"),
        (Pressure(-1.4), '-1.40" w.c.'),
        (Flow(42.0), "42.0 scfm"),
    ],
)
def test_every_quantity_prints_the_way_the_sheet_is_written(quantity: object, shown: str) -> None:
    assert str(quantity) == shown


def test_a_blank_sheet_cell_is_not_a_number() -> None:
    with pytest.raises(UnitError):
        Temperature.parse("")

"""The refusals and the alternate units, one branch at a time.

Every one of these is a line the ordinary suite never reaches because the
ordinary suite reads sheets that are filled in correctly. They are the lines
that run on the day somebody types the wrong thing, which is the day the
message matters most.
"""

from __future__ import annotations

import pytest

from gemwalk.errors import RangeError, UnitError
from gemwalk.units import Flow, Percent, Ppmv, Pressure, Temperature


def test_a_surface_reading_below_nothing_is_refused() -> None:
    with pytest.raises(RangeError, match="surface reading"):
        Ppmv(-1.0)


def test_a_surface_reading_over_the_whole_atmosphere_is_refused() -> None:
    with pytest.raises(RangeError, match="surface reading"):
        Ppmv(1_000_001.0)


def test_a_surface_reading_of_the_whole_atmosphere_is_allowed() -> None:
    assert Ppmv(1_000_000.0).value == pytest.approx(1_000_000.0)


@pytest.mark.parametrize("text", ["480 mg", "480 badgers", "480 F"])
def test_a_surface_reading_in_a_unit_nobody_uses_is_refused(text: str) -> None:
    with pytest.raises(UnitError, match="surface reading"):
        Ppmv.parse(text)


@pytest.mark.parametrize(
    ("text", "value"),
    [("480", 480.0), ("480 ppm", 480.0), ("480 ppmv", 480.0), ("2.5 pct", 25_000.0)],
)
def test_every_form_of_a_surface_reading_reads(text: str, value: float) -> None:
    assert Ppmv.parse(text).value == pytest.approx(value)


@pytest.mark.parametrize("text", ["118 K", "118 badgers", "118 wc"])
def test_a_temperature_in_a_unit_nobody_uses_is_refused(text: str) -> None:
    with pytest.raises(UnitError, match="temperature"):
        Temperature.parse(text)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("118", 118.0),
        ("118 F", 118.0),
        ("118 degF", 118.0),
        ("118 °F", 118.0),
        ("55 C", 131.0),
        ("55 degC", 131.0),
        ("55 °C", 131.0),
    ],
)
def test_every_form_of_a_temperature_reads(text: str, value: float) -> None:
    assert Temperature.parse(text).fahrenheit == pytest.approx(value)


def test_a_temperature_off_the_thermocouple_scale_is_refused() -> None:
    with pytest.raises(RangeError, match="temperature"):
        Temperature(-41.0)
    with pytest.raises(RangeError, match="temperature"):
        Temperature(2_501.0)


@pytest.mark.parametrize("text", ["-1.4 psi", "-1.4 bar", "-1.4 badgers"])
def test_a_pressure_in_a_unit_nobody_uses_is_refused(text: str) -> None:
    with pytest.raises(UnitError, match="pressure"):
        Pressure.parse(text)


@pytest.mark.parametrize(
    "text",
    [
        "-1.4",
        "-1.4 in wc",
        "-1.4 in. w.c.",
        "-1.4 inch wc",
        "-1.4 inches wc",
        "-1.4 wc",
        "-1.4 iwc",
        "-1.4 in h2o",
    ],
)
def test_every_form_of_a_pressure_reads(text: str) -> None:
    assert Pressure.parse(text).inches == pytest.approx(-1.4)


def test_a_pressure_off_the_gauge_is_refused() -> None:
    with pytest.raises(RangeError, match="pressure"):
        Pressure(-201.0)
    with pytest.raises(RangeError, match="pressure"):
        Pressure(201.0)


@pytest.mark.parametrize("text", ["42 gpm", "42 lps", "42 badgers"])
def test_a_flow_in_a_unit_nobody_uses_is_refused(text: str) -> None:
    with pytest.raises(UnitError, match="flow"):
        Flow.parse(text)


@pytest.mark.parametrize(
    ("text", "value"),
    [("42", 42.0), ("42 scfm", 42.0), ("42 cfm", 42.0), ("2520 scfh", 42.0), ("2520 cfh", 42.0)],
)
def test_every_form_of_a_flow_reads(text: str, value: float) -> None:
    assert Flow.parse(text).scfm == pytest.approx(value)


@pytest.mark.parametrize("text", ["", "   ", "one", "-", "%"])
def test_a_cell_with_no_number_in_it_is_refused_by_every_reader(text: str) -> None:
    for reader in (Percent.parse, Ppmv.parse, Temperature.parse, Pressure.parse, Flow.parse):
        with pytest.raises(UnitError):
            reader(text)


@pytest.mark.parametrize("text", ["+1.4", "1.4", "-1.4", ".4", "-.4", "1.", "0"])
def test_a_number_written_any_ordinary_way_reads(text: str) -> None:
    assert isinstance(Pressure.parse(text).inches, float)


def test_the_quantities_compare_the_way_the_numbers_do() -> None:
    assert Percent(1.0) < Percent(2.0)
    assert Ppmv(400.0) < Ppmv(500.0)
    assert Temperature(118.0) < Temperature(131.0)
    assert Pressure(-2.0) < Pressure(-1.0)
    assert Flow(1.0) < Flow(2.0)

"""Reading a wellhead against the standard, and where the standards differ."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.assess import Assessment, Concern, Election, assess
from gemwalk.model.device import Device, Kind
from gemwalk.model.reading import Reading
from gemwalk.rules import CF, WWW, XXX, Finding
from gemwalk.units import Temperature

TAKEN = dt.date(2025, 4, 8)


def a_device(**changes: object) -> Device:
    fields: dict[str, object] = {
        "label": "VW-041",
        "site": "NORTHRIDGE",
        "area": "A-03",
        "kind": Kind.VERTICAL,
        "station": "N 12+40",
        "total_depth": 92.0,
        "screen_top": 22.0,
        "screen_bottom": 86.0,
        "drilled_on": dt.date(2021, 5, 12),
    }
    fields.update(changes)
    return Device(**fields)  # type: ignore[arg-type]


def a_reading(**changes: object) -> Reading:
    fields: dict[str, object] = {
        "run": "MR-2025-04-01",
        "device": "VW-041",
        "taken_on": TAKEN,
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


def read(reading: Reading, **changes: object) -> Assessment:
    device = changes.pop("device", a_device())
    standard = changes.pop("standard", XXX)
    election = changes.pop("election", None)
    return assess(reading, device, standard, election)  # type: ignore[arg-type]


def test_a_clean_wellhead_is_over_nothing() -> None:
    result = read(a_reading())
    assert result.is_clear
    assert result.exceedances == ()
    assert result.kinds == ()


def test_a_hot_wellhead_is_over_on_temperature() -> None:
    result = read(a_reading(temperature=138.0))
    assert result.kinds == (Finding.TEMPERATURE,)
    judgement = result.of(Finding.TEMPERATURE)
    assert judgement is not None
    assert judgement.limit == pytest.approx(131.0)
    assert "138.0 F" in str(judgement)


def test_a_wellhead_exactly_on_the_limit_is_not_over() -> None:
    assert read(a_reading(temperature=131.0)).is_clear


def test_an_approved_value_takes_a_hot_wellhead_back_under() -> None:
    raised = a_device().approve_higher_temperature(Temperature(145.0), dt.date(2025, 3, 1))
    assert read(a_reading(temperature=138.0), device=raised).is_clear


def test_an_approval_dated_after_the_reading_does_not_help() -> None:
    raised = a_device().approve_higher_temperature(Temperature(145.0), dt.date(2025, 5, 1))
    assert read(a_reading(temperature=138.0), device=raised).kinds == (Finding.TEMPERATURE,)


def test_oxygen_over_five_is_a_finding() -> None:
    result = read(a_reading(oxygen=6.2, balance=3.3))
    assert result.kinds == (Finding.OXYGEN,)


def test_the_older_standard_never_reads_nitrogen() -> None:
    reading = a_reading(oxygen=1.0, balance=26.0, methane=45.0, carbon=28.0)
    result = read(reading, standard=WWW, election=Election(nitrogen_alternative=True))
    assert result.of(Finding.NITROGEN) is None
    assert result.of(Finding.OXYGEN) is not None
    assert result.is_clear


def test_electing_nitrogen_moves_the_limit_onto_the_balance() -> None:
    reading = a_reading(oxygen=1.0, balance=26.0, methane=45.0, carbon=28.0)
    plain = read(reading, standard=XXX)
    elected = read(reading, standard=XXX, election=Election(nitrogen_alternative=True))
    assert plain.is_clear
    assert elected.kinds == (Finding.NITROGEN,)


def test_electing_nitrogen_can_clear_a_wellhead_that_was_over_on_oxygen() -> None:
    reading = a_reading(oxygen=6.2, balance=16.0, methane=45.0, carbon=32.8)
    assert read(reading, standard=CF).kinds == (Finding.OXYGEN,)
    elected = read(reading, standard=CF, election=Election(nitrogen_alternative=True))
    assert elected.is_clear


def test_a_wellhead_at_atmosphere_is_over_on_pressure() -> None:
    result = read(a_reading(static=0.0))
    assert result.kinds == (Finding.PRESSURE,)
    judgement = result.of(Finding.PRESSURE)
    assert judgement is not None
    assert "not under vacuum" in str(judgement)


def test_an_approved_alternative_stops_the_pressure_comparison_being_made() -> None:
    result = read(a_reading(static=1.2), election=Election(higher_pressure=True))
    assert result.of(Finding.PRESSURE) is None
    assert result.is_clear


def test_the_older_standard_has_no_pressure_alternative_to_elect() -> None:
    result = read(a_reading(static=1.2), standard=WWW, election=Election(higher_pressure=True))
    assert result.kinds == (Finding.PRESSURE,)


def test_a_wellhead_can_be_over_on_all_three_at_once() -> None:
    result = read(a_reading(temperature=140.0, oxygen=8.0, balance=1.5, static=0.4))
    assert result.kinds == (Finding.TEMPERATURE, Finding.OXYGEN, Finding.PRESSURE)


def test_the_report_order_is_temperature_then_gas_then_pressure() -> None:
    result = read(a_reading())
    assert [j.finding for j in result.judgements] == [
        Finding.TEMPERATURE,
        Finding.OXYGEN,
        Finding.PRESSURE,
    ]


def test_a_sheet_that_does_not_add_up_is_a_concern_not_a_finding() -> None:
    result = read(a_reading(balance=2.0))
    assert Concern.UNBALANCED in result.concerns
    assert result.is_clear


def test_a_shut_wellhead_and_a_dead_one_are_both_concerns() -> None:
    shut = read(a_reading(valve_after=0.0))
    assert Concern.SHUT in shut.concerns
    dead = read(a_reading(methane=0.0, carbon=0.0, oxygen=20.9, balance=79.1))
    assert Concern.DEAD in dead.concerns
    assert Concern.RICH_AIR in dead.concerns


def test_gas_in_the_head_and_nothing_coming_out_is_a_concern() -> None:
    result = read(a_reading(flow=0.0))
    assert Concern.NO_FLOW in result.concerns


def test_a_shut_wellhead_is_not_also_a_no_flow_concern() -> None:
    result = read(a_reading(valve_after=0.0, flow=0.0))
    assert Concern.SHUT in result.concerns
    assert Concern.NO_FLOW not in result.concerns


def test_a_concern_prints_the_sentence_the_desk_reads() -> None:
    assert str(Concern.UNBALANCED) == "the four gas figures do not add up"


def test_the_assessment_carries_the_wellhead_and_the_day() -> None:
    result = read(a_reading())
    assert result.device == "VW-041"
    assert result.taken_on == TAKEN

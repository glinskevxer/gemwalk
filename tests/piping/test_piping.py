"""Headers, laterals, and what a device hangs off."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import OrderError, RuleError
from gemwalk.model.piping import Header, Lateral

INSTALLED = dt.date(2019, 9, 3)


def a_header(**changes: object) -> Header:
    fields: dict[str, object] = {
        "label": "HD-01",
        "site": "NORTHRIDGE",
        "name": "north trunk",
        "diameter": 18.0,
        "material": "HDPE SDR17",
        "length_feet": 2_140.0,
        "installed_on": INSTALLED,
    }
    fields.update(changes)
    return Header(**fields)  # type: ignore[arg-type]


def a_lateral(**changes: object) -> Lateral:
    fields: dict[str, object] = {
        "label": "LT-004",
        "site": "NORTHRIDGE",
        "header": "HD-01",
        "diameter": 8.0,
        "material": "HDPE SDR17",
        "length_feet": 460.0,
        "installed_on": INSTALLED,
    }
    fields.update(changes)
    return Lateral(**fields)  # type: ignore[arg-type]


def test_pipe_has_a_diameter_and_a_length() -> None:
    with pytest.raises(RuleError):
        a_header(diameter=0.0)
    with pytest.raises(RuleError):
        a_lateral(length_feet=0.0)


def test_a_material_the_site_does_not_stock_is_refused() -> None:
    with pytest.raises(RuleError, match="not a pipe"):
        a_header(material="cast iron")


def test_pipe_cannot_come_out_before_it_went_in() -> None:
    with pytest.raises(OrderError):
        a_header(retired_on=dt.date(2018, 1, 1))
    with pytest.raises(OrderError):
        a_lateral(retired_on=dt.date(2018, 1, 1))


def test_pipe_is_in_service_between_the_two_dates() -> None:
    header = a_header(retired_on=dt.date(2024, 6, 1))
    assert not header.in_service_on(dt.date(2019, 9, 2))
    assert header.in_service_on(dt.date(2024, 6, 1))
    assert not header.in_service_on(dt.date(2024, 6, 2))


def test_live_pipe_has_no_end_date() -> None:
    assert a_header().in_service_on(dt.date(2030, 1, 1))
    assert a_lateral().in_service_on(dt.date(2030, 1, 1))


def test_retiring_pipe_twice_is_refused() -> None:
    header = a_header().retire(dt.date(2024, 6, 1))
    assert not header.is_live
    with pytest.raises(RuleError):
        header.retire(dt.date(2024, 7, 1))
    lateral = a_lateral().retire(dt.date(2024, 6, 1))
    with pytest.raises(RuleError):
        lateral.retire(dt.date(2024, 7, 1))


def test_a_lateral_cannot_be_bigger_than_the_header_it_ties_into() -> None:
    assert a_lateral().fits(a_header())
    assert not a_lateral(diameter=24.0).fits(a_header())


def test_a_lateral_the_same_size_as_its_header_still_fits() -> None:
    assert a_lateral(diameter=18.0).fits(a_header())

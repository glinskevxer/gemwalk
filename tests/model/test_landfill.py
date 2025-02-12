"""The site, the areas, and the deadline an area carries."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import OrderError, RuleError
from gemwalk.model.landfill import Area, Cover, Site, read_optional_day
from gemwalk.rules import WWW, XXX


def a_site(**changes: object) -> Site:
    fields: dict[str, object] = {
        "label": "NORTHRIDGE",
        "name": "Northridge Sanitary Landfill",
        "standard": "XXX",
        "permit": "MSW-1188-04",
        "zone": "America/Chicago",
        "design_capacity": 8_400_000.0,
        "opened_on": dt.date(1998, 6, 1),
    }
    fields.update(changes)
    return Site(**fields)  # type: ignore[arg-type]


def an_area(**changes: object) -> Area:
    fields: dict[str, object] = {
        "label": "A-03",
        "site": "NORTHRIDGE",
        "name": "phase 3 north slope",
        "acres": 12.4,
        "first_waste": dt.date(2019, 4, 15),
    }
    fields.update(changes)
    return Area(**fields)  # type: ignore[arg-type]


def test_a_site_needs_a_label_and_a_real_capacity() -> None:
    with pytest.raises(RuleError):
        a_site(label="  ")
    with pytest.raises(RuleError):
        a_site(design_capacity=0.0)


def test_a_site_cannot_close_before_it_opened() -> None:
    with pytest.raises(OrderError):
        a_site(closed_on=dt.date(1997, 1, 1))


def test_a_site_knows_whether_it_was_taking_waste_on_a_day() -> None:
    site = a_site(closed_on=dt.date(2024, 12, 31))
    assert site.is_open_on(dt.date(2024, 12, 31))
    assert not site.is_open_on(dt.date(2025, 1, 1))
    assert not site.is_open_on(dt.date(1998, 5, 31))


def test_closing_a_shut_site_is_refused() -> None:
    site = a_site().close(dt.date(2024, 12, 31))
    assert site.is_closed
    with pytest.raises(RuleError):
        site.close(dt.date(2025, 1, 2))


def test_design_capacity_is_measured_against_the_standard() -> None:
    assert a_site().over_design_capacity(XXX)
    assert not a_site(design_capacity=900_000.0).over_design_capacity(XXX)


def test_a_filling_area_gets_five_years_from_the_first_load() -> None:
    assert an_area().install_due(XXX) == dt.date(2024, 4, 15)


def test_a_closed_area_gets_two_years_from_the_last_load() -> None:
    area = an_area().stop_filling(dt.date(2021, 8, 3)).close(dt.date(2021, 11, 20))
    assert area.install_due(XXX) == dt.date(2023, 8, 3)


def test_closing_an_area_can_pull_the_deadline_earlier_than_its_neighbour() -> None:
    filling = an_area()
    closed = an_area(label="A-04", first_waste=dt.date(2020, 1, 6))
    closed = closed.stop_filling(dt.date(2020, 9, 1)).close(dt.date(2020, 12, 1))
    assert closed.install_due(WWW) < filling.install_due(WWW)


def test_the_deadline_off_a_leap_day_lands_on_the_day_before() -> None:
    area = an_area(first_waste=dt.date(2020, 2, 29))
    assert area.install_due(XXX) == dt.date(2025, 2, 28)


def test_an_area_covers_some_ground() -> None:
    with pytest.raises(RuleError):
        an_area(acres=0.0)


def test_an_area_cannot_close_while_it_is_still_filling() -> None:
    with pytest.raises(RuleError):
        an_area().close(dt.date(2021, 11, 20))


def test_an_area_cannot_take_its_last_load_before_its_first() -> None:
    with pytest.raises(OrderError):
        an_area(last_waste=dt.date(2018, 1, 1))


def test_an_area_cannot_be_closed_before_its_last_load() -> None:
    with pytest.raises(OrderError):
        an_area(last_waste=dt.date(2021, 8, 3), closed_on=dt.date(2021, 1, 1))


def test_an_area_cannot_stop_filling_twice() -> None:
    area = an_area().stop_filling(dt.date(2021, 8, 3))
    with pytest.raises(RuleError):
        area.stop_filling(dt.date(2021, 9, 3))


def test_an_area_cannot_close_twice() -> None:
    area = an_area().stop_filling(dt.date(2021, 8, 3)).close(dt.date(2021, 11, 20))
    assert area.cover is Cover.FINAL
    with pytest.raises(RuleError):
        area.close(dt.date(2022, 1, 4))


def test_a_blank_sheet_cell_is_no_date() -> None:
    assert read_optional_day(None) is None
    assert read_optional_day("   ") is None
    assert read_optional_day("2021-08-03") == dt.date(2021, 8, 3)


def test_a_cover_prints_as_the_word_the_sheet_uses() -> None:
    assert str(Cover.INTERMEDIATE) == "intermediate"

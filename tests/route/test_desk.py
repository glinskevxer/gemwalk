"""The pattern through the surface desk."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Quarter
from gemwalk.errors import RuleError, StateError
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, furnish

MAY = dt.date(2025, 5, 13)


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def a_walk(office: Office, on: dt.date = MAY) -> str:
    return office.surface.open_walk(
        SITE,
        on,
        monitor="T. Wierzbicki",
        instrument="TVA1000B-8841",
        background=2.0,
        wind_mean=3.4,
        wind_gust=7.1,
    ).label


def test_a_pattern_is_laid_with_numbered_legs(office: Office) -> None:
    made = office.surface.lay_pattern("A-03", legs=3, metres=400.0)
    assert [leg.label for leg in made] == ["A-03-L01", "A-03-L02", "A-03-L03"]
    assert made[0].metres == pytest.approx(400.0)


def test_laying_more_legs_carries_on_the_numbering(office: Office) -> None:
    office.surface.lay_pattern("A-03", legs=2, metres=400.0)
    more = office.surface.lay_pattern("A-03", legs=1, metres=400.0)
    assert [leg.label for leg in more] == ["A-03-L03"]


def test_the_desk_says_how_many_legs_an_area_wants(office: Office) -> None:
    assert office.surface.wanted_legs("A-03", 400.0) == 5
    assert office.surface.wanted_legs("A-04", 400.0) < 5


def test_an_area_with_no_pattern_is_not_incomplete(office: Office) -> None:
    walk = a_walk(office)
    assert office.surface.incomplete(walk) == []
    assert office.surface.covered_whole(walk)


def test_a_walk_that_crossed_nothing_missed_everything(office: Office) -> None:
    office.surface.lay_pattern("A-03", legs=2, metres=400.0)
    walk = a_walk(office)
    short = office.surface.incomplete(walk)
    assert [route.area for route in short] == ["A-03"]
    assert short[0].missed == ("A-03-L01", "A-03-L02")


def test_a_walk_that_crossed_every_leg_is_whole(office: Office) -> None:
    legs = office.surface.lay_pattern("A-03", legs=2, metres=400.0)
    walk = a_walk(office)
    for leg in legs:
        office.surface.cross(walk, leg.label)
    assert office.surface.covered_whole(walk)
    assert office.surface.route_of(walk, "A-03").share == pytest.approx(1.0)


def test_a_leg_cannot_be_crossed_on_a_finished_walk(office: Office) -> None:
    legs = office.surface.lay_pattern("A-03", legs=1, metres=400.0)
    walk = a_walk(office)
    office.surface.finish_walk(walk, MAY)
    with pytest.raises(StateError):
        office.surface.cross(walk, legs[0].label)


def test_a_leg_of_another_site_is_refused(office: Office) -> None:
    office.sites.open_site(
        "SOUTHFORK",
        "Southfork",
        subpart="WWW",
        permit="MSW-2",
        zone="America/Chicago",
        design_capacity=3_100_000.0,
        opened_on=dt.date(1994, 2, 1),
    )
    office.sites.add_area(
        "B-01", "SOUTHFORK", "cell one", acres=6.0, first_waste=dt.date(1994, 3, 1)
    )
    other = office.surface.lay_pattern("B-01", legs=1, metres=400.0)[0]
    walk = a_walk(office)
    with pytest.raises(RuleError, match="not a leg at"):
        office.surface.cross(walk, other.label)


def test_a_retired_leg_is_not_missed(office: Office) -> None:
    legs = office.surface.lay_pattern("A-03", legs=2, metres=400.0)
    office.surface.legs.put(legs[1].retire(dt.date(2025, 5, 1)))
    walk = a_walk(office)
    office.surface.cross(walk, legs[0].label)
    assert office.surface.covered_whole(walk)


def test_the_ground_crossed_is_counted_in_acres(office: Office) -> None:
    legs = office.surface.lay_pattern("A-03", legs=5, metres=400.0)
    walk = a_walk(office)
    for leg in legs:
        office.surface.cross(walk, leg.label)
    route = office.surface.route_of(walk, "A-03")
    assert route.enough_for(office.sites.standard_of(SITE))


def test_a_quarter_walked_short_does_not_count_as_walked(office: Office) -> None:
    office.surface.lay_pattern("A-03", legs=2, metres=400.0)
    walk = a_walk(office)
    office.surface.finish_walk(walk, MAY)
    missed = office.surface.quarters_missed(SITE, Quarter(2025, 2), Quarter(2025, 2))
    assert [str(q) for q in missed] == ["2025Q2"]


def test_a_quarter_walked_whole_counts(office: Office) -> None:
    legs = office.surface.lay_pattern("A-03", legs=2, metres=400.0)
    walk = a_walk(office)
    for leg in legs:
        office.surface.cross(walk, leg.label)
    office.surface.finish_walk(walk, MAY)
    assert office.surface.quarters_missed(SITE, Quarter(2025, 2), Quarter(2025, 2)) == []


def test_every_area_is_read_for_one_walk(office: Office) -> None:
    office.surface.lay_pattern("A-03", legs=1, metres=400.0)
    office.surface.lay_pattern("A-04", legs=1, metres=400.0)
    walk = a_walk(office)
    assert [route.area for route in office.surface.routes_of(walk)] == ["A-03", "A-04"]


def test_the_compliance_report_names_the_legs_a_walk_missed(office: Office) -> None:
    from gemwalk.report.compliance import compliance_report

    office.surface.lay_pattern("A-03", legs=2, metres=400.0)
    walk = a_walk(office)
    office.surface.cross(walk, "A-03-L01")
    office.surface.finish_walk(walk, MAY)
    section = compliance_report(office, SITE, Quarter(2025, 2)).find("surface monitoring")
    assert section is not None
    body = "\n".join(section.lines())
    assert "missed A-03-L02" in body
    assert "acres in A-03" in body


def test_a_whole_walk_says_nothing_about_missed_legs(office: Office) -> None:
    from gemwalk.report.compliance import compliance_report

    legs = office.surface.lay_pattern("A-03", legs=5, metres=400.0)
    walk = a_walk(office)
    for leg in legs:
        office.surface.cross(walk, leg.label)
    office.surface.finish_walk(walk, MAY)
    section = compliance_report(office, SITE, Quarter(2025, 2)).find("surface monitoring")
    assert section is not None
    assert not any("missed" in line for line in section.body)

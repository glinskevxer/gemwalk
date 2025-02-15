"""Opening a site, cutting areas into it, and closing both."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import DuplicateError, RuleError, UnknownError
from gemwalk.model.landfill import Cover
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book


@pytest.fixture
def desk(book: Book) -> SiteDesk:
    made = SiteDesk(book)
    made.open_site(
        "NORTHRIDGE",
        "Northridge Sanitary Landfill",
        subpart="XXX",
        permit="MSW-1188-04",
        zone="America/Chicago",
        design_capacity=8_400_000.0,
        opened_on=dt.date(1998, 6, 1),
    )
    return made


def test_a_site_is_read_back_the_way_it_went_in(desk: SiteDesk) -> None:
    site = desk.sites.get("NORTHRIDGE")
    assert site.permit == "MSW-1188-04"
    assert site.design_capacity == pytest.approx(8_400_000.0)
    assert site.opened_on == dt.date(1998, 6, 1)
    assert site.closed_on is None


def test_a_site_carries_its_standard_and_its_wall_clock(desk: SiteDesk) -> None:
    assert desk.standard_of("NORTHRIDGE").code == "XXX"
    assert desk.zone_of("NORTHRIDGE") == "America/Chicago"


def test_a_subpart_nobody_writes_is_refused(desk: SiteDesk) -> None:
    with pytest.raises(UnknownError):
        desk.open_site(
            "SOUTHFORK",
            "Southfork",
            subpart="QQQ",
            permit="MSW-2",
            zone="America/Chicago",
            design_capacity=1.0,
            opened_on=dt.date(2001, 1, 1),
        )


def test_the_same_site_cannot_be_opened_twice(desk: SiteDesk) -> None:
    with pytest.raises(DuplicateError):
        desk.open_site(
            "NORTHRIDGE",
            "again",
            subpart="XXX",
            permit="MSW-1188-04",
            zone="America/Chicago",
            design_capacity=8_400_000.0,
            opened_on=dt.date(1998, 6, 1),
        )


def test_an_area_cannot_predate_the_site_it_sits_in(desk: SiteDesk) -> None:
    with pytest.raises(RuleError):
        desk.add_area("A-01", "NORTHRIDGE", "phase 1", acres=9.0, first_waste=dt.date(1997, 1, 1))


def test_an_area_of_a_site_that_is_not_there_is_refused(desk: SiteDesk) -> None:
    with pytest.raises(UnknownError):
        desk.add_area("A-01", "SOUTHFORK", "phase 1", acres=9.0, first_waste=dt.date(2001, 1, 1))


def test_the_areas_of_a_site_come_back_in_label_order(desk: SiteDesk) -> None:
    desk.add_area("A-02", "NORTHRIDGE", "phase 2", acres=11.0, first_waste=dt.date(2012, 3, 1))
    desk.add_area("A-01", "NORTHRIDGE", "phase 1", acres=9.0, first_waste=dt.date(2004, 5, 1))
    assert [a.label for a in desk.areas_of("NORTHRIDGE")] == ["A-01", "A-02"]


def test_the_deadline_of_an_area_uses_the_site_standard(desk: SiteDesk) -> None:
    desk.add_area("A-03", "NORTHRIDGE", "phase 3", acres=12.4, first_waste=dt.date(2019, 4, 15))
    assert desk.install_due("A-03") == dt.date(2024, 4, 15)


def test_closing_an_area_moves_its_deadline(desk: SiteDesk) -> None:
    desk.add_area("A-03", "NORTHRIDGE", "phase 3", acres=12.4, first_waste=dt.date(2019, 4, 15))
    desk.stop_filling("A-03", dt.date(2021, 8, 3))
    desk.close_area("A-03", dt.date(2021, 11, 20))
    assert desk.areas.get("A-03").cover is Cover.FINAL
    assert desk.install_due("A-03") == dt.date(2023, 8, 3)


def test_an_area_past_its_deadline_is_listed(desk: SiteDesk) -> None:
    desk.add_area("A-03", "NORTHRIDGE", "phase 3", acres=12.4, first_waste=dt.date(2019, 4, 15))
    desk.add_area("A-04", "NORTHRIDGE", "phase 4", acres=8.0, first_waste=dt.date(2023, 6, 1))
    overdue = desk.overdue_areas("NORTHRIDGE", dt.date(2025, 1, 1))
    assert [a.label for a in overdue] == ["A-03"]


def test_a_site_with_an_area_still_filling_cannot_close(desk: SiteDesk) -> None:
    desk.add_area("A-04", "NORTHRIDGE", "phase 4", acres=8.0, first_waste=dt.date(2023, 6, 1))
    with pytest.raises(RuleError, match="A-04"):
        desk.close_site("NORTHRIDGE", dt.date(2025, 12, 31))


def test_a_site_closes_once_every_area_has_stopped(desk: SiteDesk) -> None:
    desk.add_area("A-04", "NORTHRIDGE", "phase 4", acres=8.0, first_waste=dt.date(2023, 6, 1))
    desk.stop_filling("A-04", dt.date(2025, 10, 1))
    closed = desk.close_site("NORTHRIDGE", dt.date(2025, 12, 31))
    assert closed.closed_on == dt.date(2025, 12, 31)


def test_a_closed_site_stays_readable(desk: SiteDesk) -> None:
    desk.close_site("NORTHRIDGE", dt.date(2025, 12, 31))
    assert desk.sites.get("NORTHRIDGE").is_closed

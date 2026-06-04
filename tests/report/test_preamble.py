"""The heading every report starts with."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.clock import Month, Quarter, read_moment
from gemwalk.errors import UnknownError
from gemwalk.report.annual import annual_report
from gemwalk.report.compliance import compliance_report
from gemwalk.report.monthly import monthly_report
from gemwalk.report.plant import plant_report
from gemwalk.report.preamble import headed
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, ZONE, furnish


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def test_the_heading_names_the_site_the_kind_and_the_period(office: Office) -> None:
    report, subpart = headed(office, SITE, "probe report", "2025Q2")
    assert report.title == "Northridge Sanitary Landfill probe report"
    assert report.subtitle == "2025Q2 under 40 CFR 60 subpart XXX, permit MSW-1188-04"
    assert subpart.code == "XXX"


def test_a_site_the_book_never_issued_is_refused(office: Office) -> None:
    with pytest.raises(UnknownError):
        headed(office, "SOUTHFORK", "probe report", "2025Q2")


def test_every_report_uses_the_same_wording(office: Office) -> None:
    reports = [
        monthly_report(office, SITE, Month(2025, 4)),
        compliance_report(office, SITE, Quarter(2025, 2)),
        annual_report(office, SITE, 2025),
        plant_report(
            office,
            SITE,
            read_moment("2025-06-11 00:00", ZONE),
            read_moment("2025-06-12 00:00", ZONE),
        ),
    ]
    for report in reports:
        assert report.title.startswith("Northridge Sanitary Landfill ")
        assert "under 40 CFR 60 subpart XXX, permit MSW-1188-04" in report.subtitle


def test_each_report_says_which_period_it_covers(office: Office) -> None:
    assert monthly_report(office, SITE, Month(2025, 4)).subtitle.startswith("2025-04")
    assert compliance_report(office, SITE, Quarter(2025, 2)).subtitle.startswith("2025Q2")
    assert annual_report(office, SITE, 2025).subtitle.startswith("2025")


def test_the_plant_report_says_the_moments_and_the_clock(office: Office) -> None:
    report = plant_report(
        office,
        SITE,
        read_moment("2025-06-11 00:00", ZONE),
        read_moment("2025-06-12 00:00", ZONE),
    )
    assert "2025-06-11 00:00 to 2025-06-12 00:00" in report.subtitle
    assert ZONE in report.subtitle


def test_the_well_card_heads_itself_differently_on_purpose(office: Office) -> None:
    from gemwalk.report.device import device_report

    report = device_report(office, "VW-001", on=dt.date(2025, 4, 30))
    assert report.title == "VW-001 well card"
    assert "permit" not in report.subtitle

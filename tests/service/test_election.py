"""What a site elects, and when the election starts counting."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import OrderError, RuleError
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book

OPENED = dt.date(1998, 6, 1)
ELECTED = dt.date(2025, 3, 1)


@pytest.fixture
def desk(book: Book) -> SiteDesk:
    made = SiteDesk(book)
    for label, subpart in (("NORTHRIDGE", "XXX"), ("SOUTHFORK", "WWW")):
        made.open_site(
            label,
            label.title(),
            subpart=subpart,
            permit=f"MSW-{label}",
            zone="America/Chicago",
            design_capacity=8_400_000.0,
            opened_on=OPENED,
        )
    return made


def test_a_site_that_has_elected_nothing_reads_back_as_nothing(desk: SiteDesk) -> None:
    election = desk.election_of("NORTHRIDGE")
    assert not election.nitrogen_alternative
    assert not election.higher_pressure


def test_a_site_can_elect_the_nitrogen_alternative(desk: SiteDesk) -> None:
    desk.elect("NORTHRIDGE", ELECTED, nitrogen_alternative=True)
    assert desk.election_of("NORTHRIDGE").nitrogen_alternative


def test_an_election_counts_from_the_day_it_was_made(desk: SiteDesk) -> None:
    desk.elect("NORTHRIDGE", ELECTED, nitrogen_alternative=True)
    assert not desk.election_of("NORTHRIDGE", dt.date(2025, 2, 1)).nitrogen_alternative
    assert desk.election_of("NORTHRIDGE", ELECTED).nitrogen_alternative


def test_a_standard_with_no_alternative_refuses_the_election(desk: SiteDesk) -> None:
    with pytest.raises(RuleError, match="nitrogen alternative"):
        desk.elect("SOUTHFORK", ELECTED, nitrogen_alternative=True)
    with pytest.raises(RuleError, match="pressure alternative"):
        desk.elect("SOUTHFORK", ELECTED, higher_pressure=True)


def test_an_election_cannot_predate_the_site(desk: SiteDesk) -> None:
    with pytest.raises(OrderError):
        desk.elect("NORTHRIDGE", dt.date(1990, 1, 1), nitrogen_alternative=True)


def test_electing_again_replaces_what_was_there(desk: SiteDesk) -> None:
    desk.elect("NORTHRIDGE", ELECTED, nitrogen_alternative=True, higher_pressure=True)
    desk.elect("NORTHRIDGE", dt.date(2026, 1, 5), nitrogen_alternative=True)
    election = desk.election_of("NORTHRIDGE", dt.date(2026, 2, 1))
    assert election.nitrogen_alternative
    assert not election.higher_pressure


def test_an_election_survives_the_book(desk: SiteDesk) -> None:
    desk.elect("NORTHRIDGE", ELECTED, higher_pressure=True)
    site = desk.sites.get("NORTHRIDGE")
    assert site.higher_pressure
    assert site.elected_on == ELECTED

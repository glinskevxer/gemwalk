"""The site group."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.support import Shell, open_site, shell


@pytest.fixture
def cli(tmp_path: Path) -> Shell:
    return shell(tmp_path)


def test_opening_a_site_says_which_standard_it_landed_under(cli: Shell) -> None:
    open_site(cli)
    assert "subpart XXX" in cli.ok("site", "show", "NORTHRIDGE")


def test_a_subpart_nobody_writes_is_refused_by_click(cli: Shell) -> None:
    out = cli.fails(
        "site",
        "open",
        "X",
        "X",
        "--subpart",
        "QQQ",
        "--permit",
        "p",
        "--zone",
        "UTC",
        "--capacity",
        "1",
        "--opened",
        "2000-01-01",
    )
    assert "QQQ" in out


def test_a_date_that_is_not_a_date_says_how_to_write_one(cli: Shell) -> None:
    out = cli.fails(
        "site",
        "open",
        "X",
        "X",
        "--subpart",
        "XXX",
        "--permit",
        "p",
        "--zone",
        "UTC",
        "--capacity",
        "1",
        "--opened",
        "last thursday",
    )
    assert "2025-04-08" in out


def test_the_site_list_carries_the_permit(cli: Shell) -> None:
    open_site(cli)
    out = cli.ok("site", "list")
    assert "NORTHRIDGE" in out
    assert "MSW-1188-04" in out
    assert "open" in out


def test_show_prints_the_citation_and_the_clock(cli: Shell) -> None:
    open_site(cli)
    out = cli.ok("site", "show", "NORTHRIDGE")
    assert "40 CFR 60 subpart XXX" in out
    assert "America/Chicago" in out
    assert "nitrogen alternative: no" in out


def test_electing_shows_up_on_the_site(cli: Shell) -> None:
    open_site(cli)
    cli.ok("site", "elect", "NORTHRIDGE", "--on", "2025-03-01", "--nitrogen")
    assert "nitrogen alternative: yes" in cli.ok("site", "show", "NORTHRIDGE")


def test_an_election_a_standard_does_not_offer_is_refused(cli: Shell) -> None:
    open_site(cli, "SOUTHFORK", "WWW")
    out = cli.fails("site", "elect", "SOUTHFORK", "--on", "2025-03-01", "--nitrogen")
    assert "nitrogen alternative" in out


def test_an_election_reads_as_of_a_day(cli: Shell) -> None:
    open_site(cli)
    cli.ok("site", "elect", "NORTHRIDGE", "--on", "2025-03-01", "--nitrogen")
    assert "nitrogen alternative: no" in cli.ok("site", "show", "NORTHRIDGE", "--on", "2025-01-01")


def test_adding_an_area_says_when_collection_is_due(cli: Shell) -> None:
    open_site(cli)
    out = cli.ok(
        "site",
        "area",
        "A-09",
        "NORTHRIDGE",
        "phase 9",
        "--acres",
        "4",
        "--first-waste",
        "2022-05-01",
    )
    assert "2027-05-01" in out


def test_an_area_of_a_site_that_is_not_there_is_refused(cli: Shell) -> None:
    out = cli.fails(
        "site",
        "area",
        "A-09",
        "SOUTHFORK",
        "phase 9",
        "--acres",
        "4",
        "--first-waste",
        "2022-05-01",
    )
    assert "SOUTHFORK" in out


def test_the_area_list_flags_the_overdue_ones(cli: Shell) -> None:
    open_site(cli)
    out = cli.ok("site", "areas", "NORTHRIDGE", "--on", "2025-04-30")
    assert "A-03" in out
    assert "overdue" in out


def test_closing_an_area_pulls_its_deadline_in(cli: Shell) -> None:
    open_site(cli)
    cli.ok("site", "stop", "A-03", "--on", "2021-08-03")
    out = cli.ok("site", "cap", "A-03", "--on", "2021-11-20")
    assert "2023-08-03" in out
    assert "final" in out


def test_an_area_still_filling_cannot_be_capped(cli: Shell) -> None:
    open_site(cli)
    assert "still taking waste" in cli.fails("site", "cap", "A-03", "--on", "2021-11-20")


def test_a_site_with_an_area_still_filling_cannot_close(cli: Shell) -> None:
    open_site(cli)
    assert "A-03" in cli.fails("site", "close", "NORTHRIDGE", "--on", "2025-12-31")


def test_a_site_closes_once_every_area_has_stopped(cli: Shell) -> None:
    open_site(cli)
    cli.ok("site", "stop", "A-03", "--on", "2021-08-03")
    cli.ok("site", "stop", "A-04", "--on", "2024-10-01")
    assert "closed on 2025-12-31" in cli.ok("site", "close", "NORTHRIDGE", "--on", "2025-12-31")

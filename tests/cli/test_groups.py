"""Every command group is reachable, described, and made of named commands.

The suites next to this one drive the groups through the top level command.
This one names each module on its own, so a group that stops being registered
is a failure here rather than a quiet absence everywhere else.
"""

from __future__ import annotations

import click
import pytest

from gemwalk.cli import (
    cover,
    instrument,
    landfill,
    monitoring,
    plant,
    records,
    report,
    support,
    wellfield,
)
from gemwalk.cli import main as main_module

GROUPS: dict[str, click.Group] = {
    "site": landfill.site,
    "well": wellfield.well,
    "pipe": wellfield.pipe,
    "run": monitoring.run,
    "record": records.record,
    "work": records.work,
    "cover": cover.cover,
    "plant": plant.plant,
    "water": plant.water,
    "report": report.report,
    "meter": instrument.meter,
}


def test_every_group_is_registered_on_the_top_level_command() -> None:
    top = main_module.main
    assert isinstance(top, click.Group)
    registered = set(top.commands)
    assert set(GROUPS) <= registered
    assert "store" in registered
    assert "about" in registered


@pytest.mark.parametrize("name", sorted(GROUPS))
def test_every_group_says_what_it_is_for(name: str) -> None:
    group = GROUPS[name]
    assert group.help
    assert group.commands


@pytest.mark.parametrize("name", sorted(GROUPS))
def test_every_command_in_every_group_says_what_it_does(name: str) -> None:
    for command in GROUPS[name].commands.values():
        assert command.help, f"{name} {command.name} has no help"


@pytest.mark.parametrize("name", sorted(GROUPS))
def test_every_option_in_every_group_says_what_it_is(name: str) -> None:
    for command in GROUPS[name].commands.values():
        for parameter in command.params:
            if isinstance(parameter, click.Option) and parameter.name != "help":
                assert parameter.help, f"{name} {command.name} {parameter.name} has no help"


def test_the_top_level_command_turns_refusals_into_messages() -> None:
    assert isinstance(main_module.main, support.DeskGroup)


def test_the_date_reader_takes_a_field_sheet_date() -> None:
    import datetime as dt

    assert support.DAY.convert("2025-04-08", None, None) == dt.date(2025, 4, 8)


def test_the_date_reader_hands_a_date_straight_back() -> None:
    import datetime as dt

    day = dt.date(2025, 4, 8)
    assert support.DAY.convert(day, None, None) is day

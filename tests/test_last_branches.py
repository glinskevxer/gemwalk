"""The last handful of branches, and the note that the whole thing is finished.

Everything here is a line the suite reached round the outside of rather than
through. None of them is interesting on its own. Together they are the
difference between a package where every branch has been executed once and a
package where a few of them have only ever been read.
"""

from __future__ import annotations

import ast
import datetime as dt
from typing import Any

import click
import pytest

from gemwalk.clock import Month, Quarter
from gemwalk.errors import RuleError, UnitError, UnknownError
from gemwalk.model.device import Device, Kind
from gemwalk.model.rework import Job as ReworkJob
from gemwalk.model.rework import Rework
from gemwalk.model.work import Job, Standing, WorkOrder
from gemwalk.rules import WWW, XXX
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from gemwalk.store.repo import Repository
from gemwalk.tools import check_cli, check_design, check_errors, check_handbook
from gemwalk.tools.walker import Module, package_root
from gemwalk.units import Temperature
from tests.support import SITE, furnish

APRIL = dt.date(2025, 4, 8)


def a_module(source: str, name: str = "gemwalk.model.probe") -> Module:
    return Module(package_root() / "model" / "probe.py", name, ast.parse(source), source)


def test_a_dataclass_written_with_a_dotted_name_is_still_a_dataclass() -> None:
    source = (
        '"""m."""\n\nimport dataclasses\n\n\n'
        '@dataclasses.dataclass(frozen=True)\nclass A:\n    """a."""\n\n    x: int\n'
    )
    made, frozen = check_design.is_dataclass(ast.parse(source).body[-1])  # type: ignore[arg-type]
    assert made
    assert frozen


def test_a_dataclass_with_a_keyword_that_is_not_frozen_reads_as_unfrozen() -> None:
    source = (
        '"""m."""\n\nfrom dataclasses import dataclass\n\n\n'
        '@dataclass(order=True)\nclass A:\n    """a."""\n\n    x: int\n'
    )
    faults = check_design.faults_in(a_module(source))
    assert any("is not frozen" in fault for fault in faults)


def test_a_decorator_that_is_not_a_dataclass_is_left_alone() -> None:
    source = (
        '"""m."""\n\nimport functools\n\n\n'
        '@functools.cache\ndef go() -> int:\n    """g."""\n    return 1\n'
    )
    assert check_design.faults_in(a_module(source)) == []


def test_a_command_and_an_option_with_no_help_are_both_found() -> None:
    group = click.Group("probe", help="A group.")

    @group.command("go")
    @click.option("--quietly", is_flag=True)
    def go(quietly: bool) -> None:
        pass

    faults = [
        fault
        for path, command in check_cli.commands(group)
        for fault in ([f"{path} says nothing about what it does"] if not command.help else [])
    ]
    assert faults == ["go says nothing about what it does"]


def test_a_raise_of_an_attribute_is_read_by_its_last_name() -> None:
    source = (
        '"""m."""\n\nimport errno\n\n\ndef go() -> None:\n    """g."""\n'
        "    raise errno.ValueError\n"
    )
    faults = check_errors.faults_in(a_module(source, "gemwalk.service.probe"))
    assert any("raises ValueError" in fault for fault in faults)


def test_a_raise_of_something_that_is_not_a_name_is_left_alone() -> None:
    source = (
        '"""m."""\n\n\ndef go(kinds: dict[str, type[Exception]]) -> None:\n'
        '    """g."""\n    raise kinds["x"]("no")\n'
    )
    assert check_errors.faults_in(a_module(source, "gemwalk.service.probe")) == []


def test_a_handbook_that_is_not_there_names_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    monkeypatch.setattr(check_handbook, "repo_root", lambda: tmp_path)
    assert check_handbook.named() == []


def test_a_repository_with_no_writer_says_so(book: Book) -> None:
    class Bare(Repository[Any]):
        table = "site"
        kind = "site"
        columns = ("label",)

    with pytest.raises(NotImplementedError):
        Bare(book).write(object())
    with pytest.raises(NotImplementedError):
        Bare(book).with_key(object(), 1)


def test_an_integrity_error_that_is_not_a_duplicate_comes_straight_back(
    book: Book,
) -> None:
    import sqlite3

    from gemwalk.store.devices import DeviceRepository

    furnish(Office(book))
    devices = DeviceRepository(book)
    orphan = Device(
        label="VW-999",
        site="NOWHERE",
        area="A-03",
        kind=Kind.VERTICAL,
        station="x",
        total_depth=90.0,
        screen_top=20.0,
        screen_bottom=84.0,
        drilled_on=APRIL,
    )
    with pytest.raises(sqlite3.IntegrityError):
        devices.add(orphan)


def test_the_first_quarter_and_the_first_month_step_back_a_year() -> None:
    assert Quarter(2025, 1).previous == Quarter(2024, 4)
    assert Month(2025, 1).previous == Month(2024, 12)


def test_a_month_label_with_words_in_it_is_refused() -> None:
    with pytest.raises(UnitError, match="a month"):
        Month.parse("2025-ab")


def test_a_device_has_to_pull_on_some_ground() -> None:
    with pytest.raises(RuleError, match="some ground"):
        Device(
            label="VW-001",
            site=SITE,
            area="A-03",
            kind=Kind.VERTICAL,
            station="x",
            total_depth=90.0,
            screen_top=20.0,
            screen_bottom=84.0,
            drilled_on=APRIL,
            influence=0.0,
        )


def test_a_device_knows_whether_it_is_piped(book: Book) -> None:
    office = furnish(Office(book))
    assert office.wellfield.devices.get("VW-001").is_piped
    made = office.wellfield.drill(
        SITE,
        "A-03",
        station="x",
        total_depth=90.0,
        screen_top=20.0,
        screen_bottom=84.0,
        on=APRIL,
    )
    assert not made.is_piped


def test_a_standard_with_no_higher_value_ignores_an_approval() -> None:
    device = Device(
        label="VW-001",
        site=SITE,
        area="A-03",
        kind=Kind.VERTICAL,
        station="x",
        total_depth=90.0,
        screen_top=20.0,
        screen_bottom=84.0,
        drilled_on=APRIL,
    ).approve_higher_temperature(Temperature(145.0), APRIL)
    assert device.temperature_limit(XXX, APRIL) == Temperature(145.0)
    assert WWW.allows_higher_temperature


def test_a_rework_job_finished_before_it_started_is_refused() -> None:
    with pytest.raises(Exception, match="is not before"):
        ReworkJob(
            label="RW-1",
            device="VW-001",
            site=SITE,
            kind=Rework.REPAIR,
            started_on=APRIL,
            finished_on=dt.date(2025, 4, 1),
            before_depth=92.0,
            before_top=22.0,
            before_bottom=86.0,
        )


def test_a_closed_order_is_not_on_the_board(book: Book) -> None:
    office = furnish(Office(book))
    order = office.work.raise_order(
        SITE, Job.VALVE, "VW-001", on=APRIL, due=dt.date(2025, 4, 13)
    ).label
    office.work.finish(order, dt.date(2025, 4, 10))
    assert office.work.board(SITE, dt.date(2025, 4, 11)) == []
    assert (
        WorkOrder(
            label="WO-1",
            site=SITE,
            job=Job.VALVE,
            target="VW-001",
            raised_on=APRIL,
            due_on=dt.date(2025, 4, 13),
            state=Standing.DONE,
            done_on=dt.date(2025, 4, 10),
        ).days_left(APRIL)
        is None
    )


def test_an_order_off_a_record_with_no_window_left_is_refused(book: Book) -> None:
    office = furnish(Office(book))
    with pytest.raises(UnknownError):
        office.work.raise_for_exceedance("EX-1999-001", Job.VALVE, APRIL)
    with pytest.raises(UnknownError):
        office.work.raise_for_hit("SH-1999-001", Job.COVER, APRIL)

"""What every command group needs: the book, the date readers, the printing.

One refusal path. Every command that can be told something the book will not
take lets the package's own exception out, and it is turned into a message with
no traceback here. Nothing in the command modules catches anything.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import click

from gemwalk.clock import read_day, read_moment
from gemwalk.errors import GemwalkError, UnitError
from gemwalk.report.frame import Report
from gemwalk.service.office import Office

F = TypeVar("F", bound=Callable[..., Any])


class DayType(click.ParamType):
    """A date on the command line, written the way the field sheets are."""

    name = "date"

    def convert(self, value: Any, param: Any, ctx: Any) -> dt.date:
        """Read the argument as a date, or fail the way click expects."""
        if isinstance(value, dt.date):
            return value
        try:
            return read_day(str(value))
        except UnitError:
            self.fail(f"{value!r} is not a date, write it as 2025-04-08", param, ctx)


class MomentType(click.ParamType):
    """A wall time on the command line, read in the site's own zone."""

    name = "moment"

    def __init__(self, zone: str = "UTC") -> None:
        self.zone = zone

    def convert(self, value: Any, param: Any, ctx: Any) -> dt.datetime:
        """Read the argument as a moment, or fail the way click expects."""
        if isinstance(value, dt.datetime):
            return value
        zone = self.zone
        if ctx is not None and isinstance(ctx.obj, Ledger) and ctx.obj.zone:
            zone = ctx.obj.zone
        try:
            return read_moment(str(value), zone)
        except UnitError:
            self.fail(f"{value!r} is not a moment, write it as '2025-04-08 06:30'", param, ctx)


DAY = DayType()
MOMENT = MomentType()


class Ledger:
    """What the top level command hands down to every group.

    The book is opened the first time something asks for it, so a command that
    only prints help does not create a file as a side effect.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.zone = ""
        self._office: Office | None = None

    @property
    def office(self) -> Office:
        """The office, opened and migrated the first time it is wanted."""
        if self._office is None:
            self._office = Office.open(self.path)
        return self._office

    def use_zone(self, site: str) -> str:
        """Remember a site's wall clock so a moment argument can be read in it."""
        self.zone = self.office.sites.zone_of(site)
        return self.zone

    def close(self) -> None:
        """Shut the book, if it was ever opened."""
        if self._office is not None:
            self._office.close()
            self._office = None


pass_ledger = click.make_pass_decorator(Ledger)


def show(report: Report) -> None:
    """Print a report."""
    click.echo(report.render(), nl=False)


def line(text: str) -> None:
    """Print one line."""
    click.echo(text)


def rows(headings: tuple[str, ...], body: list[tuple[str, ...]]) -> None:
    """Print a small table without building a whole report for it."""
    widths = [len(head) for head in headings]
    for row in body:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    click.echo("  ".join(h.ljust(w) for h, w in zip(headings, widths, strict=True)).rstrip())
    click.echo("  ".join("-" * w for w in widths))
    for row in body:
        click.echo("  ".join(c.ljust(w) for c, w in zip(row, widths, strict=True)).rstrip())


def refuse(failure: GemwalkError) -> click.ClickException:
    """Turn one of the package's refusals into a message with no traceback."""
    return click.ClickException(str(failure))


__all__ = [
    "DAY",
    "MOMENT",
    "DayType",
    "Ledger",
    "MomentType",
    "line",
    "pass_ledger",
    "refuse",
    "rows",
    "show",
]

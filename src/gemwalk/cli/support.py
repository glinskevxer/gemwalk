"""What every command group needs: the book, the date readers, the printing.

One refusal path. Every command that can be told something the book will not
take lets the package's own exception out, and it is turned into a message with
no traceback here. Nothing in the command modules catches anything.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Sequence
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


DAY = DayType()


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


class DeskGroup(click.Group):
    """A command group that turns the package's refusals into messages.

    Every command under it can let a :class:`~gemwalk.errors.GemwalkError` out,
    and it arrives here as an ordinary click failure with no traceback. Putting
    it on the top level group is enough, because a subgroup is invoked through
    it.
    """

    def invoke(self, ctx: click.Context) -> Any:
        """Run the command and turn a refusal into a message."""
        try:
            return super().invoke(ctx)
        except GemwalkError as failure:
            raise refuse(failure) from None


pass_ledger = click.make_pass_decorator(Ledger)


def moment_at(ledger: Ledger, site: str, text: str) -> dt.datetime:
    """Read a wall time in the site's own zone.

    A moment cannot be a click parameter type, because click reads the options
    before the command body runs and the zone is not known until the site has
    been looked up. So the moment arrives as text and is read here.
    """
    try:
        return read_moment(text, ledger.use_zone(site))
    except UnitError:
        raise click.BadParameter(
            f"{text!r} is not a moment, write it as '2025-04-08 06:30'"
        ) from None


def show(report: Report) -> None:
    """Print a report."""
    click.echo(report.render(), nl=False)


def line(text: str) -> None:
    """Print one line."""
    click.echo(text)


def rows(headings: tuple[str, ...], body: Sequence[Sequence[str]]) -> None:
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
    "DayType",
    "DeskGroup",
    "Ledger",
    "line",
    "moment_at",
    "pass_ledger",
    "refuse",
    "rows",
    "show",
]

"""The top level command, and the book every group works through."""

from __future__ import annotations

import sys

import click

from gemwalk import __version__
from gemwalk.cli.landfill import site
from gemwalk.cli.monitoring import run as run_group
from gemwalk.cli.support import DeskGroup, Ledger, line, pass_ledger, rows
from gemwalk.cli.wellfield import pipe, well
from gemwalk.errors import GemwalkError
from gemwalk.store.migrations import MIGRATIONS, pending, version

DEFAULT_BOOK = "gemwalk.sqlite3"


@click.group(cls=DeskGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--book",
    default=DEFAULT_BOOK,
    envvar="GEMWALK_BOOK",
    type=click.Path(dir_okay=False),
    show_default=True,
    help="the sqlite file this site's records live in",
)
@click.version_option(__version__, prog_name="gemwalk")
@click.pass_context
def main(ctx: click.Context, book: str) -> None:
    """Landfill gas collection and control, from the wellhead to the flare."""
    ctx.obj = Ledger(book)
    ctx.call_on_close(ctx.obj.close)


@main.group()
def store() -> None:
    """The book itself: making one, checking it, counting what is in it."""


@store.command("init")
@pass_ledger
def store_init(ledger: Ledger) -> None:
    """Make a book, or bring an existing one up to the current schema."""
    office = ledger.office
    line(f"{ledger.path} is at schema {office.schema_version} of {MIGRATIONS[-1].number}")


@store.command("counts")
@pass_ledger
def store_counts(ledger: Ledger) -> None:
    """Say how many rows are in each table."""
    counts = ledger.office.counts()
    rows(("table", "rows"), [(name, str(count)) for name, count in counts.items()])


@store.command("check")
@pass_ledger
def store_check(ledger: Ledger) -> None:
    """Say whether the book is at the schema the package expects."""
    office = ledger.office
    owed = pending(office.book)
    if owed:
        names = ", ".join(str(m.number) for m in owed)
        raise click.ClickException(f"the book is missing migrations {names}")
    line(f"schema {version(office.book)}, nothing owed")


@main.command()
def about() -> None:
    """Say what this is and what it is for."""
    line(f"gemwalk {__version__}")
    line("landfill gas collection and control system field desk")
    line("wellfield monitoring, exceedance clocks, surface walkovers, the blower station")


main.add_command(site)
main.add_command(well)
main.add_command(pipe)
main.add_command(run_group)


def run() -> int:
    """The console script, with the package's refusals turned into messages."""
    try:
        main.main(standalone_mode=False)
    except click.ClickException as failure:
        failure.show()
        return failure.exit_code
    except click.Abort:
        click.echo("aborted", err=True)
        return 1
    except GemwalkError as failure:
        click.echo(f"error: {failure}", err=True)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())

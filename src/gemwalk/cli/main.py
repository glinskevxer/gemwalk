"""The top level command, and the book every group works through."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from gemwalk import __version__
from gemwalk.cli.cover import cover
from gemwalk.cli.instrument import meter
from gemwalk.cli.landfill import site
from gemwalk.cli.memo import note
from gemwalk.cli.monitoring import run as run_group
from gemwalk.cli.plant import plant, water
from gemwalk.cli.records import record, work
from gemwalk.cli.report import report
from gemwalk.cli.sheets import export
from gemwalk.cli.support import DeskGroup, Ledger, line, pass_ledger, rows
from gemwalk.cli.wellfield import pipe, well
from gemwalk.errors import GemwalkError
from gemwalk.service.seed import seed
from gemwalk.store.maintenance import copy_to, health, row_counts, tidy
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


@store.command("verify")
@pass_ledger
def store_verify(ledger: Ledger) -> None:
    """Read the book for damage and for records that point at nothing."""
    found = health(ledger.office.book)
    line(str(found))
    for said in found.damage:
        line(f"  {said}")
    for orphan in found.orphans:
        line(f"  {orphan}")
    if not found.is_sound:
        raise click.ClickException("the book is not sound")


@store.command("tidy")
@pass_ledger
def store_tidy(ledger: Ledger) -> None:
    """Rebuild the file to reclaim space and refresh the query planner."""
    before = health(ledger.office.book)
    after = tidy(ledger.office.book)
    line(f"{before.bytes:,} bytes before, {after.bytes:,} after")


@store.command("backup")
@click.argument("target", type=click.Path(dir_okay=False, path_type=Path))
@pass_ledger
def store_backup(ledger: Ledger, target: Path) -> None:
    """Take a consistent copy of the book, whatever is going on in it."""
    written = copy_to(ledger.office.book, target)
    line(f"{ledger.path} copied to {written}")


@store.command("rows")
@pass_ledger
def store_rows(ledger: Ledger) -> None:
    """Say how many rows are in each table, biggest first."""
    counts = row_counts(ledger.office.book)
    rows(("table", "rows"), [(name, str(count)) for name, count in counts.items()])


@store.command("seed")
@click.option("--force", is_flag=True, help="seed a book that already has a site in it")
@pass_ledger
def store_seed(ledger: Ledger, force: bool) -> None:
    """Fill the book with a year of a plausible site, so it can be looked at."""
    office = ledger.office
    if office.counts().get("site", 0) and not force:
        raise click.ClickException("this book already has a site in it, pass --force")
    counts = seed(office)
    line(f"seeded {ledger.path}")
    rows(("table", "rows"), [(name, str(count)) for name, count in counts.items() if count])


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
main.add_command(record)
main.add_command(work)
main.add_command(cover)
main.add_command(plant)
main.add_command(water)
main.add_command(meter)
main.add_command(report)
main.add_command(export)
main.add_command(note)


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

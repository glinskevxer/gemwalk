"""Commands that write the records out as comma separated sheets."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import click

from gemwalk.cli.support import DAY, Ledger, line, pass_ledger
from gemwalk.clock import Quarter
from gemwalk.report.sheets import (
    Sheet,
    calibrations_sheet,
    devices_sheet,
    everything,
    faults_sheet,
    notes_sheet,
    orders_sheet,
    readings_sheet,
    records_sheet,
    surface_sheet,
)

TO = click.option(
    "--to",
    "target",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="a file to write, instead of printing",
)


def deliver(sheet: Sheet, target: Path | None) -> None:
    """Print a sheet, or write it to a file and say what was written."""
    if target is None:
        click.echo(sheet.text(), nl=False)
        return
    target.write_text(sheet.text())
    line(f"{len(sheet.rows)} rows to {target}")


@click.group()
def export() -> None:
    """Write the records out as sheets a spreadsheet can open."""


@export.command("everything")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day the open records are read as of")
@click.option(
    "--into",
    "room",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
    help="a directory to write the sheets into",
)
@pass_ledger
def export_everything(ledger: Ledger, site: str, on: dt.date, room: Path) -> None:
    """Write every sheet a site has into a directory."""
    room.mkdir(parents=True, exist_ok=True)
    made = everything(ledger.office, site, on)
    for sheet in made:
        target = room / f"{sheet.name}.csv"
        target.write_text(sheet.text())
        line(f"{len(sheet.rows):>6} rows  {target.name}")
    line(f"{len(made)} sheets into {room}")


@export.command("devices")
@click.argument("site")
@TO
@pass_ledger
def export_devices(ledger: Ledger, site: str, target: Path | None) -> None:
    """Write every device at one site."""
    deliver(devices_sheet(ledger.office, site), target)


@export.command("faults")
@click.argument("site")
@TO
@pass_ledger
def export_faults(ledger: Ledger, site: str, target: Path | None) -> None:
    """Write every fault ever found on one site's cover."""
    deliver(faults_sheet(ledger.office, site), target)


@export.command("notes")
@click.argument("site")
@TO
@pass_ledger
def export_notes(ledger: Ledger, site: str, target: Path | None) -> None:
    """Write every note anybody has written at one site."""
    deliver(notes_sheet(ledger.office, site, ledger.use_zone(site)), target)


@export.command("readings")
@click.argument("run")
@TO
@pass_ledger
def export_readings(ledger: Ledger, run: str, target: Path | None) -> None:
    """Write every wellhead reading on one run."""
    deliver(readings_sheet(ledger.office, run), target)


@export.command("records")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to measure the clocks against")
@TO
@pass_ledger
def export_records(ledger: Ledger, site: str, on: dt.date, target: Path | None) -> None:
    """Write every open exceedance at a site."""
    deliver(records_sheet(ledger.office, site, on), target)


@export.command("orders")
@click.argument("site")
@click.option("--from", "first", type=DAY, required=True, help="the first day")
@click.option("--to-day", "last", type=DAY, required=True, help="the last day")
@TO
@pass_ledger
def export_orders(
    ledger: Ledger, site: str, first: dt.date, last: dt.date, target: Path | None
) -> None:
    """Write every work order raised inside a range of days."""
    deliver(orders_sheet(ledger.office, site, first, last), target)


@export.command("surface")
@click.argument("site")
@click.argument("quarter")
@TO
@pass_ledger
def export_surface(ledger: Ledger, site: str, quarter: str, target: Path | None) -> None:
    """Write every spot found on the cover in one quarter."""
    deliver(surface_sheet(ledger.office, site, Quarter.parse(quarter)), target)


@export.command("calibrations")
@click.argument("label")
@TO
@pass_ledger
def export_calibrations(ledger: Ledger, label: str, target: Path | None) -> None:
    """Write every calibration of one meter."""
    meter = ledger.office.instruments.instruments.get(label)
    zone = ledger.use_zone(meter.site)
    deliver(calibrations_sheet(ledger.office, label, zone), target)


__all__ = ["deliver", "export"]

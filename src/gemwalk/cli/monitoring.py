"""Commands for the monthly monitoring run."""

from __future__ import annotations

import datetime as dt

import click

from gemwalk.cli.support import DAY, Ledger, line, pass_ledger, rows
from gemwalk.clock import Month
from gemwalk.quality import Character


@click.group()
def run() -> None:
    """Opening a monitoring run, reading the wellheads, closing it."""


@run.command("open")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day the crew starts")
@click.option("--monitor", required=True, help="who is walking it")
@click.option("--meter", required=True, help="the serial of the analyser")
@pass_ledger
def run_open(ledger: Ledger, site: str, on: dt.date, monitor: str, meter: str) -> None:
    """Start a monitoring pass over a site."""
    made = ledger.office.monitoring.open_run(site, on, monitor=monitor, meter=meter)
    roster = ledger.office.wellfield.roster(site)
    line(f"{made.label} open, {len(roster)} wellheads to read")


@run.command("read")
@click.argument("label")
@click.argument("device")
@click.option("--on", type=DAY, required=True, help="the day the wellhead was read")
@click.option("--methane", type=float, required=True, help="methane percent by volume")
@click.option("--carbon", type=float, required=True, help="carbon dioxide percent by volume")
@click.option("--oxygen", type=float, required=True, help="oxygen percent by volume")
@click.option("--balance", type=float, required=True, help="balance percent, which is nitrogen")
@click.option(
    "--temp",
    "temperature",
    type=float,
    required=True,
    help="wellhead temperature in Fahrenheit",
)
@click.option("--static", type=float, required=True, help="gauge pressure in inches of water")
@click.option("--applied", type=float, required=True, help="applied vacuum in inches of water")
@click.option("--flow", type=float, required=True, help="flow in standard cubic feet a minute")
@click.option("--valve-before", type=float, required=True, help="turns open on arrival")
@click.option("--valve-after", type=float, required=True, help="turns open on leaving")
@click.option("--note", default="", help="anything the crew wrote on the sheet")
@pass_ledger
def run_read(
    ledger: Ledger,
    label: str,
    device: str,
    on: dt.date,
    methane: float,
    carbon: float,
    oxygen: float,
    balance: float,
    temperature: float,
    static: float,
    applied: float,
    flow: float,
    valve_before: float,
    valve_after: float,
    note: str,
) -> None:
    """Write one wellhead reading onto an open run."""
    ledger.office.monitoring.record(
        label,
        device,
        on=on,
        methane=methane,
        carbon=carbon,
        oxygen=oxygen,
        balance=balance,
        temperature=temperature,
        static=static,
        applied=applied,
        flow=flow,
        valve_before=valve_before,
        valve_after=valve_after,
        note=note,
    )
    result = ledger.office.monitoring.assessment(label, device)
    if result.is_clear:
        line(f"{device} read clear")
    else:
        line(f"{device} over on " + ", ".join(str(kind) for kind in result.kinds))
    for concern in result.concerns:
        line(f"  look again: {concern}")


@run.command("missing")
@click.argument("label")
@pass_ledger
def run_missing(ledger: Ledger, label: str) -> None:
    """List the wellheads on the roster this run has no reading for."""
    short = ledger.office.monitoring.missing(label)
    if not short:
        line("every wellhead on the roster has been read")
        return
    line(f"{len(short)} unread")
    for device in short:
        line(f"  {device.label}  {device.station}")


@run.command("close")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day the crew finished")
@click.option("--note", default="", help="why any wellhead was left unread")
@pass_ledger
def run_close(ledger: Ledger, label: str, on: dt.date, note: str) -> None:
    """Shut a run once every wellhead on the roster has been read."""
    closed = ledger.office.monitoring.close_run(label, on, note=note)
    line(f"{closed.label} closed on {closed.closed_on}")


@run.command("show")
@click.argument("label")
@pass_ledger
def run_show(ledger: Ledger, label: str) -> None:
    """Read every wellhead on a run against the site's standard."""
    desk = ledger.office.monitoring
    body: list[tuple[str, ...]] = []
    for result in desk.assessments(label):
        reading = desk.readings.on_run_for(label, result.device)
        if reading is None:
            continue
        body.append(
            (
                result.device,
                str(reading.methane_reading),
                str(reading.oxygen_reading),
                str(reading.nitrogen),
                str(reading.wellhead_temperature),
                str(reading.gauge),
                str(reading.gas_flow),
                ", ".join(str(kind) for kind in result.kinds) or "-",
            )
        )
    rows(("well", "CH4", "O2", "bal", "temp", "gauge", "flow", "over"), body)


@run.command("quality")
@click.argument("label")
@pass_ledger
def run_quality(ledger: Ledger, label: str) -> None:
    """Read every analysis on a run for what it says about the well."""
    desk = ledger.office.monitoring
    shapes = desk.characters(label)
    body: list[tuple[str, ...]] = []
    for reading in desk.readings.of_run(label):
        analysis = reading.analysis
        body.append(
            (
                reading.device,
                str(reading.methane_reading),
                str(analysis.corrected_methane),
                f"{analysis.air:.1f}%",
                f"{analysis.nitrogen_ratio:.1f}" if reading.oxygen > 0 else "-",
                f"{analysis.heat_value():.0f}",
                str(shapes[reading.device]),
            )
        )
    rows(("well", "CH4", "corrected", "air", "N2/O2", "btu", "what it looks like"), body)
    line(
        f"{desk.field_flow(label):,.0f} scfm off the field, {desk.energy(label):,.2f} MMBtu an hour"
    )


@run.command("shape")
@click.argument("label")
@click.option(
    "--like",
    type=click.Choice([c.name.lower() for c in Character]),
    required=True,
    help="the shape of analysis to list",
)
@pass_ledger
def run_shape(ledger: Ledger, label: str, like: str) -> None:
    """List the wellheads on a run whose analysis has one shape."""
    wanted = Character[like.upper()]
    found = ledger.office.monitoring.of_character(label, wanted)
    line(f"{len(found)} wellheads read as {wanted}")
    for reading in found:
        analysis = reading.analysis
        line(
            f"  {reading.device}  {reading.methane_reading} methane, "
            f"{analysis.air:.1f}% air, {analysis.excess_nitrogen:.1f}% nitrogen unaccounted for"
        )


@run.command("drift")
@click.argument("device")
@click.option("--back", type=int, default=3, help="how many readings to look over")
@pass_ledger
def run_drift(ledger: Ledger, device: str, back: int) -> None:
    """Say which way a wellhead's corrected methane has been going."""
    moved = ledger.office.monitoring.drifting(device, back)
    if moved is None:
        line(f"{device} has not been read enough times to say")
        return
    way = "up" if moved > 0 else "down"
    line(f"{device} corrected methane has gone {way} {abs(moved):.1f} points")


@run.command("post")
@click.argument("label")
@pass_ledger
def run_post(ledger: Ledger, label: str) -> None:
    """Read a run into the compliance records."""
    posting = ledger.office.compliance.post_run(label)
    line(f"{posting.touched} records moved")
    if posting.opened:
        line("opened: " + ", ".join(posting.opened))
    if posting.continued:
        line("still over: " + ", ".join(posting.continued))
    if posting.escalated:
        line("moved on a stage: " + ", ".join(posting.escalated))
    if posting.closed:
        line("closed: " + ", ".join(posting.closed))


@run.command("list")
@click.argument("site")
@pass_ledger
def run_list(ledger: Ledger, site: str) -> None:
    """List every run at a site."""
    desk = ledger.office.monitoring
    rows(
        ("run", "started", "closed", "monitor", "meter", "read"),
        [
            (
                pass_.label,
                str(pass_.started_on),
                str(pass_.closed_on or "open"),
                pass_.monitor,
                pass_.meter,
                str(len(desk.readings.of_run(pass_.label))),
            )
            for pass_ in desk.runs.of_site(site)
        ],
    )


@run.command("gaps")
@click.argument("site")
@click.option("--first", "first", required=True, help="the first month, as 2025-01")
@click.option("--last", "last", required=True, help="the last month, as 2025-12")
@pass_ledger
def run_gaps(ledger: Ledger, site: str, first: str, last: str) -> None:
    """Name every month in a range with no monitoring run at all."""
    missed = ledger.office.monitoring.months_missed(site, Month.parse(first), Month.parse(last))
    if not missed:
        line("every month in the range was walked")
        return
    line("no run in " + ", ".join(str(month) for month in missed))


__all__ = ["run"]

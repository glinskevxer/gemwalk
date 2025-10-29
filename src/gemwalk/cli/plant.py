"""Commands for the blower station and for the liquids that come back."""

from __future__ import annotations

import datetime as dt

import click

from gemwalk.cli.support import DAY, Ledger, line, moment_at, pass_ledger, rows
from gemwalk.clock import show_moment
from gemwalk.model.liquids import SumpKind
from gemwalk.model.plant import ControlKind


@click.group()
def plant() -> None:
    """The control devices, their operating record and their outages."""


@plant.command("install")
@click.argument("label")
@click.argument("site")
@click.argument("name")
@click.option(
    "--kind",
    type=click.Choice([k.name.lower() for k in ControlKind]),
    required=True,
    help="what burns the gas",
)
@click.option("--capacity", type=float, required=True, help="what it can take, in scfm")
@click.option("--floor", type=float, default=None, help="minimum chamber temperature")
@click.option("--on", type=DAY, required=True, help="the day it went in")
@pass_ledger
def plant_install(
    ledger: Ledger,
    label: str,
    site: str,
    name: str,
    kind: str,
    capacity: float,
    floor: float | None,
    on: dt.date,
) -> None:
    """Put a control device on the system."""
    made = ledger.office.plant.install(
        label,
        site,
        name,
        kind=ControlKind[kind.upper()],
        capacity=capacity,
        on=on,
        floor_degrees=floor,
    )
    held = f", held at or above {made.floor}" if made.floor is not None else ""
    line(f"{made.label} in service as a {made.kind}{held}")


@plant.command("log")
@click.argument("label")
@click.argument("at")
@click.option("--running/--down", default=True, help="was the device burning gas")
@click.option("--flow", type=float, required=True, help="inlet flow in scfm")
@click.option("--methane", type=float, required=True, help="inlet methane percent")
@click.option(
    "--temp",
    "temperature",
    type=float,
    default=None,
    help="chamber temperature in Fahrenheit",
)
@click.option("--note", default="", help="anything the operator wrote down")
@pass_ledger
def plant_log(
    ledger: Ledger,
    label: str,
    at: str,
    running: bool,
    flow: float,
    methane: float,
    temperature: float | None,
    note: str,
) -> None:
    """Write one line of a device's operating record."""
    control = ledger.office.plant.controls.get(label)
    moment = moment_at(ledger, control.site, at)
    record = ledger.office.plant.log(
        label,
        moment,
        running=running,
        flow=flow,
        methane=methane,
        temperature=temperature,
        note=note,
    )
    line(f"{label} logged, {record.methane_flow:.1f} scfm of methane")


@plant.command("blocks")
@click.argument("label")
@click.option("--from", "first", required=True, help="the first moment, as '2025-06-11 09:00'")
@click.option("--to", "last", required=True, help="the last moment")
@pass_ledger
def plant_blocks(ledger: Ledger, label: str, first: str, last: str) -> None:
    """Print the fixed three hour blocks and their averages."""
    control = ledger.office.plant.controls.get(label)
    zone = ledger.use_zone(control.site)
    start = moment_at(ledger, control.site, first)
    end = moment_at(ledger, control.site, last)
    body: list[tuple[str, ...]] = []
    for block in ledger.office.plant.blocks(label, start, end):
        body.append(
            (
                show_moment(block.start, zone),
                str(block.readings),
                str(block.running),
                "-" if block.average is None else f"{block.average:.1f}",
                "below" if block.below else "",
            )
        )
    rows(("block", "records", "running", "average", ""), body)


@plant.command("down")
@click.argument("label")
@click.argument("at")
@click.argument("reason")
@click.option("--planned/--unplanned", default=False, help="was the outage arranged")
@pass_ledger
def plant_down(ledger: Ledger, label: str, at: str, reason: str, planned: bool) -> None:
    """Record a control device going down."""
    control = ledger.office.plant.controls.get(label)
    moment = moment_at(ledger, control.site, at)
    outage = ledger.office.plant.start_outage(label, moment, reason, planned=planned)
    subpart = ledger.office.sites.standard_of(control.site)
    line(f"{outage.label} open, back within {subpart.shutdown_days} days")


@plant.command("up")
@click.argument("outage")
@click.argument("at")
@click.option("--note", default="", help="what was done")
@pass_ledger
def plant_up(ledger: Ledger, outage: str, at: str, note: str) -> None:
    """Record a control device coming back."""
    found = ledger.office.plant.outages.get(outage)
    moment = moment_at(ledger, found.site, at)
    closed = ledger.office.plant.end_outage(outage, moment, note)
    line(f"{closed.label} closed after {closed.hours(moment):.1f} hours")


@plant.command("board")
@click.argument("site")
@click.argument("at")
@pass_ledger
def plant_board(ledger: Ledger, site: str, at: str) -> None:
    """Say what is down and what has been down too long."""
    moment = moment_at(ledger, site, at)
    desk = ledger.office.plant
    down = desk.down_now(site)
    if not down:
        line("every control device is available")
    for outage in down:
        line(f"{outage.control} down since {outage.started_at.date()}: {outage.reason}")
    long = desk.long_outages(site, moment)
    if long:
        line("past the window: " + ", ".join(o.label for o in long))


@click.group()
def water() -> None:
    """Liquid levels, the sumps and what gets hauled off them."""


@water.command("tape")
@click.argument("device")
@click.argument("depth", type=float)
@click.option("--on", type=DAY, required=True, help="the day the tape went down")
@click.option("--pumped/--not-pumped", default=False, help="was the well pumped that day")
@click.option("--note", default="", help="anything the crew wrote down")
@pass_ledger
def water_tape(
    ledger: Ledger, device: str, depth: float, on: dt.date, pumped: bool, note: str
) -> None:
    """Write down a tape drop at one well."""
    ledger.office.liquids.tape(device, on, depth, pumped=pumped, note=note)
    water_in = ledger.office.liquids.water_in(device, on)
    if water_in is None:
        line(f"{device} tape recorded")
        return
    state = "flooded" if water_in.flooded else f"{water_in.share * 100:.0f}% of screen under water"
    line(f"{device} has {water_in.column:.1f} ft standing, {state}")


@water.command("standing")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to read the levels as of")
@pass_ledger
def water_standing(ledger: Ledger, site: str, on: dt.date) -> None:
    """List what is standing in every well, wettest first."""
    standing = ledger.office.liquids.standing(site, on)
    if not standing:
        line("no tape drops on file")
        return
    rows(
        ("well", "tape", "column", "screen under water", ""),
        [
            (
                w.device.label,
                f"{w.level.depth:g}",
                f"{w.column:.1f}",
                f"{w.share * 100:.0f}%",
                "pump" if w.needs_pumping else "",
            )
            for w in standing
        ],
    )


@water.command("sump")
@click.argument("site")
@click.argument("station")
@click.option("--capacity", type=float, required=True, help="how much it holds, in gallons")
@click.option(
    "--kind",
    type=click.Choice([k.name.lower() for k in SumpKind]),
    default=SumpKind.KNOCKOUT.name.lower(),
    help="what kind of catcher it is",
)
@click.option("--on", type=DAY, required=True, help="the day it went in")
@pass_ledger
def water_sump(
    ledger: Ledger, site: str, station: str, capacity: float, kind: str, on: dt.date
) -> None:
    """Put a condensate catcher on the pipe tree."""
    made = ledger.office.liquids.add_sump(
        site, station, kind=SumpKind[kind.upper()], capacity=capacity, on=on
    )
    line(f"{made.label} in at {made.station}, {made.capacity:g} gallons")


@water.command("pump")
@click.argument("sump")
@click.argument("at")
@click.argument("gallons", type=float)
@click.option("--hauler", required=True, help="who took the load")
@click.option("--to", "bound_for", required=True, help="where the load went")
@click.option("--note", default="", help="anything on the ticket")
@pass_ledger
def water_pump(
    ledger: Ledger, sump: str, at: str, gallons: float, hauler: str, bound_for: str, note: str
) -> None:
    """Write down a load taken off a sump."""
    found = ledger.office.liquids.sumps.get(sump)
    moment = moment_at(ledger, found.site, at)
    load = ledger.office.liquids.pump(
        sump, moment, gallons, hauler=hauler, bound_for=bound_for, note=note
    )
    filled = f"{load.fills(found) * 100:.0f}% of the pot"
    line(f"{load.gallons:g} gallons off {sump} to {load.bound_for}, {filled}")


@water.command("hauled")
@click.argument("site")
@click.option("--from", "first", required=True, help="the first moment")
@click.option("--to", "last", required=True, help="the last moment")
@pass_ledger
def water_hauled(ledger: Ledger, site: str, first: str, last: str) -> None:
    """Say how much came off every sump at a site in a range."""
    start = moment_at(ledger, site, first)
    end = moment_at(ledger, site, last)
    total = ledger.office.liquids.hauled(site, start, end)
    line(f"{total:,.0f} gallons hauled")
    by_hauler = ledger.office.liquids.by_hauler(start, end)
    if by_hauler:
        rows(("hauler", "gallons"), [(name, f"{g:,.0f}") for name, g in by_hauler.items()])


__all__ = ["plant", "water"]

"""Commands for the devices in the ground and the pipe they hang off."""

from __future__ import annotations

import datetime as dt

import click

from gemwalk.cli.support import DAY, Ledger, line, pass_ledger, rows
from gemwalk.model.device import Kind, State
from gemwalk.model.piping import MATERIALS
from gemwalk.units import Temperature


@click.group()
def well() -> None:
    """Drilling, wiring, raising and retiring the extraction devices."""


@well.command("drill")
@click.argument("site")
@click.argument("area")
@click.option("--station", required=True, help="where on the site it went in")
@click.option("--depth", type=float, required=True, help="total borehole depth in feet")
@click.option("--screen-top", type=float, required=True, help="top of the slotted pipe")
@click.option("--screen-bottom", type=float, required=True, help="bottom of the slotted pipe")
@click.option("--on", type=DAY, required=True, help="the day it was drilled")
@click.option(
    "--kind",
    type=click.Choice([k.name.lower() for k in Kind]),
    default=Kind.VERTICAL.name.lower(),
    help="what went in the ground",
)
@click.option("--label", default=None, help="a label off the old paper records")
@pass_ledger
def well_drill(
    ledger: Ledger,
    site: str,
    area: str,
    station: str,
    depth: float,
    screen_top: float,
    screen_bottom: float,
    on: dt.date,
    kind: str,
    label: str | None,
) -> None:
    """Put a new device in the ground."""
    made = ledger.office.wellfield.drill(
        site,
        area,
        kind=Kind[kind.upper()],
        station=station,
        total_depth=depth,
        screen_top=screen_top,
        screen_bottom=screen_bottom,
        on=on,
        label=label,
    )
    line(f"{made.label} drilled in {made.area}, {made.screen_length:g} ft of screen")


@well.command("connect")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day it went on the tree")
@pass_ledger
def well_connect(ledger: Ledger, label: str, on: dt.date) -> None:
    """Wire a drilled device onto the pipe tree."""
    device = ledger.office.wellfield.connect(label, on)
    line(f"{device.label} on the run from {device.connected_on}")


@well.command("off")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day the valve was shut")
@pass_ledger
def well_off(ledger: Ledger, label: str, on: dt.date) -> None:
    """Take a device off the monthly run, for a raise or a repair."""
    device = ledger.office.wellfield.take_offline(label, on)
    subpart = ledger.office.sites.standard_of(device.site)
    line(f"{device.label} off the run, back on within {subpart.raising_days} days")


@well.command("on")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day it went back on")
@pass_ledger
def well_on(ledger: Ledger, label: str, on: dt.date) -> None:
    """Put a device that was off the run back on it."""
    device = ledger.office.wellfield.put_online(label, on)
    line(f"{device.label} back on the run")


@well.command("abandon")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day it came out of service")
@pass_ledger
def well_abandon(ledger: Ledger, label: str, on: dt.date) -> None:
    """Take a device out of service for good."""
    device = ledger.office.wellfield.abandon(label, on)
    line(f"{device.label} abandoned on {device.abandoned_on}")


@well.command("approve")
@click.argument("label")
@click.argument("degrees", type=float)
@click.option("--on", type=DAY, required=True, help="the day the approval takes effect")
@pass_ledger
def well_approve(ledger: Ledger, label: str, degrees: float, on: dt.date) -> None:
    """Record an approved higher operating temperature for one wellhead."""
    device = ledger.office.wellfield.approve_higher_temperature(label, Temperature(degrees), on)
    line(f"{device.label} held to {Temperature(degrees)} from {on}")


@well.command("list")
@click.argument("site")
@click.option(
    "--state",
    type=click.Choice([s.value for s in State]),
    default=None,
    help="only devices in one state",
)
@pass_ledger
def well_list(ledger: Ledger, site: str, state: str | None) -> None:
    """List the devices at a site."""
    devices = ledger.office.wellfield.devices.of_site(site)
    if state is not None:
        devices = [d for d in devices if d.state.value == state]
    rows(
        ("device", "area", "kind", "state", "screen", "lateral", "drilled"),
        [
            (
                d.label,
                d.area,
                str(d.kind),
                str(d.state),
                f"{d.screen_top:g}-{d.screen_bottom:g}",
                d.lateral or "-",
                str(d.drilled_on),
            )
            for d in devices
        ],
    )


@well.command("roster")
@click.argument("site")
@pass_ledger
def well_roster(ledger: Ledger, site: str) -> None:
    """List the devices the crew is expected to read on the next run."""
    roster = ledger.office.wellfield.roster(site)
    line(f"{len(roster)} devices on the run")
    for device in roster:
        line(f"  {device.label}  {device.station}")


@well.command("board")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to measure against")
@pass_ledger
def well_board(ledger: Ledger, site: str, on: dt.date) -> None:
    """Say what is off the run, unwired, or past a window."""
    desk = ledger.office.wellfield
    tally = desk.count_by_state(site)
    line("  ".join(f"{state} {count}" for state, count in tally.items()))
    waiting = desk.unconnected(site, on)
    if waiting:
        line("drilled and not wired: " + ", ".join(d.label for d in waiting))
    late = desk.overdue_offline(site, on)
    if late:
        line("off the run too long: " + ", ".join(d.label for d in late))
    unpiped = ledger.office.piping.unpiped(site)
    if unpiped:
        line("no lateral: " + ", ".join(d.label for d in unpiped))


@well.command("offline")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to measure against")
@pass_ledger
def well_offline(ledger: Ledger, site: str, on: dt.date) -> None:
    """List the devices that are off the run and how long they have been."""
    desk = ledger.office.wellfield
    off = desk.offline(site)
    if not off:
        line("nothing is off the run")
        return
    subpart = ledger.office.sites.standard_of(site)
    rows(
        ("device", "since", "days", "window", ""),
        [
            (
                d.label,
                str(d.offline_since),
                str(d.offline_days(on)),
                str(subpart.raising_days),
                "too long" if d.offline_too_long(subpart, on) else "",
            )
            for d in off
        ],
    )


@click.group()
def pipe() -> None:
    """The headers and laterals between the wellheads and the blower."""


@pipe.command("header")
@click.argument("site")
@click.argument("name")
@click.option("--diameter", type=float, required=True, help="outside diameter in inches")
@click.option("--material", type=click.Choice(MATERIALS), required=True, help="what it is made of")
@click.option("--length", type=float, required=True, help="how long the run is in feet")
@click.option("--on", type=DAY, required=True, help="the day it went in")
@pass_ledger
def pipe_header(
    ledger: Ledger,
    site: str,
    name: str,
    diameter: float,
    material: str,
    length: float,
    on: dt.date,
) -> None:
    """Lay a trunk line out of the blower station."""
    made = ledger.office.piping.lay_header(
        site, name, diameter=diameter, material=material, length_feet=length, on=on
    )
    line(f"{made.label} laid, {made.diameter:g} inch {made.material}")


@pipe.command("lateral")
@click.argument("site")
@click.argument("header")
@click.option("--diameter", type=float, required=True, help="outside diameter in inches")
@click.option("--material", type=click.Choice(MATERIALS), required=True, help="what it is made of")
@click.option("--length", type=float, required=True, help="how long the run is in feet")
@click.option("--on", type=DAY, required=True, help="the day it went in")
@pass_ledger
def pipe_lateral(
    ledger: Ledger,
    site: str,
    header: str,
    diameter: float,
    material: str,
    length: float,
    on: dt.date,
) -> None:
    """Branch a lateral off a header."""
    made = ledger.office.piping.lay_lateral(
        site, header, diameter=diameter, material=material, length_feet=length, on=on
    )
    line(f"{made.label} tied into {made.header}")


@pipe.command("tie")
@click.argument("device")
@click.argument("lateral")
@pass_ledger
def pipe_tie(ledger: Ledger, device: str, lateral: str) -> None:
    """Pipe a wellhead to a lateral."""
    tied = ledger.office.piping.tie_in(device, lateral)
    line(f"{tied.label} piped to {tied.lateral}")


@pipe.command("pull")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day it came out")
@pass_ledger
def pipe_pull(ledger: Ledger, label: str, on: dt.date) -> None:
    """Take a lateral or a header off the system, leaves first."""
    desk = ledger.office.piping
    if desk.laterals.find(label) is not None:
        desk.retire_lateral(label, on)
    else:
        desk.retire_header(label, on)
    line(f"{label} pulled on {on}")


@pipe.command("show")
@click.argument("label")
@pass_ledger
def pipe_show(ledger: Ledger, label: str) -> None:
    """Show one header and everything hanging off it."""
    desk = ledger.office.piping
    trunk = desk.trunk(label)
    line(f"{trunk.header.label}  {trunk.header.name}  {trunk.device_count} devices")
    rows(
        ("device", "area", "state", "lateral"),
        [(d.label, d.area, str(d.state), d.lateral or "-") for d in desk.devices_on_header(label)],
    )


@pipe.command("branch")
@click.argument("label")
@pass_ledger
def pipe_branch(ledger: Ledger, label: str) -> None:
    """Show one lateral and the devices on it."""
    branch = ledger.office.piping.branch(label)
    live = branch.live_devices
    line(f"{branch.lateral.label} into {branch.lateral.header}")
    line(f"  {len(branch.devices)} devices, {len(live)} of them on the run")
    for device in branch.devices:
        line(f"  {device.label}  {device.state}")


@pipe.command("tree")
@click.argument("site")
@pass_ledger
def pipe_tree(ledger: Ledger, site: str) -> None:
    """Print the collection system from the blower out."""
    for trunk in ledger.office.piping.tree(site):
        header = trunk.header
        state = "live" if header.is_live else f"pulled {header.retired_on}"
        line(f"{header.label}  {header.name}  {header.diameter:g}in  {state}")
        for branch in trunk.branches:
            lateral = branch.lateral
            line(f"  {lateral.label}  {lateral.diameter:g}in  {len(branch.devices)} devices")
            for device in branch.devices:
                line(f"    {device.label}  {device.state}")


__all__ = ["pipe", "well"]

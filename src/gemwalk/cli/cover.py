"""Commands for the quarterly walkover of the cover."""

from __future__ import annotations

import datetime as dt

import click

from gemwalk.cli.support import DAY, Ledger, line, pass_ledger, rows
from gemwalk.clock import Quarter
from gemwalk.model.fault import Damage
from gemwalk.model.landfill import Cover
from gemwalk.model.surface import Step


@click.group()
def cover() -> None:
    """Walking the cover, marking what reads over, and working the marks off."""


@cover.command("walk")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day the crew starts")
@click.option("--monitor", required=True, help="who is walking it")
@click.option("--instrument", required=True, help="the serial of the detector")
@click.option("--background", type=float, required=True, help="background in parts per million")
@click.option("--wind", type=float, required=True, help="average wind in miles an hour")
@click.option("--gust", type=float, required=True, help="the strongest gust in miles an hour")
@click.option("--spacing", type=float, default=30.0, help="pattern spacing in metres")
@pass_ledger
def cover_walk(
    ledger: Ledger,
    site: str,
    on: dt.date,
    monitor: str,
    instrument: str,
    background: float,
    wind: float,
    gust: float,
    spacing: float,
) -> None:
    """Start a walkover of the cover."""
    made = ledger.office.surface.open_walk(
        site,
        on,
        monitor=monitor,
        instrument=instrument,
        background=background,
        wind_mean=wind,
        wind_gust=gust,
        spacing=spacing,
    )
    subpart = ledger.office.sites.standard_of(site)
    line(f"{made.label} open, anything at or over {made.limit(subpart)} is a hit")
    for fault in made.faults(subpart):
        line(f"  this walk does not stand: {fault}")


@cover.command("mark")
@click.argument("walk")
@click.argument("area")
@click.argument("station")
@click.argument("reading", type=float)
@click.option("--on", type=DAY, required=True, help="the day it was read")
@click.option(
    "--kind",
    type=click.Choice([c.value for c in Cover]),
    default=Cover.INTERMEDIATE.value,
    help="what is on top at the spot",
)
@click.option("--note", default="", help="anything the crew wrote down")
@pass_ledger
def cover_mark(
    ledger: Ledger,
    walk: str,
    area: str,
    station: str,
    reading: float,
    on: dt.date,
    kind: str,
    note: str,
) -> None:
    """Write down a spot the detector read over the limit."""
    hit = ledger.office.surface.mark(
        walk, area, station, reading, on=on, cover=Cover(kind), note=note
    )
    subpart = ledger.office.sites.standard_of(hit.site)
    line(f"{hit.label} at {hit.station}, {hit.surface_reading}, repair by {hit.due(subpart)}")


@cover.command("finish")
@click.argument("walk")
@click.option("--on", type=DAY, required=True, help="the day the crew finished")
@pass_ledger
def cover_finish(ledger: Ledger, walk: str, on: dt.date) -> None:
    """Close a walkover off once the whole cover has been crossed."""
    done = ledger.office.surface.finish_walk(walk, on)
    found = len(ledger.office.surface.hits.of_walk(walk))
    line(f"{done.label} finished on {done.finished_on}, {found} spots marked")


@cover.command("repair")
@click.argument("hit")
@click.option("--on", type=DAY, required=True, help="the day the cover work was done")
@click.option("--note", default="", help="what was actually done")
@pass_ledger
def cover_repair(ledger: Ledger, hit: str, on: dt.date, note: str) -> None:
    """Record the cover work on a spot and start its remonitor window."""
    worked = ledger.office.surface.repair(hit, on, note)
    subpart = ledger.office.sites.standard_of(worked.site)
    line(f"{worked.label} repaired, remonitor by {worked.due(subpart)}")


@cover.command("remonitor")
@click.argument("hit")
@click.argument("reading", type=float)
@click.option("--on", type=DAY, required=True, help="the day it was read again")
@click.option("--note", default="", help="anything the crew wrote down")
@pass_ledger
def cover_remonitor(ledger: Ledger, hit: str, reading: float, on: dt.date, note: str) -> None:
    """Read a repaired spot again and take it wherever the number says."""
    after = ledger.office.surface.remonitor(hit, on, reading, note)
    subpart = ledger.office.sites.standard_of(after.site)
    if not after.is_open:
        line(f"{after.label} closed on {after.closed_on}")
        return
    line(f"{after.label} still over, attempt {after.attempt}, {after.step} by {after.due(subpart)}")


@cover.command("fault")
@click.argument("area")
@click.argument("station")
@click.option(
    "--kind",
    type=click.Choice([k.name.lower() for k in Damage]),
    required=True,
    help="what is wrong with the cover",
)
@click.option("--extent", type=float, required=True, help="how big it is, in square feet")
@click.option("--on", type=DAY, required=True, help="the day it was found")
@click.option("--by", "found_by", required=True, help="who found it")
@click.option("--note", default="", help="anything worth writing down")
@pass_ledger
def cover_fault(
    ledger: Ledger,
    area: str,
    station: str,
    kind: str,
    extent: float,
    on: dt.date,
    found_by: str,
    note: str,
) -> None:
    """Write down something wrong with the cover."""
    fault = ledger.office.surface.find_fault(
        area, Damage[kind.upper()], station, extent=extent, on=on, found_by=found_by, note=note
    )
    urgency = "urgent" if fault.is_urgent else "ordinary"
    line(f"{fault.label}: {urgency}, {fault.window} days, due {fault.due}")


@cover.command("fixed")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day the work was done")
@click.option("--note", default="", help="what was actually done")
@pass_ledger
def cover_fixed(ledger: Ledger, label: str, on: dt.date, note: str) -> None:
    """Record the cover work that put a fault right."""
    fault = ledger.office.surface.fix_fault(label, on, note)
    late = (
        " after its date"
        if fault.fixed_on and fault.fixed_on > (fault.found_on + dt.timedelta(days=fault.window))
        else ""
    )
    line(f"{fault.label} fixed on {fault.fixed_on}{late}")


@cover.command("faults")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to measure against")
@pass_ledger
def cover_faults(ledger: Ledger, site: str, on: dt.date) -> None:
    """List everything wrong with the cover, the least time left first."""
    desk = ledger.office.surface
    open_now = desk.open_faults(site, on)
    if not open_now:
        line("nothing is wrong with the cover")
        return
    late = {fault.label for fault in desk.late_faults(site, on)}
    rows(
        ("fault", "area", "kind", "where", "size", "found", "due", "days", ""),
        [
            (
                fault.label,
                fault.area,
                str(fault.kind),
                fault.station,
                f"{fault.extent:g}",
                str(fault.found_on),
                str(fault.due),
                str(fault.days_left(on)),
                "late" if fault.label in late else "",
            )
            for fault in open_now
        ],
    )


@cover.command("history")
@click.argument("site")
@click.argument("station")
@pass_ledger
def cover_history(ledger: Ledger, site: str, station: str) -> None:
    """List every fault ever found at one place on the cover."""
    found = ledger.office.surface.faults_at(site, station)
    if not found:
        line(f"nothing has ever been found at {station}")
        return
    for fault in found:
        line(str(fault))


@cover.command("pattern")
@click.argument("area")
@click.option("--legs", type=int, default=None, help="how many legs to lay, or work it out")
@click.option("--metres", type=float, required=True, help="how long each leg is")
@pass_ledger
def cover_pattern(ledger: Ledger, area: str, legs: int | None, metres: float) -> None:
    """Lay the walkover pattern across one area."""
    desk = ledger.office.surface
    wanted = desk.wanted_legs(area, metres)
    made = desk.lay_pattern(area, legs=legs if legs is not None else wanted, metres=metres)
    line(f"{len(made)} legs laid across {area}, which wants {wanted}")
    for leg in made:
        line(f"  {leg.label}  {leg.name}  {leg.metres:g} m")


@cover.command("cross")
@click.argument("walk")
@click.argument("legs", nargs=-1, required=True)
@click.option("--note", default="", help="anything worth writing down")
@pass_ledger
def cover_cross(ledger: Ledger, walk: str, legs: tuple[str, ...], note: str) -> None:
    """Record that a walk crossed one or more legs of the pattern."""
    for leg in legs:
        ledger.office.surface.cross(walk, leg, note)
    line(f"{len(legs)} legs crossed on {walk}")


@cover.command("route")
@click.argument("walk")
@pass_ledger
def cover_route(ledger: Ledger, walk: str) -> None:
    """Say how much of the pattern a walk covered, area by area."""
    desk = ledger.office.surface
    routes = desk.routes_of(walk)
    if not routes:
        line("this site has no areas to walk")
        return
    subpart = ledger.office.sites.standard_of(desk.walks.get(walk).site)
    for route in routes:
        line(str(route))
        if route.legs:
            line(f"  {route.swept(subpart):.1f} of {route.acres:g} acres crossed")
    if desk.covered_whole(walk):
        line("the whole pattern was walked")


@cover.command("board")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to measure against")
@pass_ledger
def cover_board(ledger: Ledger, site: str, on: dt.date) -> None:
    """List every open spot, the least time left first."""
    board = ledger.office.surface.board(site, on)
    if not board:
        line("no open spots")
        return
    rows(
        ("spot", "area", "station", "reading", "step", "attempt", "due", "days", ""),
        [
            (
                m.hit.label,
                m.hit.area,
                m.hit.station,
                f"{m.hit.reading:g}",
                str(m.hit.step),
                str(m.hit.attempt),
                str(m.due),
                str(m.days_left),
                "late" if m.late else "",
            )
            for m in board
        ],
    )


@cover.command("waiting")
@click.argument("site")
@click.option(
    "--step",
    type=click.Choice([s.value for s in Step if s is not Step.CLOSED]),
    required=True,
    help="the work the spots are waiting on",
)
@pass_ledger
def cover_waiting(ledger: Ledger, site: str, step: str) -> None:
    """List the spots waiting on one kind of work."""
    waiting = ledger.office.surface.waiting_on(site, Step(step))
    line(f"{len(waiting)} spots waiting on {step}")
    for hit in waiting:
        line(f"  {hit.label}  {hit.station}  attempt {hit.attempt}")


@cover.command("gaps")
@click.argument("site")
@click.option("--first", required=True, help="the first quarter, as 2025Q1")
@click.option("--last", required=True, help="the last quarter, as 2025Q4")
@pass_ledger
def cover_gaps(ledger: Ledger, site: str, first: str, last: str) -> None:
    """Name every quarter in a range with no valid finished walkover."""
    missed = ledger.office.surface.quarters_missed(site, Quarter.parse(first), Quarter.parse(last))
    if not missed:
        line("every quarter in the range was walked")
        return
    line("no valid walkover in " + ", ".join(str(q) for q in missed))


@cover.command("repeats")
@click.argument("site")
@click.option("--since", type=DAY, required=True, help="the day to count from")
@pass_ledger
def cover_repeats(ledger: Ledger, site: str, since: dt.date) -> None:
    """Name the places on the cover that have been marked more than once."""
    repeats = ledger.office.surface.repeat_stations(site, since)
    if not repeats:
        line("no place has been marked twice")
        return
    rows(("station", "times"), [(place, str(count)) for place, count in repeats.items()])


@cover.command("invalid")
@click.argument("site")
@pass_ledger
def cover_invalid(ledger: Ledger, site: str) -> None:
    """List the walkovers whose own conditions throw their readings out."""
    subpart = ledger.office.sites.standard_of(site)
    bad = ledger.office.surface.invalid_walks(site)
    if not bad:
        line("every walkover on the record stands")
        return
    for walk in bad:
        line(f"{walk.label}  {walk.started_on}")
        for fault in walk.faults(subpart):
            line(f"  {fault}")


@cover.command("walks")
@click.argument("site")
@pass_ledger
def cover_walks(ledger: Ledger, site: str) -> None:
    """List every walkover at a site and say whether it stands."""
    desk = ledger.office.surface
    subpart = ledger.office.sites.standard_of(site)
    rows(
        ("walk", "quarter", "started", "finished", "wind", "gust", "spacing", "stands"),
        [
            (
                w.label,
                str(w.quarter),
                str(w.started_on),
                str(w.finished_on or "open"),
                f"{w.wind_mean:g}",
                f"{w.wind_gust:g}",
                f"{w.spacing:g}",
                "yes" if w.is_valid(subpart) else "no",
            )
            for w in desk.walks.of_site(site)
        ],
    )


__all__ = ["cover"]

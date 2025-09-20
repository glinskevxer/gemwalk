"""Commands for the quarterly walkover of the cover."""

from __future__ import annotations

import datetime as dt

import click

from gemwalk.cli.support import DAY, Ledger, line, pass_ledger, rows
from gemwalk.clock import Quarter
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

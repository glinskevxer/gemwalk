"""The operating record of the blower station, read as a period rather than a day.

Almost everything about a control device is only meaningful over a stretch. A
single reading of fifteen hundred degrees says nothing; the block averages say
whether the chamber held. A single outage says nothing; the total downtime and
the longest one say whether the field had anywhere to send its gas.

So this report takes two moments and reads everything between them. The one
figure that is not a period figure is on the top line anyway, because the first
question anybody asks about a flare is whether it is lit right now.
"""

from __future__ import annotations

import datetime as dt

from gemwalk.clock import hours_between, show_moment
from gemwalk.report.frame import Align, Column, Report, Table, number, share
from gemwalk.service.office import Office


def plant_report(office: Office, site: str, first: dt.datetime, last: dt.datetime) -> Report:
    """Build the operating report for one site's blower station."""
    landfill = office.sites.sites.get(site)
    zone = landfill.zone
    report = Report(
        title=f"{landfill.name} plant report",
        subtitle=f"{show_moment(first, zone)} to {show_moment(last, zone)}, {zone}",
    )
    _now(office, report, site)
    _devices(office, report, site, first, last, zone)
    _blocks(office, report, site, first, last, zone)
    _outages(office, report, site, first, last, zone)
    _watches(office, report, site, zone)
    return report


def _now(office: Office, report: Report, site: str) -> None:
    section = report.section("right now")
    down = office.plant.down_now(site)
    live = office.plant.controls.live(site)
    section.say(f"{len(live)} control devices on the system, {len(down)} of them down")
    for outage in down:
        section.say(f"  {outage.control} down since {outage.started_at.date()}: {outage.reason}")


def _devices(
    office: Office,
    report: Report,
    site: str,
    first: dt.datetime,
    last: dt.datetime,
    zone: str,
) -> None:
    section = report.section("what each device did")
    table = Table(
        columns=(
            Column("device"),
            Column("kind"),
            Column("capacity", Align.RIGHT),
            Column("records", Align.RIGHT, adds_up=True),
            Column("running", Align.RIGHT),
            Column("methane", Align.RIGHT),
            Column("hours down", Align.RIGHT, adds_up=True),
        ),
        empty="no control device on the system",
    )
    del zone
    for control in office.plant.controls.live(site):
        records = office.plant.operations.between(control.label, first, last)
        table.add(
            control.label,
            str(control.kind),
            number(control.capacity, 0),
            len(records),
            share(office.plant.availability(control.label, first, last)),
            number(office.plant.throughput(control.label, first, last)),
            round(office.plant.downtime_hours(control.label, first, last), 1),
        )
    section.table(table)


def _blocks(
    office: Office,
    report: Report,
    site: str,
    first: dt.datetime,
    last: dt.datetime,
    zone: str,
) -> None:
    section = report.section("the chamber")
    table = Table(
        columns=(
            Column("device"),
            Column("block"),
            Column("records", Align.RIGHT),
            Column("average", Align.RIGHT),
            Column("floor", Align.RIGHT),
        ),
        title="blocks that averaged under the floor",
        empty="every block held its floor",
    )
    counted = 0
    for control in office.plant.controls.live(site):
        if not control.kind.has_chamber:
            continue
        blocks = office.plant.blocks(control.label, first, last)
        counted += sum(1 for block in blocks if not block.is_empty)
        for block in blocks:
            if block.below and block.average is not None and block.floor is not None:
                table.add(
                    control.label,
                    show_moment(block.start, zone),
                    block.readings,
                    number(block.average),
                    number(block.floor),
                )
    section.say(f"{counted} three hour blocks with the device running in them")
    section.table(table)


def _outages(
    office: Office,
    report: Report,
    site: str,
    first: dt.datetime,
    last: dt.datetime,
    zone: str,
) -> None:
    section = report.section("what was down")
    subpart = office.sites.standard_of(site)
    touching = office.plant.outages.overlapping(site, first, last)
    table = Table(
        columns=(
            Column("outage"),
            Column("device"),
            Column("from"),
            Column("to", blank="still down"),
            Column("hours", Align.RIGHT, adds_up=True),
            Column("planned"),
            Column("reason"),
        ),
        empty="nothing was down in this period",
    )
    for outage in touching:
        ended = outage.ended_at or last
        table.add(
            outage.label,
            outage.control,
            show_moment(max(outage.started_at, first), zone),
            None if outage.ended_at is None else show_moment(outage.ended_at, zone),
            round(hours_between(max(outage.started_at, first), min(ended, last)), 1),
            "yes" if outage.planned else "no",
            outage.reason,
        )
    section.table(table)
    long = office.plant.long_outages(site, last)
    if long:
        section.say(
            f"{len(long)} outages have run past the {subpart.shutdown_days} day window: "
            + ", ".join(o.label for o in long)
        )


def _watches(office: Office, report: Report, site: str, zone: str) -> None:
    section = report.section("the flame")
    over = office.plant.smoking(site)
    short = office.plant.unfinished_watches(site)
    if not over and not short:
        section.say("no watch has found more smoke than the rule allows")
        return
    table = Table(
        columns=(
            Column("watch"),
            Column("device"),
            Column("started"),
            Column("minutes", Align.RIGHT),
            Column("smoking", Align.RIGHT),
            Column("in two hours", Align.RIGHT),
            Column("verdict"),
        ),
        empty="no watch to report",
    )
    for watch in [*over, *short]:
        table.add(
            watch.label,
            watch.control,
            show_moment(watch.started_at, zone),
            number(watch.watched, 0),
            number(watch.visible),
            number(watch.in_two_hours),
            "over the limit" if watch.over else "short, go back",
        )
    section.table(table)


__all__ = ["plant_report"]

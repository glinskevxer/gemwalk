"""The quarterly compliance report, which is the one that leaves the site.

It is written for somebody who was not there and is looking for the things that
did not happen. So it leads with the gaps: months with no monitoring run,
quarters with no valid walkover, records whose windows ran out, and orders
nobody closed. Everything that went to plan is a count.

A walkover that was made in a wind the standard does not allow counts as a
quarter with no walkover, and that is deliberate. The readings on it are not
evidence of anything, so a report that listed it as done would be saying the
site did something it did not do.
"""

from __future__ import annotations

import datetime as dt

from gemwalk.clock import Month, Quarter
from gemwalk.report.frame import Align, Column, Report, Table, number
from gemwalk.service.office import Office


def compliance_report(office: Office, site: str, quarter: Quarter) -> Report:
    """Build the quarterly compliance report for one site."""
    landfill = office.sites.sites.get(site)
    subpart = office.sites.standard_of(site)
    day = quarter.last_day
    report = Report(
        title=f"{landfill.name} compliance report",
        subtitle=f"{quarter} under {subpart.citation}, permit {landfill.permit}",
    )
    _monitoring_section(office, report, site, quarter)
    _surface_section(office, report, site, quarter)
    _records_section(office, report, site, day)
    _work_section(office, report, site, day)
    _instrument_section(office, report, site, day)
    _plant_section(office, report, site, quarter)
    return report


def _monitoring_section(office: Office, report: Report, site: str, quarter: Quarter) -> None:
    section = report.section("wellfield monitoring")
    first = Month.of(quarter.first_day)
    last = Month.of(quarter.last_day)
    missed = office.monitoring.months_missed(site, first, last)
    done = 0
    month = first
    while month <= last:
        done += len(office.monitoring.runs_in(site, month))
        month = month.next
    section.say(f"{done} monitoring runs in the quarter")
    if missed:
        section.say("no run at all in " + ", ".join(str(m) for m in missed))
    else:
        section.say("every month in the quarter was walked")
    short = Table(
        columns=(Column("run"), Column("started"), Column("unread", Align.RIGHT), Column("why")),
        title="runs closed with wellheads unread",
        empty="every run was finished",
    )
    for month_run in office.monitoring.runs.between(
        site, quarter.first_day.isoformat(), quarter.last_day.isoformat()
    ):
        if month_run.note:
            short.add(
                month_run.label,
                month_run.started_on,
                len(office.monitoring.missing(month_run.label)),
                month_run.note,
            )
    section.table(short)


def _surface_section(office: Office, report: Report, site: str, quarter: Quarter) -> None:
    section = report.section("surface monitoring")
    subpart = office.sites.standard_of(site)
    walks = office.surface.walks.in_quarter(site, quarter)
    table = Table(
        columns=(
            Column("walk"),
            Column("started"),
            Column("finished", blank="open"),
            Column("background", Align.RIGHT),
            Column("wind", Align.RIGHT),
            Column("gust", Align.RIGHT),
            Column("spacing", Align.RIGHT),
            Column("stands", blank="-"),
        ),
        empty="no walkover this quarter",
    )
    for walk in walks:
        faults = walk.faults(subpart)
        table.add(
            walk.label,
            walk.started_on,
            walk.finished_on,
            number(walk.background, 0),
            number(walk.wind_mean),
            number(walk.wind_gust),
            number(walk.spacing, 0),
            "yes" if not faults else "; ".join(faults),
        )
    section.table(table)
    missed = office.surface.quarters_missed(site, quarter, quarter)
    if missed:
        section.say("this quarter has no valid finished walkover on the record")
    hits = office.surface.hits.between_days(
        site, quarter.first_day.isoformat(), quarter.last_day.isoformat()
    )
    section.say(f"{len(hits)} spots over the limit")
    spots = Table(
        columns=(
            Column("spot"),
            Column("area"),
            Column("station"),
            Column("reading", Align.RIGHT),
            Column("found"),
            Column("step"),
            Column("attempt", Align.RIGHT),
            Column("due", blank="-"),
        ),
        title="spots found this quarter",
        empty="nothing over the limit",
    )
    for hit in hits:
        spots.add(
            hit.label,
            hit.area,
            hit.station,
            number(hit.reading, 0),
            hit.found_on,
            str(hit.step),
            hit.attempt,
            hit.due(subpart),
        )
    section.table(spots)


def _records_section(office: Office, report: Report, site: str, day: dt.date) -> None:
    section = report.section("records past their window")
    late = office.compliance.overdue(site, day)
    section.say(f"{len(late)} wellhead records past their window")
    table = Table(
        columns=(
            Column("record"),
            Column("well"),
            Column("kind"),
            Column("opened"),
            Column("stage"),
            Column("expected"),
            Column("due"),
            Column("days over", Align.RIGHT),
        ),
        empty="nothing past its window",
    )
    for standing in late:
        found = standing.exceedance
        table.add(
            found.label,
            found.device,
            str(found.kind),
            found.opened_on,
            str(found.stage),
            str(standing.expected),
            standing.due,
            -standing.days_left,
        )
    section.table(table)
    spots = Table(
        columns=(
            Column("spot"),
            Column("station"),
            Column("step"),
            Column("days over", Align.RIGHT),
        ),
        title="surface spots past their window",
        empty="nothing past its window",
    )
    for mark in office.surface.overdue(site, day):
        spots.add(mark.hit.label, mark.hit.station, str(mark.hit.step), -mark.days_left)
    section.table(spots)


def _work_section(office: Office, report: Report, site: str, day: dt.date) -> None:
    section = report.section("work")
    open_orders = office.work.orders.open_at(site)
    section.say(f"{len(open_orders)} work orders open")
    unhandled = office.work.unhandled(site, day)
    if unhandled:
        section.say("no order raised against " + ", ".join(unhandled))
    table = Table(
        columns=(
            Column("order"),
            Column("job"),
            Column("where"),
            Column("because", blank="-"),
            Column("due"),
            Column("days over", Align.RIGHT),
        ),
        title="orders past their date",
        empty="no order is late",
    )
    for ticket in office.work.overdue(site, day):
        order = ticket.order
        table.add(
            order.label,
            str(order.job),
            order.target,
            order.because,
            order.due_on,
            -ticket.days_left,
        )
    section.table(table)


def _instrument_section(office: Office, report: Report, site: str, day: dt.date) -> None:
    section = report.section("the instruments")
    table = Table(
        columns=(
            Column("meter"),
            Column("kind"),
            Column("serial"),
            Column("last calibrated", blank="never"),
            Column("drift", Align.RIGHT, blank="-"),
            Column("stands"),
        ),
        empty="no instrument on the books",
    )
    for meter in office.instruments.instruments.live(site):
        standing = office.instruments.standing(meter.label, day)
        check = standing.calibration
        table.add(
            meter.label,
            str(meter.kind),
            meter.serial,
            None if check is None else check.day,
            None if check is None else f"{check.drift:.1f}%",
            "yes" if standing.is_good else "no",
        )
    section.table(table)
    due = office.instruments.due(site, day)
    if due:
        section.say(
            "not calibrated for the last day of the quarter: " + ", ".join(m.label for m in due)
        )


def _plant_section(office: Office, report: Report, site: str, quarter: Quarter) -> None:
    section = report.section("the plant")
    subpart = office.sites.standard_of(site)
    table = Table(
        columns=(
            Column("device"),
            Column("kind"),
            Column("capacity", Align.RIGHT),
            Column("floor", Align.RIGHT, blank="-"),
        ),
        empty="no control device on the system",
    )
    for control in office.plant.controls.live(site):
        table.add(
            control.label,
            str(control.kind),
            number(control.capacity, 0),
            None if control.floor_degrees is None else number(control.floor_degrees, 0),
        )
    section.table(table)
    smoking = office.plant.smoking(site)
    if smoking:
        section.say(f"{len(smoking)} watches found more smoke than the rule allows")
        for watch in smoking:
            section.say(f"  {watch}")
    short = office.plant.unfinished_watches(site)
    if short:
        section.say(f"{len(short)} watches stopped before they could say anything")
    long = office.plant.long_outages(
        site, dt.datetime.combine(quarter.last_day, dt.time(23, 59), tzinfo=dt.UTC)
    )
    if long:
        section.say(
            f"{len(long)} outages ran past the {subpart.shutdown_days} day window: "
            + ", ".join(o.label for o in long)
        )


__all__ = ["compliance_report"]

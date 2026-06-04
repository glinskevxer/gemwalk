"""The annual report, which is the one that goes to the regulator.

It is a different document from the quarterly one and not a longer version of
it. The quarterly report is for the site, and it leads with what did not happen
so somebody can go and do it. The annual report is for a reader who was not
there, will not visit, and is deciding whether the site was operated the way it
said it would be. So it leads with the year's shape: how many wellheads were
read, how many findings that produced, how many of them were dealt with inside
the windows, and which ones were not.

The count that matters is the last one. A year with two hundred findings and
none late is a well run site. A year with four findings and two of them late is
not, and no total anywhere else on the page shows that.
"""

from __future__ import annotations

import datetime as dt

from gemwalk.clock import Month, Quarter
from gemwalk.model.exceedance import Exceedance
from gemwalk.report.frame import Align, Column, Report, Table, number, share
from gemwalk.report.preamble import headed
from gemwalk.rules import Finding
from gemwalk.service.office import Office


def annual_report(office: Office, site: str, year: int) -> Report:
    """Build the annual report for one site."""
    first = dt.date(year, 1, 1)
    last = dt.date(year, 12, 31)
    report, _ = headed(office, site, "annual report", str(year))
    _shape(office, report, site, year, first, last)
    _findings(office, report, site, first, last)
    _surface(office, report, site, year)
    _work(office, report, site, first, last)
    _field(office, report, site, last)
    return report


def _shape(
    office: Office, report: Report, site: str, year: int, first: dt.date, last: dt.date
) -> None:
    section = report.section("the year")
    runs = office.monitoring.runs.between(site, first.isoformat(), last.isoformat())
    readings = sum(len(office.monitoring.readings.of_run(run.label)) for run in runs)
    section.say(f"{len(runs)} monitoring runs, {readings} wellhead readings")
    missed = office.monitoring.months_missed(site, Month(year, 1), Month(year, 12))
    if missed:
        section.say("no run at all in " + ", ".join(str(month) for month in missed))
    else:
        section.say("every month of the year was walked")
    quarters = [Quarter(year, n) for n in (1, 2, 3, 4)]
    short = office.surface.quarters_missed(site, quarters[0], quarters[-1])
    if short:
        section.say("no valid surface walkover in " + ", ".join(str(q) for q in short))
    else:
        section.say("every quarter of the year was walked")


def _findings(office: Office, report: Report, site: str, first: dt.date, last: dt.date) -> None:
    section = report.section("what the wellheads produced")
    opened = office.compliance.exceedances.between_days(site, first.isoformat(), last.isoformat())
    section.say(f"{len(opened)} findings opened in the year")
    tally = Table(
        columns=(
            Column("kind"),
            Column("opened", Align.RIGHT, adds_up=True),
            Column("closed inside the window", Align.RIGHT, adds_up=True),
            Column("still open", Align.RIGHT, adds_up=True),
        ),
        empty="no finding was opened this year",
    )
    subpart = office.sites.standard_of(site)
    for kind in Finding:
        of_kind = [found for found in opened if found.kind is kind]
        if not of_kind:
            continue
        inside = sum(1 for found in of_kind if _closed_in_time(found, subpart.windows.correct))
        still = sum(1 for found in of_kind if found.is_open)
        tally.add(str(kind), len(of_kind), inside, still)
    section.table(tally)
    late = [
        found
        for found in opened
        if not found.is_open and not _closed_in_time(found, subpart.windows.action)
    ]
    section.say(f"{len(late)} findings took longer than the {subpart.windows.action} day window")
    listing = Table(
        columns=(
            Column("record"),
            Column("device"),
            Column("kind"),
            Column("opened"),
            Column("closed"),
            Column("days", Align.RIGHT),
        ),
        title="findings that ran past the second window",
        empty="every finding was closed inside its windows",
    )
    for found in late:
        listing.add(
            found.label,
            found.device,
            str(found.kind),
            found.opened_on,
            found.closed_on,
            (found.closed_on - found.opened_on).days if found.closed_on else None,
        )
    section.table(listing)


def _closed_in_time(found: Exceedance, days: int) -> bool:
    """True when a record was closed inside *days* of the reading that opened it."""
    if found.closed_on is None:
        return False
    return (found.closed_on - found.opened_on).days <= days


def _surface(office: Office, report: Report, site: str, year: int) -> None:
    section = report.section("what the cover produced")
    first = dt.date(year, 1, 1)
    last = dt.date(year, 12, 31)
    hits = office.surface.hits.between_days(site, first.isoformat(), last.isoformat())
    section.say(f"{len(hits)} spots over the limit")
    if hits:
        closed = [hit for hit in hits if not hit.is_open]
        section.say(f"{len(closed)} of them closed, {len(hits) - len(closed)} still open")
        second = [hit for hit in hits if hit.attempt > 1]
        section.say(f"{len(second)} needed more than one go at the cover")
    faults = office.surface.faults.between_days(site, first.isoformat(), last.isoformat())
    if faults:
        fixed = [fault for fault in faults if not fault.is_open]
        late = [
            fault
            for fault in faults
            if fault.fixed_on is not None
            and fault.fixed_on > fault.found_on + dt.timedelta(days=fault.window)
        ]
        section.say(
            f"{len(faults)} faults found on the cover, {len(fixed)} fixed, "
            f"{len(late)} of those after the date they carried"
        )
    else:
        section.say("nothing was found wrong with the cover")
    repeats = office.surface.repeat_stations(site, first)
    table = Table(
        columns=(Column("station"), Column("times marked", Align.RIGHT)),
        title="places marked more than once",
        empty="no place on the cover was marked twice",
    )
    for station, times in repeats.items():
        table.add(station, times)
    section.table(table)


def _work(office: Office, report: Report, site: str, first: dt.date, last: dt.date) -> None:
    section = report.section("the work")
    orders = office.work.orders.between_days(site, first.isoformat(), last.isoformat())
    done = [order for order in orders if not order.is_open]
    late = office.work.finished_late(site, first, last)
    section.say(f"{len(orders)} work orders raised, {len(done)} closed")
    if done:
        section.say(
            f"{len(late)} were finished after the date they carried, "
            f"which is {share(len(late) / len(done))} of the ones that closed"
        )


def _field(office: Office, report: Report, site: str, day: dt.date) -> None:
    section = report.section("the field at the end of the year")
    tally = office.wellfield.count_by_state(site)
    section.say(
        f"{tally['connected']} devices on the run, {tally['drilled']} waiting to be wired, "
        f"{tally['offline']} off the run, {tally['abandoned']} abandoned"
    )
    table = Table(
        columns=(
            Column("area"),
            Column("acres", Align.RIGHT),
            Column("devices", Align.RIGHT, adds_up=True),
            Column("wanted", Align.RIGHT, adds_up=True),
            Column("covered", Align.RIGHT),
            Column("collection due"),
        ),
        empty="no area on the books",
    )
    subpart = office.sites.standard_of(site)
    for read in office.wellfield.coverage_at(site):
        area = office.sites.areas.get(read.area)
        table.add(
            read.area,
            number(read.acres),
            len(read.devices),
            read.wanted,
            share(read.share),
            area.install_due(subpart),
        )
    section.table(table)
    short = office.wellfield.shortfalls(site, day)
    for shortfall in short:
        section.say(str(shortfall))


__all__ = ["annual_report"]

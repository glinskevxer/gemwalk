"""The monthly wellfield report: what was read, what it said, what it started.

This is the report the site manager actually reads, and it is built to be read
in one pass down the page. The wellheads that are fine are counted and not
listed. The wellheads that are not are listed with the number that put them
there and the limit it was measured against, because a report that says a well
is out of compliance without saying by how much is a report somebody has to go
and look things up for.
"""

from __future__ import annotations

import datetime as dt

from gemwalk.assess import Assessment
from gemwalk.clock import Month
from gemwalk.model.reading import Run
from gemwalk.report.frame import Align, Column, Report, Table, number, share
from gemwalk.service.office import Office

WELLHEAD_COLUMNS = (
    Column("well"),
    Column("methane", Align.RIGHT),
    Column("oxygen", Align.RIGHT),
    Column("balance", Align.RIGHT),
    Column("temp", Align.RIGHT),
    Column("gauge", Align.RIGHT),
    Column("flow", Align.RIGHT),
    Column("over", blank="-"),
)


def monthly_report(office: Office, site: str, month: Month, *, on: dt.date | None = None) -> Report:
    """Build the monthly wellfield report for one site."""
    day = on or month.last_day
    landfill = office.sites.sites.get(site)
    subpart = office.sites.standard_of(site)
    report = Report(
        title=f"{landfill.name} wellfield report",
        subtitle=f"{month} under {subpart.citation}, permit {landfill.permit}",
    )
    _site_section(office, report, site, day)
    runs = office.monitoring.runs_in(site, month)
    _runs_section(office, report, site, runs)
    _wellhead_section(office, report, runs)
    _findings_section(office, report, site, month, day)
    _liquids_section(office, report, site, day)
    return report


def _site_section(office: Office, report: Report, site: str, day: dt.date) -> None:
    section = report.section("the site")
    tally = office.wellfield.count_by_state(site)
    section.say(
        f"{tally['connected']} devices on the run, {tally['drilled']} drilled and not wired, "
        f"{tally['offline']} off the run, {tally['abandoned']} abandoned"
    )
    election = office.sites.election_of(site, day)
    if election.nitrogen_alternative:
        section.say("the site reads nitrogen against twenty percent, not oxygen against five")
    if election.higher_pressure:
        section.say("the site holds an approved alternative to the pressure standard")
    overdue = office.sites.overdue_areas(site, day)
    if overdue:
        section.say("collection is past due in " + ", ".join(area.label for area in overdue))
    for shortfall in office.wellfield.shortfalls(site, day):
        section.say(str(shortfall))


def _runs_section(office: Office, report: Report, site: str, runs: list[Run]) -> None:
    section = report.section("the runs")
    table = Table(
        columns=(
            Column("run"),
            Column("started"),
            Column("closed", blank="open"),
            Column("monitor"),
            Column("meter"),
            Column("read", Align.RIGHT),
            Column("unread", Align.RIGHT),
        ),
        empty="no monitoring run this month",
    )
    for pass_ in office.monitoring.runs.of_site(site):
        if pass_ not in runs:
            continue
        read = len(office.monitoring.readings.of_run(pass_.label))
        table.add(
            pass_.label,
            pass_.started_on,
            pass_.closed_on,
            pass_.monitor,
            pass_.meter,
            read,
            len(office.monitoring.missing(pass_.label)),
        )
    section.table(table)


def _wellhead_section(office: Office, report: Report, runs: list[Run]) -> None:
    section = report.section("the wellheads")
    table = Table(columns=WELLHEAD_COLUMNS, empty="no readings this month")
    clear = 0
    concerns = Table(
        columns=(Column("well"), Column("concern"), Column("what the water says", blank="-")),
        empty="nothing to look at twice",
    )
    for pass_ in runs:
        for assessment in office.monitoring.assessments(pass_.label):
            reading = office.monitoring.readings.on_run_for(pass_.label, assessment.device)
            if reading is None:
                continue
            if assessment.is_clear:
                clear += 1
            else:
                table.add(
                    assessment.device,
                    str(reading.methane_reading),
                    str(reading.oxygen_reading),
                    str(reading.nitrogen),
                    str(reading.wellhead_temperature),
                    str(reading.gauge),
                    str(reading.gas_flow),
                    ", ".join(str(kind) for kind in assessment.kinds),
                )
            _concerns(office, concerns, assessment)
    section.say(f"{clear} wellheads read clear")
    section.table(table)
    section.table(concerns)


def _concerns(office: Office, table: Table, assessment: Assessment) -> None:
    for concern in assessment.concerns:
        table.add(
            assessment.device,
            str(concern),
            office.liquids.explains(assessment.device, assessment.taken_on, (concern,)),
        )


def _findings_section(
    office: Office, report: Report, site: str, month: Month, day: dt.date
) -> None:
    section = report.section("the findings")
    opened = office.compliance.exceedances.between_days(
        site, month.first_day.isoformat(), month.last_day.isoformat()
    )
    section.say(f"{len(opened)} opened this month")
    table = Table(
        columns=(
            Column("record"),
            Column("well"),
            Column("kind"),
            Column("opened"),
            Column("reading", Align.RIGHT),
            Column("limit", Align.RIGHT),
            Column("stage"),
            Column("due"),
            Column("days", Align.RIGHT),
        ),
        title="still open",
        empty="nothing open",
    )
    for standing in office.compliance.board(site, day):
        found = standing.exceedance
        table.add(
            found.label,
            found.device,
            str(found.kind),
            found.opened_on,
            number(found.value),
            number(found.limit_value),
            str(found.stage),
            standing.due,
            standing.days_left,
        )
    section.table(table)


def _liquids_section(office: Office, report: Report, site: str, day: dt.date) -> None:
    section = report.section("liquids")
    wet = office.liquids.dewater_list(site, day)
    table = Table(
        columns=(
            Column("well"),
            Column("tape", Align.RIGHT),
            Column("column", Align.RIGHT),
            Column("screen under water", Align.RIGHT),
        ),
        empty="nothing standing high enough to pump",
    )
    for water in wet:
        table.add(
            water.device.label,
            number(water.level.depth),
            number(water.column),
            share(water.share),
        )
    section.table(table)


__all__ = ["monthly_report"]

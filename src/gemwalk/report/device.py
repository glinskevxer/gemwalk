"""The well card: everything the desk knows about one extraction device.

This is the report somebody prints before walking out to a wellhead, and it is
built so that the question "why is this well like this" can be answered from
one page. The construction is at the top because a screen from twenty two to
eighty six feet explains a great deal about a well that reads no flow. The
readings are next, oldest first, with the number that put each one out of
compliance marked, so a well that has been drifting hot for four months looks
different from one that went hot last week.

The point of the arrangement is that the water, the findings and the work all
sit under the same dates. A well that was flooded in June, read dead in June
and had a pump put in it in July is three records that only mean anything
together.
"""

from __future__ import annotations

import datetime as dt

from gemwalk.assess import assess
from gemwalk.clock import show_moment
from gemwalk.report.frame import Align, Column, Report, Table, number, share
from gemwalk.service.office import Office


def device_report(office: Office, label: str, *, on: dt.date | None = None) -> Report:
    """Build the well card for one device."""
    device = office.wellfield.devices.get(label)
    day = on or dt.date.today()  # noqa: DTZ011
    subpart = office.sites.standard_of(device.site)
    report = Report(
        title=f"{device.label} well card",
        subtitle=f"{device.site} area {device.area}, {device.kind}, {subpart.citation}",
    )
    del subpart
    _construction(office, report, label, day)
    _readings(office, report, label)
    _findings(office, report, label, day)
    _water(office, report, label)
    _work(office, report, label)
    _notes(office, report, label)
    return report


def _construction(office: Office, report: Report, label: str, day: dt.date) -> None:
    device = office.wellfield.devices.get(label)
    subpart = office.sites.standard_of(device.site)
    section = report.section("how it was built")
    section.say(f"station {device.station}")
    section.say(
        f"{number(device.total_depth)} ft of hole, screened from "
        f"{number(device.screen_top)} to {number(device.screen_bottom)} ft, "
        f"{number(device.screen_length)} ft of slot"
    )
    section.say(f"drilled {device.drilled_on}, state {device.state}")
    if device.connected_on is not None:
        section.say(f"wired up {device.connected_on} onto {device.lateral or 'no lateral'}")
    if device.offline_since is not None:
        section.say(
            f"off the run since {device.offline_since}, "
            f"{device.offline_days(day)} days of a {subpart.raising_days} day window"
        )
    limit = device.temperature_limit(subpart, day)
    if device.hov_approved is not None:
        section.say(f"held to {limit} by an approval dated {device.hov_approved}")
    else:
        section.say(f"held to the standard's {limit}")


def _readings(office: Office, report: Report, label: str) -> None:
    section = report.section("what it has read")
    device = office.wellfield.devices.get(label)
    subpart = office.sites.standard_of(device.site)
    table = Table(
        columns=(
            Column("day"),
            Column("run"),
            Column("CH4", Align.RIGHT),
            Column("CO2", Align.RIGHT),
            Column("O2", Align.RIGHT),
            Column("bal", Align.RIGHT),
            Column("temp", Align.RIGHT),
            Column("gauge", Align.RIGHT),
            Column("flow", Align.RIGHT),
            Column("valve", Align.RIGHT),
            Column("over", blank="-"),
        ),
        empty="this wellhead has never been read",
    )
    readings = office.monitoring.readings.of_device(label)
    for reading in readings:
        election = office.sites.election_of(device.site, reading.taken_on)
        result = assess(reading, device, subpart, election)
        table.add(
            reading.taken_on,
            reading.run,
            str(reading.methane_reading),
            f"{reading.carbon:.1f}%",
            str(reading.oxygen_reading),
            str(reading.nitrogen),
            str(reading.wellhead_temperature),
            str(reading.gauge),
            str(reading.gas_flow),
            f"{reading.valve_before:g}-{reading.valve_after:g}",
            ", ".join(str(kind) for kind in result.kinds) or None,
        )
    section.table(table)
    if len(readings) >= 2:
        first, last = readings[0], readings[-1]
        section.say(
            f"methane has gone from {first.methane_reading} to {last.methane_reading} "
            f"and flow from {first.gas_flow} to {last.gas_flow}"
        )


def _findings(office: Office, report: Report, label: str, day: dt.date) -> None:
    section = report.section("what it has been written up for")
    device = office.wellfield.devices.get(label)
    subpart = office.sites.standard_of(device.site)
    table = Table(
        columns=(
            Column("record"),
            Column("kind"),
            Column("opened"),
            Column("reading", Align.RIGHT),
            Column("limit", Align.RIGHT),
            Column("stage"),
            Column("due", blank="-"),
            Column("closed", blank="open"),
        ),
        empty="this wellhead has never been written up",
    )
    for found in office.compliance.exceedances.of_device(label):
        table.add(
            found.label,
            str(found.kind),
            found.opened_on,
            number(found.value),
            number(found.limit_value),
            str(found.stage),
            found.due(subpart),
            found.closed_on,
        )
    section.table(table)
    open_now = office.compliance.exceedances.open_on_device(label)
    if open_now:
        late = [f for f in open_now if f.is_late(subpart, day)]
        section.say(f"{len(open_now)} open, {len(late)} of them past their window")


def _water(office: Office, report: Report, label: str) -> None:
    section = report.section("what has been standing in it")
    device = office.wellfield.devices.get(label)
    table = Table(
        columns=(
            Column("day"),
            Column("tape", Align.RIGHT),
            Column("column", Align.RIGHT),
            Column("screen under water", Align.RIGHT),
            Column("pumped"),
        ),
        empty="no tape drop on file",
    )
    for level in office.liquids.levels.of_device(label):
        table.add(
            level.taken_on,
            number(level.depth),
            number(level.liquid_column(device)),
            share(level.submerged_share(device)),
            "yes" if level.pumped else "no",
        )
    section.table(table)


def _notes(office: Office, report: Report, label: str) -> None:
    section = report.section("what anybody wrote down about it")
    table = Table(
        columns=(Column("when"), Column("who"), Column("what they wrote")),
        empty="nobody has written anything down about it",
    )
    zone = office.sites.zone_of(office.wellfield.devices.get(label).site)
    for memo in office.memos.about(label):
        table.add(show_moment(memo.at, zone), memo.by_whom, memo.first_line)
    section.table(table)


def _work(office: Office, report: Report, label: str) -> None:
    section = report.section("who has been sent to it")
    table = Table(
        columns=(
            Column("order"),
            Column("job"),
            Column("raised"),
            Column("due"),
            Column("state"),
            Column("done", blank="-"),
            Column("because", blank="-"),
        ),
        empty="nobody has ever been sent to it",
    )
    for order in office.work.history(label):
        table.add(
            order.label,
            str(order.job),
            order.raised_on,
            order.due_on,
            str(order.state),
            order.done_on,
            order.because,
        )
    section.table(table)


__all__ = ["device_report"]

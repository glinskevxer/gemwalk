"""The morning page: everything with a date on it, on one sheet of paper.

The other reports answer questions about a period. This one answers the only
question anybody has at seven in the morning, which is what has to happen
today. So it is one page, it is ordered by how little time is left rather than
by what kind of record something is, and it says nothing at all about anything
that is not due.

Six different kinds of record end up on it and they have six different clocks.
That is exactly why it exists: a desk that keeps six boards keeps looking at
five of them.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from gemwalk.report.frame import Align, Column, Report, Table
from gemwalk.report.preamble import headed
from gemwalk.service.office import Office


@dataclass(frozen=True)
class Due:
    """One thing with a date on it, whatever kind of record it came off."""

    days_left: int
    due: dt.date
    kind: str
    label: str
    where: str
    said: str

    @property
    def late(self) -> bool:
        """True when the date has already gone by."""
        return self.days_left < 0

    def __str__(self) -> str:
        when = "late" if self.late else f"{self.days_left} days"
        return f"{self.due}  {when:>9}  {self.kind} {self.label} at {self.where}: {self.said}"


def everything_due(office: Office, site: str, on: dt.date) -> list[Due]:
    """Everything at a site with a date on it, the least time left first."""
    found: list[Due] = []
    for standing in office.compliance.board(site, on):
        record = standing.exceedance
        found.append(
            Due(
                standing.days_left,
                standing.due,
                "record",
                record.label,
                record.device,
                f"{record.kind} at the {record.stage} stage",
            )
        )
    for mark in office.surface.board(site, on):
        found.append(
            Due(
                mark.days_left,
                mark.due,
                "spot",
                mark.hit.label,
                mark.hit.station,
                f"waiting on a {mark.hit.step}, attempt {mark.hit.attempt}",
            )
        )
    for fault in office.surface.open_faults(site, on):
        left = fault.days_left(on)
        if left is not None and fault.due is not None:
            found.append(Due(left, fault.due, "fault", fault.label, fault.station, str(fault.kind)))
    for ticket in office.work.board(site, on):
        order = ticket.order
        found.append(
            Due(
                ticket.days_left,
                order.due_on,
                "order",
                order.label,
                order.target,
                f"{order.job}, {order.crew or 'nobody assigned'}",
            )
        )
    return sorted(found, key=lambda due: (due.days_left, due.kind, due.label))


def board_report(office: Office, site: str, on: dt.date) -> Report:
    """Build the morning page for one site."""
    report, subpart = headed(office, site, "board", str(on))
    due = everything_due(office, site, on)
    late = [entry for entry in due if entry.late]
    section = report.section("what is due")
    section.say(f"{len(due)} things with a date on them, {len(late)} of them late")
    table = Table(
        columns=(
            Column("due"),
            Column("days", Align.RIGHT),
            Column("kind"),
            Column("record"),
            Column("where"),
            Column("what"),
        ),
        empty="nothing is due",
    )
    for entry in due:
        table.add(
            entry.due,
            entry.days_left,
            entry.kind,
            entry.label,
            entry.where,
            entry.said,
        )
    section.table(table)

    waiting = report.section("nobody has been sent to")
    unhandled = office.work.unhandled(site, on)
    if unhandled:
        waiting.say(", ".join(unhandled))
    else:
        waiting.say("every open record has an order against it")

    tools = report.section("before anybody goes out")
    meters = office.instruments.due(site, on)
    if meters:
        tools.say("not calibrated for today: " + ", ".join(m.label for m in meters))
    else:
        tools.say("every meter in service is calibrated for today")
    down = office.plant.down_now(site)
    if down:
        tools.say("down: " + ", ".join(f"{o.control} ({o.reason})" for o in down))
    long = office.plant.long_outages(site, dt.datetime.combine(on, dt.time(23, 59), tzinfo=dt.UTC))
    if long:
        tools.say(
            f"past the {subpart.shutdown_days} day window: " + ", ".join(o.label for o in long)
        )
    offline = office.wellfield.overdue_offline(site, on)
    if offline:
        tools.say("off the run too long: " + ", ".join(d.label for d in offline))
    return report


__all__ = ["Due", "board_report", "everything_due"]

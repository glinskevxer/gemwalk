"""Commands for the compliance clocks and the work orders raised off them."""

from __future__ import annotations

import datetime as dt

import click

from gemwalk.cli.support import DAY, Ledger, line, pass_ledger, rows
from gemwalk.model.work import Job


@click.group()
def record() -> None:
    """The exceedance clocks: what is open, what is late, what closed them."""


@record.command("board")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to measure against")
@pass_ledger
def record_board(ledger: Ledger, site: str, on: dt.date) -> None:
    """List every open record, the least time left first."""
    board = ledger.office.compliance.board(site, on)
    if not board:
        line("nothing open")
        return
    rows(
        ("record", "well", "kind", "opened", "stage", "expected", "due", "days", ""),
        [
            (
                s.exceedance.label,
                s.exceedance.device,
                str(s.exceedance.kind),
                str(s.exceedance.opened_on),
                str(s.exceedance.stage),
                str(s.expected),
                str(s.due),
                str(s.days_left),
                "late" if s.late else "",
            )
            for s in board
        ],
    )


@record.command("late")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to measure against")
@pass_ledger
def record_late(ledger: Ledger, site: str, on: dt.date) -> None:
    """List only the records whose window has already run out."""
    late = ledger.office.compliance.overdue(site, on)
    line(f"{len(late)} records past their window")
    for standing in late:
        found = standing.exceedance
        line(f"  {found.label}  {found.device}  {found.kind}  {-standing.days_left} days over")


@record.command("show")
@click.argument("label")
@pass_ledger
def record_show(ledger: Ledger, label: str) -> None:
    """Show one record and every recheck taken against it."""
    desk = ledger.office.compliance
    found = desk.exceedances.get(label)
    subpart = ledger.office.sites.standard_of(found.site)
    line(f"{found.label}  {found.device}  {found.kind}")
    line(f"  opened {found.opened_on} at {found.value:g} against a limit of {found.limit_value:g}")
    line(f"  stage {found.stage}, due {found.due(subpart) or 'closed'}")
    if found.closed_on is not None:
        line(f"  closed {found.closed_on}")
    walked = desk.rechecks.of_exceedance(label)
    if not walked:
        line("  no recheck yet")
        return
    for check in walked:
        verdict = "under" if check.clear else "still over"
        line(f"  {check.taken_on}  {check.value:g}  {verdict}  at the {check.stage} stage")


@record.command("recheck")
@click.argument("label")
@click.argument("value", type=float)
@click.option("--on", type=DAY, required=True, help="the day of the field visit")
@click.option("--clear/--still-over", required=True, help="did it come back under the limit")
@click.option("--note", default="", help="what the crew did")
@pass_ledger
def record_recheck(
    ledger: Ledger, label: str, value: float, on: dt.date, clear: bool, note: str
) -> None:
    """Record a field visit against an open record, off a run."""
    after = ledger.office.compliance.recheck(label, on, value, clear=clear, note=note)
    if after.is_open:
        line(f"{after.label} still open at the {after.stage} stage")
    else:
        line(f"{after.label} closed on {after.closed_on}")


@record.command("catch-up")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to move the records to")
@pass_ledger
def record_catch_up(ledger: Ledger, site: str, on: dt.date) -> None:
    """Move every open record to the stage the calendar has reached."""
    moved = ledger.office.compliance.catch_up(site, on)
    if not moved:
        line("every record is at the stage the calendar says")
        return
    line("moved on a stage: " + ", ".join(moved))


@record.command("kinds")
@click.argument("site")
@pass_ledger
def record_kinds(ledger: Ledger, site: str) -> None:
    """Count the open records by what kind of reading opened them."""
    tally = ledger.office.compliance.open_kinds(site)
    rows(("kind", "open"), [(kind, str(count)) for kind, count in tally.items()])


@click.group()
def work() -> None:
    """The jobs the field crew is handed."""


@work.command("raise")
@click.argument("site")
@click.argument("target")
@click.option(
    "--job",
    type=click.Choice([j.name.lower() for j in Job]),
    required=True,
    help="what the crew is being sent to do",
)
@click.option("--on", type=DAY, required=True, help="the day the order was written")
@click.option("--due", type=DAY, required=True, help="the day it has to be done by")
@click.option("--note", default="", help="anything the crew needs to know")
@pass_ledger
def work_raise(
    ledger: Ledger, site: str, target: str, job: str, on: dt.date, due: dt.date, note: str
) -> None:
    """Write a job the desk decided on."""
    order = ledger.office.work.raise_order(
        site, Job[job.upper()], target, on=on, due=due, note=note
    )
    line(f"{order.label} raised, due {order.due_on}")


@work.command("from")
@click.argument("label")
@click.option(
    "--job",
    type=click.Choice([j.name.lower() for j in Job]),
    required=True,
    help="what the crew is being sent to do",
)
@click.option("--on", type=DAY, required=True, help="the day the order was written")
@click.option("--note", default="", help="anything the crew needs to know")
@pass_ledger
def work_from(ledger: Ledger, label: str, job: str, on: dt.date, note: str) -> None:
    """Write a job off a compliance record, on that record's own deadline."""
    desk = ledger.office.work
    chosen = Job[job.upper()]
    if desk.compliance.exceedances.find(label) is not None:
        order = desk.raise_for_exceedance(label, chosen, on, note)
    else:
        order = desk.raise_for_hit(label, chosen, on, note)
    line(f"{order.label} raised off {label}, due {order.due_on}")


@work.command("assign")
@click.argument("label")
@click.argument("crew")
@click.option("--on", type=DAY, required=True, help="the day it was handed out")
@pass_ledger
def work_assign(ledger: Ledger, label: str, crew: str, on: dt.date) -> None:
    """Hand an order to a crew."""
    order = ledger.office.work.assign(label, crew, on)
    line(f"{order.label} with {order.crew}")


@work.command("done")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day the job was finished")
@click.option("--note", default="", help="what was actually done")
@pass_ledger
def work_done(ledger: Ledger, label: str, on: dt.date, note: str) -> None:
    """Record an order as done."""
    order = ledger.office.work.finish(label, on, note)
    late = " after its date" if order.was_late() else ""
    line(f"{order.label} finished on {order.done_on}{late}")


@work.command("cancel")
@click.argument("label")
@click.argument("why")
@click.option("--on", type=DAY, required=True, help="the day it was called off")
@pass_ledger
def work_cancel(ledger: Ledger, label: str, why: str, on: dt.date) -> None:
    """Call an order off, with a reason."""
    order = ledger.office.work.cancel(label, on, why)
    line(f"{order.label} cancelled: {order.note}")


@work.command("board")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to measure against")
@pass_ledger
def work_board(ledger: Ledger, site: str, on: dt.date) -> None:
    """List every open order, the least time left first."""
    board = ledger.office.work.board(site, on)
    if not board:
        line("no open orders")
        return
    rows(
        ("order", "job", "where", "because", "crew", "due", "days", ""),
        [
            (
                t.order.label,
                str(t.order.job),
                t.order.target,
                t.order.because or "-",
                t.order.crew or "-",
                str(t.order.due_on),
                str(t.days_left),
                "late" if t.late else "",
            )
            for t in board
        ],
    )


@work.command("unhandled")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to measure against")
@pass_ledger
def work_unhandled(ledger: Ledger, site: str, on: dt.date) -> None:
    """Name every open record with nobody sent to it."""
    waiting = ledger.office.work.unhandled(site, on)
    if not waiting:
        line("every open record has an order against it")
        return
    line("nobody sent to " + ", ".join(waiting))


@work.command("crews")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to measure against")
@pass_ledger
def work_crews(ledger: Ledger, site: str, on: dt.date) -> None:
    """Say how many open orders each crew is carrying."""
    load = ledger.office.work.crew_load(site, on)
    if not load:
        line("nothing is assigned")
        return
    rows(("crew", "open"), [(crew, str(count)) for crew, count in load.items()])


__all__ = ["record", "work"]

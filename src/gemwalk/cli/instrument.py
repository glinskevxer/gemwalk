"""Commands for the meters and the calibrations behind every reading."""

from __future__ import annotations

import datetime as dt

import click

from gemwalk.cli.support import DAY, Ledger, line, moment_at, pass_ledger, rows
from gemwalk.model.instrument import Meter


@click.group()
def meter() -> None:
    """The instruments, their calibrations, and whether they were fit to use."""


@meter.command("add")
@click.argument("label")
@click.argument("site")
@click.option(
    "--kind",
    type=click.Choice([k.name.lower() for k in Meter]),
    required=True,
    help="what kind of instrument it is",
)
@click.option("--maker", required=True, help="who made it")
@click.option("--model", required=True, help="the model name")
@click.option("--serial", required=True, help="the serial number")
@click.option("--on", type=DAY, required=True, help="the day it went into service")
@pass_ledger
def meter_add(
    ledger: Ledger,
    label: str,
    site: str,
    kind: str,
    maker: str,
    model: str,
    serial: str,
    on: dt.date,
) -> None:
    """Put a meter in the book."""
    made = ledger.office.instruments.add(
        label,
        site,
        kind=Meter[kind.upper()],
        maker=maker,
        model=model,
        serial=serial,
        on=on,
    )
    line(
        f"{made.label} in service as a {made.kind}, "
        f"a calibration stands for {made.kind.good_for_days} day(s)"
    )


@meter.command("retire")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day it came out of service")
@pass_ledger
def meter_retire(ledger: Ledger, label: str, on: dt.date) -> None:
    """Take a meter out of service."""
    retired = ledger.office.instruments.retire(label, on)
    line(f"{retired.label} out of service on {retired.retired_on}")


@meter.command("calibrate")
@click.argument("label")
@click.argument("at")
@click.option("--standard", required=True, help="what is on the bottle")
@click.option("--expected", type=float, required=True, help="what the bottle says it is")
@click.option("--before", type=float, required=True, help="what the meter read as found")
@click.option("--after", type=float, required=True, help="what it read once adjusted")
@click.option("--by", "by_whom", required=True, help="who did it")
@click.option("--note", default="", help="anything worth writing down")
@pass_ledger
def meter_calibrate(
    ledger: Ledger,
    label: str,
    at: str,
    standard: str,
    expected: float,
    before: float,
    after: float,
    by_whom: str,
    note: str,
) -> None:
    """Write down a calibration of one meter."""
    found = ledger.office.instruments.instruments.get(label)
    moment = moment_at(ledger, found.site, at)
    check = ledger.office.instruments.calibrate(
        label,
        moment,
        standard=standard,
        expected=expected,
        before=before,
        after=after,
        by_whom=by_whom,
        note=note,
    )
    line(f"{label} drift {check.drift:.1f}%, error after {check.error:.1f}%")
    if not check.passed:
        line("  it did not pass, so it is not fit to use")
    elif check.drifted:
        line("  it passed, but the readings taken since the last check are in doubt")


@meter.command("standing")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day to ask about")
@pass_ledger
def meter_standing(ledger: Ledger, label: str, on: dt.date) -> None:
    """Say whether a meter was fit to use on one day, and why."""
    standing = ledger.office.instruments.standing(label, on)
    line(str(standing))
    line("fit to use" if standing.is_good else "not fit to use")


@meter.command("due")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to ask about")
@pass_ledger
def meter_due(ledger: Ledger, site: str, on: dt.date) -> None:
    """List the meters in service whose calibration does not cover a day."""
    due = ledger.office.instruments.due(site, on)
    if not due:
        line("every meter in service is calibrated for that day")
        return
    for found in due:
        line(f"{found.label}  {found.kind}  {ledger.office.instruments.standing(found.label, on)}")


@meter.command("history")
@click.argument("label")
@pass_ledger
def meter_history(ledger: Ledger, label: str) -> None:
    """List every calibration of one meter, oldest first."""
    history = ledger.office.instruments.history(label)
    if not history:
        line(f"{label} has never been calibrated")
        return
    rows(
        ("day", "standard", "expected", "before", "after", "drift", "error", "by", ""),
        [
            (
                str(check.day),
                check.standard,
                f"{check.expected:g}",
                f"{check.before:g}",
                f"{check.after:g}",
                f"{check.drift:.1f}%",
                f"{check.error:.1f}%",
                check.by_whom,
                "failed" if not check.passed else ("drifted" if check.drifted else ""),
            )
            for check in history
        ],
    )


@meter.command("day")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day to list")
@pass_ledger
def meter_day(ledger: Ledger, label: str, on: dt.date) -> None:
    """List every calibration of one meter on one day."""
    checks = ledger.office.instruments.used_on(label, on)
    line(f"{len(checks)} calibrations on {on}")
    for check in checks:
        line(
            f"  {check.at.time().isoformat(timespec='minutes')} utc  "
            f"drift {check.drift:.1f}%  error {check.error:.1f}%  {check.by_whom}"
        )


__all__ = ["meter"]

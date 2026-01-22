"""Commands that print the paperwork."""

from __future__ import annotations

import datetime as dt

import click

from gemwalk.cli.support import DAY, Ledger, line, pass_ledger, show
from gemwalk.clock import Month, Quarter
from gemwalk.nmoc import Inputs, needed, rate
from gemwalk.report.annual import annual_report
from gemwalk.report.compliance import compliance_report
from gemwalk.report.device import device_report
from gemwalk.report.monthly import monthly_report


@click.group()
def report() -> None:
    """The paperwork: monthly, quarterly, and the emission rate."""


@report.command("month")
@click.argument("site")
@click.argument("month")
@click.option("--on", type=DAY, default=None, help="the day to measure deadlines against")
@pass_ledger
def report_month(ledger: Ledger, site: str, month: str, on: dt.date | None) -> None:
    """Print the monthly wellfield report."""
    show(monthly_report(ledger.office, site, Month.parse(month), on=on))


@report.command("quarter")
@click.argument("site")
@click.argument("quarter")
@pass_ledger
def report_quarter(ledger: Ledger, site: str, quarter: str) -> None:
    """Print the quarterly compliance report."""
    show(compliance_report(ledger.office, site, Quarter.parse(quarter)))


@report.command("year")
@click.argument("site")
@click.argument("year", type=int)
@pass_ledger
def report_year(ledger: Ledger, site: str, year: int) -> None:
    """Print the annual report."""
    show(annual_report(ledger.office, site, year))


@report.command("device")
@click.argument("label")
@click.option("--on", type=DAY, default=None, help="the day to measure windows against")
@pass_ledger
def report_device(ledger: Ledger, label: str, on: dt.date | None) -> None:
    """Print the well card for one device."""
    show(device_report(ledger.office, label, on=on))


@report.command("rate")
@click.argument("site")
@click.option("--acceptance", type=float, required=True, help="average tonnes a year")
@click.option("--age", type=float, required=True, help="years since the first load")
@click.option("--closed", type=float, default=0.0, help="years since the site closed")
@click.option("--arid/--wet", default=False, help="use the dry climate rate constant")
@click.option("--nmoc", type=float, default=None, help="a measured concentration, in ppmv")
@click.option("--constant", type=float, default=None, help="a measured rate constant")
@pass_ledger
def report_rate(
    ledger: Ledger,
    site: str,
    acceptance: float,
    age: float,
    closed: float,
    arid: bool,
    nmoc: float | None,
    constant: float | None,
) -> None:
    """Work out the emission rate and say whether collection is required."""
    from gemwalk.nmoc import DEFAULT_ARID_K, DEFAULT_K

    landfill = ledger.office.sites.sites.get(site)
    subpart = ledger.office.sites.standard_of(site)
    inputs = Inputs(
        acceptance=acceptance,
        age=age,
        closed_years=closed,
        rate_constant=DEFAULT_ARID_K if arid else DEFAULT_K,
    )
    if nmoc is not None:
        inputs = inputs.measure_concentration(nmoc)
    if constant is not None:
        inputs = inputs.measure_rate(constant)
    estimate = rate(inputs)
    line(f"{estimate.tier}: {estimate.megagrams:,.1f} Mg a year of non methane organics")
    line(f"  threshold under {subpart.citation} is {subpart.nmoc_threshold_mg:g} Mg a year")
    line(
        f"  design capacity {landfill.design_capacity:,.0f} Mg against "
        f"{subpart.design_capacity_mg:,.0f} Mg"
    )
    if needed(estimate, subpart, landfill.design_capacity):
        line("  a collection and control system is required")
    elif estimate.over(subpart):
        line("  over the emission threshold but under the design capacity, so not required")
    else:
        line("  under the emission threshold, so not required")


@report.command("due")
@click.argument("site")
@click.option("--on", type=DAY, required=True, help="the day to measure against")
@pass_ledger
def report_due(ledger: Ledger, site: str, on: dt.date) -> None:
    """Print everything with a date on it, soonest first."""
    office = ledger.office
    entries: list[tuple[int, str, str]] = []
    for standing in office.compliance.board(site, on):
        entries.append(
            (
                standing.days_left,
                str(standing.due),
                f"{standing.exceedance.label} "
                f"{standing.exceedance.device} {standing.exceedance.kind} at the "
                f"{standing.exceedance.stage} stage",
            )
        )
    for mark in office.surface.board(site, on):
        entries.append(
            (
                mark.days_left,
                str(mark.due),
                f"{mark.hit.label} {mark.hit.station} waiting on a {mark.hit.step}",
            )
        )
    for ticket in office.work.board(site, on):
        entries.append(
            (
                ticket.days_left,
                str(ticket.order.due_on),
                f"{ticket.order.label} {ticket.order.job} at {ticket.order.target}",
            )
        )
    if not entries:
        line("nothing is due")
        return
    for days, due, what in sorted(entries):
        left = "late" if days < 0 else f"{days} days"
        line(f"{due}  {left:>9}  {what}")


__all__ = ["report"]

"""Commands for the landfill itself and the ground inside its fence."""

from __future__ import annotations

import datetime as dt

import click

from gemwalk.cli.support import DAY, Ledger, line, pass_ledger, rows
from gemwalk.model.landfill import Cover
from gemwalk.rules import codes


@click.group()
def site() -> None:
    """Sites, the areas in them, and what each site has elected."""


@site.command("open")
@click.argument("label")
@click.argument("name")
@click.option("--subpart", type=click.Choice(codes()), required=True, help="the standard")
@click.option("--permit", required=True, help="the state permit number")
@click.option("--zone", required=True, help="the site's own wall clock, as a zone name")
@click.option("--capacity", type=float, required=True, help="design capacity in megagrams")
@click.option("--opened", type=DAY, required=True, help="the day the site took its first load")
@pass_ledger
def site_open(
    ledger: Ledger,
    label: str,
    name: str,
    subpart: str,
    permit: str,
    zone: str,
    capacity: float,
    opened: dt.date,
) -> None:
    """Put a landfill in the book."""
    made = ledger.office.sites.open_site(
        label,
        name,
        subpart=subpart,
        permit=permit,
        zone=zone,
        design_capacity=capacity,
        opened_on=opened,
    )
    line(f"{made.label} opened under subpart {made.standard}, permit {made.permit}")


@site.command("list")
@pass_ledger
def site_list(ledger: Ledger) -> None:
    """List every site in the book."""
    rows(
        ("site", "standard", "permit", "opened", "closed"),
        [
            (s.label, s.standard, s.permit, str(s.opened_on), str(s.closed_on or "open"))
            for s in ledger.office.sites.sites.all()
        ],
    )


@site.command("show")
@click.argument("label")
@click.option("--on", type=DAY, default=None, help="the day to read the election as of")
@pass_ledger
def site_show(ledger: Ledger, label: str, on: dt.date | None) -> None:
    """Show one site, its standard and what it has elected."""
    desk = ledger.office.sites
    found = desk.sites.get(label)
    subpart = desk.standard_of(label)
    election = desk.election_of(label, on)
    line(f"{found.label}  {found.name}")
    line(f"  {subpart.citation}, permit {found.permit}")
    line(f"  clock {found.zone}, capacity {found.design_capacity:,.0f} Mg")
    shut = f"closed {found.closed_on}" if found.is_closed else "open"
    line(f"  opened {found.opened_on}, {shut}")
    line(f"  nitrogen alternative: {'yes' if election.nitrogen_alternative else 'no'}")
    line(f"  pressure alternative: {'yes' if election.higher_pressure else 'no'}")


@site.command("close")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day the last load went in")
@pass_ledger
def site_close(ledger: Ledger, label: str, on: dt.date) -> None:
    """Record a site as having taken its last load."""
    closed = ledger.office.sites.close_site(label, on)
    line(f"{closed.label} closed on {closed.closed_on}")


@site.command("elect")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day the election was made")
@click.option("--nitrogen/--no-nitrogen", default=False, help="read nitrogen instead of oxygen")
@click.option("--pressure/--no-pressure", default=False, help="an approved pressure alternative")
@pass_ledger
def site_elect(ledger: Ledger, label: str, on: dt.date, nitrogen: bool, pressure: bool) -> None:
    """Record what a site has chosen where its standard leaves a choice."""
    ledger.office.sites.elect(label, on, nitrogen_alternative=nitrogen, higher_pressure=pressure)
    line(f"{label} election recorded as of {on}")


@site.command("area")
@click.argument("label")
@click.argument("parent")
@click.argument("name")
@click.option("--acres", type=float, required=True, help="how much ground the area covers")
@click.option("--first-waste", type=DAY, required=True, help="the day the first load went in")
@pass_ledger
def site_area(
    ledger: Ledger, label: str, parent: str, name: str, acres: float, first_waste: dt.date
) -> None:
    """Cut a filling area into a site."""
    made = ledger.office.sites.add_area(label, parent, name, acres=acres, first_waste=first_waste)
    subpart = ledger.office.sites.standard_of(parent)
    line(f"{made.label} added, collection due by {made.install_due(subpart)}")


@site.command("areas")
@click.argument("parent")
@click.option("--on", type=DAY, default=None, help="the day to measure deadlines against")
@pass_ledger
def site_areas(ledger: Ledger, parent: str, on: dt.date | None) -> None:
    """List the areas of a site with their collection deadlines."""
    desk = ledger.office.sites
    subpart = desk.standard_of(parent)
    day = on or dt.date.today()  # noqa: DTZ011
    body: list[tuple[str, ...]] = []
    for area in desk.areas_of(parent):
        due = area.install_due(subpart)
        body.append(
            (
                area.label,
                area.name,
                str(area.first_waste),
                str(area.last_waste or "filling"),
                str(area.cover),
                str(due),
                "overdue" if due < day else "",
            )
        )
    rows(("area", "name", "first waste", "last waste", "cover", "due", ""), body)


@site.command("stop")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day the last load went in")
@pass_ledger
def site_stop(ledger: Ledger, label: str, on: dt.date) -> None:
    """Record an area as having taken its last load."""
    area = ledger.office.sites.stop_filling(label, on)
    line(f"{area.label} stopped taking waste on {area.last_waste}")


@site.command("cap")
@click.argument("label")
@click.option("--on", type=DAY, required=True, help="the day final cover went on")
@click.option(
    "--cover",
    type=click.Choice([c.value for c in Cover]),
    default=Cover.FINAL.value,
    help="what went on top",
)
@pass_ledger
def site_cap(ledger: Ledger, label: str, on: dt.date, cover: str) -> None:
    """Record final cover on an area and shut it."""
    area = ledger.office.sites.close_area(label, on, Cover(cover))
    subpart = ledger.office.sites.standard_of(area.site)
    line(f"{area.label} closed under {area.cover}, collection due by {area.install_due(subpart)}")


__all__ = ["site"]

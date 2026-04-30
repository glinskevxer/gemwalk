"""Reading a book for the things that are true of it and should not be.

Sqlite will hold a book together. It will not tell anybody that a wellhead has
readings from before it was wired up, or that a work order points at a record
that was closed two years ago, because neither of those breaks a foreign key.
They break the story, and the story is what somebody has to defend.

Everything here is a finding about the data rather than about the file, which
is what separates it from the maintenance check. A damaged file is a disaster
and a book full of these is an ordinary Tuesday: they accumulate from typing,
from importing old paper records, and from people fixing one thing without
noticing what pointed at it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from gemwalk.model.device import State
from gemwalk.service.office import Office


class Weight(Enum):
    """How much a finding matters."""

    SERIOUS = "serious"
    ODD = "odd"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Finding:
    """One thing about a book that should not be true of it."""

    weight: Weight
    about: str
    said: str

    def __str__(self) -> str:
        return f"{self.weight}: {self.about}: {self.said}"


def _piping(office: Office, site: str) -> list[Finding]:
    found: list[Finding] = []
    for device in office.wellfield.devices.monitored(site):
        if device.lateral is None:
            found.append(
                Finding(
                    Weight.SERIOUS,
                    device.label,
                    "on the run and piped to nothing, so it is being pulled through no pipe",
                )
            )
    return found


def _readings(office: Office, site: str) -> list[Finding]:
    found: list[Finding] = []
    for device in office.wellfield.devices.of_site(site):
        for reading in office.monitoring.readings.of_device(device.label):
            if reading.taken_on < device.drilled_on:
                found.append(
                    Finding(
                        Weight.SERIOUS,
                        device.label,
                        f"read on {reading.taken_on}, before it was drilled on {device.drilled_on}",
                    )
                )
            elif device.connected_on is not None and reading.taken_on < device.connected_on:
                found.append(
                    Finding(
                        Weight.ODD,
                        device.label,
                        f"read on {reading.taken_on}, before it was wired up on "
                        f"{device.connected_on}",
                    )
                )
    return found


def _levels(office: Office, site: str) -> list[Finding]:
    found: list[Finding] = []
    for device in office.wellfield.devices.of_site(site):
        for level in office.liquids.levels.of_device(device.label):
            if level.depth > device.total_depth:
                found.append(
                    Finding(
                        Weight.SERIOUS,
                        device.label,
                        f"taped to {level.depth:g} ft on {level.taken_on}, below the bottom "
                        f"of a {device.total_depth:g} ft hole",
                    )
                )
    return found


def _records(office: Office, site: str) -> list[Finding]:
    found: list[Finding] = []
    for record in office.compliance.exceedances.open_at(site):
        device = office.wellfield.devices.find(record.device)
        if device is None:
            found.append(Finding(Weight.SERIOUS, record.label, "open against no device"))
        elif device.state is State.ABANDONED:
            found.append(
                Finding(
                    Weight.SERIOUS,
                    record.label,
                    f"open against {device.label}, which was abandoned on {device.abandoned_on}",
                )
            )
    return found


def _orders(office: Office, site: str) -> list[Finding]:
    found: list[Finding] = []
    for order in office.work.orders.open_at(site):
        if order.because is None:
            continue
        record = office.compliance.exceedances.find(order.because)
        hit = office.surface.hits.find(order.because)
        if record is None and hit is None:
            found.append(
                Finding(Weight.SERIOUS, order.label, f"raised off {order.because}, which is gone")
            )
        elif record is not None and not record.is_open:
            found.append(
                Finding(
                    Weight.ODD,
                    order.label,
                    f"still open against {record.label}, which closed on {record.closed_on}",
                )
            )
    return found


def _shape(office: Office, site: str) -> list[Finding]:
    found: list[Finding] = []
    if not office.sites.areas_of(site):
        found.append(Finding(Weight.ODD, site, "has no filling areas in it"))
    if not office.wellfield.devices.of_site(site):
        found.append(Finding(Weight.ODD, site, "has no devices in the ground"))
    if not office.plant.controls.live(site):
        found.append(Finding(Weight.SERIOUS, site, "has nothing to burn the gas"))
    for pass_ in office.monitoring.runs.open_runs(site):
        found.append(Finding(Weight.ODD, pass_.label, f"still open since {pass_.started_on}"))
    for walk in office.surface.walks.open_walks(site):
        found.append(Finding(Weight.ODD, walk.label, f"still open since {walk.started_on}"))
    return found


def review(office: Office, site: str) -> list[Finding]:
    """Read one site's records for everything that should not be true of them."""
    office.sites.sites.get(site)
    found: list[Finding] = []
    for reader in (_shape, _piping, _readings, _levels, _records, _orders):
        found.extend(reader(office, site))
    order = {Weight.SERIOUS: 0, Weight.ODD: 1}
    return sorted(found, key=lambda f: (order[f.weight], f.about, f.said))


def serious(office: Office, site: str) -> list[Finding]:
    """Only the findings that mean the records cannot be defended."""
    return [found for found in review(office, site) if found.weight is Weight.SERIOUS]


__all__ = ["Finding", "Weight", "review", "serious"]

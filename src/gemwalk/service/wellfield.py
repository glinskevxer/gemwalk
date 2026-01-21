"""Drilling a device, wiring it up, taking it off the run and giving it up.

The desk is what a person actually does. It hands out the label, checks the
device is going into an area that exists at a site that exists, refuses a
device drilled before its area took any waste, and writes the state changes
back through one transaction each.

It is also where the roster comes from: the list of devices the crew is
expected to read this month, which is not the same as the list of devices in
the ground.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace

from gemwalk.design import Coverage, coverage
from gemwalk.errors import RuleError, StateError
from gemwalk.ids import Labels
from gemwalk.model.device import Device, Kind, State
from gemwalk.model.landfill import Area
from gemwalk.model.rework import Job, Rework
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book
from gemwalk.store.devices import DeviceRepository
from gemwalk.store.rework import ReworkRepository
from gemwalk.units import Temperature


@dataclass(frozen=True)
class Shortfall:
    """One area that is short of devices, and how long it has to fix that."""

    coverage: Coverage
    due: dt.date
    overdue: bool

    def __str__(self) -> str:
        when = "overdue since" if self.overdue else "due"
        return f"{self.coverage}, {self.coverage.short_by} more {when} {self.due}"


class WellfieldDesk:
    """The devices in the ground and what state each of them is in."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.devices = DeviceRepository(book)
        self.rework = ReworkRepository(book)
        self.sites = SiteDesk(book)
        self.labels = Labels(book)

    def drill(
        self,
        site: str,
        area: str,
        *,
        kind: Kind = Kind.VERTICAL,
        station: str,
        total_depth: float,
        screen_top: float,
        screen_bottom: float,
        on: dt.date,
        label: str | None = None,
        influence: float | None = None,
    ) -> Device:
        """Put a new device in the ground and hand it its permanent label."""
        found = self._area_of(site, area)
        if on < found.first_waste:
            raise RuleError("device", f"{area} took no waste until {found.first_waste}")
        with self.book.writing():
            given = label or self.labels.next("device", on)
            device = Device(
                label=given,
                site=site,
                area=area,
                kind=kind,
                station=station,
                total_depth=total_depth,
                screen_top=screen_top,
                screen_bottom=screen_bottom,
                drilled_on=on,
                influence=influence if influence is not None else found.target_radius,
            )
            return self.devices.add(device)

    def connect(self, label: str, on: dt.date) -> Device:
        """Wire a drilled device onto the pipe tree."""
        device = self.devices.get(label)
        with self.book.writing():
            return self.devices.put(device.connect(on))

    def take_offline(self, label: str, on: dt.date) -> Device:
        """Shut a device's valve and take it off the monthly run."""
        device = self.devices.get(label)
        with self.book.writing():
            return self.devices.put(device.take_offline(on))

    def put_online(self, label: str, on: dt.date) -> Device:
        """Put a device that was off the run back on it."""
        device = self.devices.get(label)
        with self.book.writing():
            return self.devices.put(device.put_online(on))

    def abandon(self, label: str, on: dt.date) -> Device:
        """Take a device out of service for good."""
        device = self.devices.get(label)
        with self.book.writing():
            return self.devices.put(device.abandon(on))

    def approve_higher_temperature(self, label: str, degrees: Temperature, on: dt.date) -> Device:
        """Record an approved higher operating value for one wellhead."""
        device = self.devices.get(label)
        subpart = self.sites.standard_of(device.site)
        if not subpart.allows_higher_temperature:
            raise RuleError(subpart.citation, "this standard has no higher operating value")
        if degrees <= subpart.temperature_limit:
            raise RuleError(
                subpart.citation,
                f"{degrees} is not higher than the {subpart.temperature_limit} limit",
            )
        with self.book.writing():
            return self.devices.put(device.approve_higher_temperature(degrees, on))

    def start_rework(self, device: str, kind: Rework, on: dt.date, *, note: str = "") -> Job:
        """Start work on a device, which takes it off the run while it goes on.

        Taking it off the run is not a separate decision. A well being raised
        is not being read, and a well that is not being read has to be off the
        roster or the run cannot be closed. Doing the two together is what
        stops a raise from quietly making every run short.
        """
        found = self.devices.get(device)
        if found.state is State.ABANDONED:
            raise StateError(device, "abandoned", "in service")
        if self.rework.open_on(device) is not None:
            raise RuleError("rework", f"{device} already has work open on it")
        with self.book.writing():
            job = Job.opened(self.labels.next("rework", on), found, kind, on, note)
            self.rework.add(job)
            if found.state is State.CONNECTED:
                self.devices.put(found.take_offline(on))
            return job

    def finish_rework(
        self,
        label: str,
        on: dt.date,
        *,
        depth: float | None = None,
        screen_top: float | None = None,
        screen_bottom: float | None = None,
        note: str = "",
    ) -> Job:
        """Finish the work, remeasure the device, and put it back on the run."""
        job = self.rework.get(label)
        device = self.devices.get(job.device)
        with self.book.writing():
            finished = job.finish(
                on,
                depth=depth,
                screen_top=screen_top,
                screen_bottom=screen_bottom,
                note=note,
            )
            self.rework.put(finished)
            after = finished.apply(device)
            if after.state is State.OFFLINE:
                after = after.put_online(on)
            self.devices.put(after)
            return finished

    def open_rework(self, site: str) -> list[Job]:
        """Every piece of work at a site that is still going on."""
        return self.rework.open_at(site)

    def overdue_rework(self, site: str, on: dt.date) -> list[Job]:
        """Every piece of work that has run past the window a raise allows."""
        subpart = self.sites.standard_of(site)
        return [job for job in self.rework.open_at(site) if job.over_window(subpart, on)]

    def rework_history(self, device: str) -> list[Job]:
        """Every piece of work on one device, oldest first."""
        self.devices.get(device)
        return self.rework.of_device(device)

    def set_radius(self, area: str, radius: float) -> Area:
        """Record the radius the area's collection was designed around."""
        found = self.sites.areas.get(area)
        with self.book.writing():
            return self.sites.areas.put(replace(found, target_radius=radius))

    def coverage_of(self, area: str) -> Coverage:
        """What one area has in it against what it was designed to have."""
        found = self.sites.areas.get(area)
        return coverage(found, self.devices.of_area(area))

    def coverage_at(self, site: str) -> list[Coverage]:
        """Every area of a site read against its design, in label order."""
        return [self.coverage_of(area.label) for area in self.sites.areas_of(site)]

    def shortfalls(self, site: str, on: dt.date) -> list[Shortfall]:
        """Every area short of devices, the most overdue first.

        Being short is not itself a finding. It becomes one when the area is
        also past the day collection had to be in the ground, and the two are
        worked out from completely different things, so they have to be put
        side by side rather than inferred from each other.
        """
        subpart = self.sites.standard_of(site)
        found: list[Shortfall] = []
        for area in self.sites.areas_of(site):
            read = self.coverage_of(area.label)
            if read.is_enough:
                continue
            due = area.install_due(subpart)
            found.append(Shortfall(coverage=read, due=due, overdue=due < on))
        return sorted(found, key=lambda s: (s.due, s.coverage.area))

    def roster(self, site: str) -> list[Device]:
        """The devices the crew is expected to read on the next run."""
        return self.devices.monitored(site)

    def offline(self, site: str) -> list[Device]:
        """Every device currently off the run."""
        return self.devices.in_state(site, State.OFFLINE)

    def overdue_offline(self, site: str, on: dt.date) -> list[Device]:
        """Every device that has been off the run past the window for a raise."""
        subpart = self.sites.standard_of(site)
        return [d for d in self.offline(site) if d.offline_too_long(subpart, on)]

    def unconnected(self, site: str, on: dt.date) -> list[Device]:
        """Every device drilled and never wired up, oldest first."""
        waiting = self.devices.in_state(site, State.DRILLED)
        return sorted(
            (d for d in waiting if d.drilled_on <= on), key=lambda d: (d.drilled_on, d.label)
        )

    def count_by_state(self, site: str) -> dict[str, int]:
        """How many devices are in each state, in the order a report reads them."""
        tally = {str(state): 0 for state in State}
        for device in self.devices.of_site(site):
            tally[str(device.state)] += 1
        return tally

    def _area_of(self, site: str, area: str) -> Area:
        found = self.sites.areas.get(area)
        if found.site != site:
            raise RuleError("device", f"{area} is not an area of {site}")
        return found


__all__ = ["WellfieldDesk"]

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

from gemwalk.errors import RuleError
from gemwalk.ids import Labels
from gemwalk.model.device import Device, Kind, State
from gemwalk.model.landfill import Area
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book
from gemwalk.store.devices import DeviceRepository
from gemwalk.units import Temperature


class WellfieldDesk:
    """The devices in the ground and what state each of them is in."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.devices = DeviceRepository(book)
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

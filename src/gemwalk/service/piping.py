"""Laying pipe, tying devices into it, and pulling it back out.

The tree only ever comes apart from the leaves in. A header cannot be retired
while a live lateral hangs off it, and a lateral cannot be retired while a
device that is still on the run is piped to it, because either of those leaves
a wellhead being pulled on through nothing.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from gemwalk.errors import RuleError, StateError
from gemwalk.ids import Labels
from gemwalk.model.device import Device, State
from gemwalk.model.piping import Header, Lateral
from gemwalk.store.book import Book
from gemwalk.store.devices import DeviceRepository
from gemwalk.store.piping import HeaderRepository, LateralRepository


@dataclass(frozen=True)
class Branch:
    """One lateral and the devices hanging off it."""

    lateral: Lateral
    devices: tuple[Device, ...]

    @property
    def live_devices(self) -> tuple[Device, ...]:
        """The devices on this lateral that are still on the run."""
        return tuple(d for d in self.devices if d.state is State.CONNECTED)


@dataclass(frozen=True)
class Trunk:
    """One header and the branches hanging off it."""

    header: Header
    branches: tuple[Branch, ...]

    @property
    def device_count(self) -> int:
        """How many devices feed this header, through any of its laterals."""
        return sum(len(branch.devices) for branch in self.branches)


class PipingDesk:
    """The pipe between the wellheads and the blower station."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.headers = HeaderRepository(book)
        self.laterals = LateralRepository(book)
        self.devices = DeviceRepository(book)
        self.labels = Labels(book)

    def lay_header(
        self,
        site: str,
        name: str,
        *,
        diameter: float,
        material: str,
        length_feet: float,
        on: dt.date,
    ) -> Header:
        """Put a new trunk line in and hand it its label."""
        with self.book.writing():
            header = Header(
                label=self.labels.next("header", on),
                site=site,
                name=name,
                diameter=diameter,
                material=material,
                length_feet=length_feet,
                installed_on=on,
            )
            return self.headers.add(header)

    def lay_lateral(
        self,
        site: str,
        header: str,
        *,
        diameter: float,
        material: str,
        length_feet: float,
        on: dt.date,
    ) -> Lateral:
        """Branch a new lateral off a header that is still on the system."""
        trunk = self.headers.get(header)
        if trunk.site != site:
            raise RuleError("lateral", f"{header} is not a header at {site}")
        if not trunk.is_live:
            raise StateError(header, "retired", "live")
        with self.book.writing():
            lateral = Lateral(
                label=self.labels.next("lateral", on),
                site=site,
                header=header,
                diameter=diameter,
                material=material,
                length_feet=length_feet,
                installed_on=on,
            )
            if not lateral.fits(trunk):
                raise RuleError(
                    "lateral",
                    f"a {diameter:g} inch lateral does not tie into a "
                    f"{trunk.diameter:g} inch header",
                )
            return self.laterals.add(lateral)

    def tie_in(self, device: str, lateral: str) -> Device:
        """Pipe a device's wellhead to a lateral."""
        found = self.devices.get(device)
        branch = self.laterals.get(lateral)
        if found.site != branch.site:
            raise RuleError("lateral", f"{lateral} is not pipe at {found.site}")
        if not branch.is_live:
            raise StateError(lateral, "retired", "live")
        if found.state is State.ABANDONED:
            raise StateError(device, "abandoned", "in service")
        with self.book.writing():
            return self.devices.put(found.tie_into(lateral))

    def retire_lateral(self, label: str, on: dt.date) -> Lateral:
        """Pull a lateral out, once nothing on the run is piped to it."""
        lateral = self.laterals.get(label)
        still_on = [d for d in self.devices.on_lateral(label) if d.state is State.CONNECTED]
        if still_on:
            names = ", ".join(d.label for d in still_on)
            raise RuleError("lateral", f"{names} still on the run through {label}")
        with self.book.writing():
            return self.laterals.put(lateral.retire(on))

    def retire_header(self, label: str, on: dt.date) -> Header:
        """Pull a header out, once every lateral off it has gone."""
        header = self.headers.get(label)
        live = [lateral for lateral in self.laterals.of_header(label) if lateral.is_live]
        if live:
            names = ", ".join(lateral.label for lateral in live)
            raise RuleError("header", f"{names} still tied into {label}")
        with self.book.writing():
            return self.headers.put(header.retire(on))

    def branch(self, lateral: str) -> Branch:
        """One lateral with the devices hanging off it."""
        return Branch(self.laterals.get(lateral), tuple(self.devices.on_lateral(lateral)))

    def trunk(self, header: str) -> Trunk:
        """One header with everything below it."""
        found = self.headers.get(header)
        branches = tuple(self.branch(lateral.label) for lateral in self.laterals.of_header(header))
        return Trunk(found, branches)

    def tree(self, site: str) -> list[Trunk]:
        """The whole collection system at one site, header by header."""
        return [self.trunk(header.label) for header in self.headers.of_site(site)]

    def devices_on_header(self, header: str) -> list[Device]:
        """Every device feeding one header, in label order."""
        found: list[Device] = []
        for branch in self.trunk(header).branches:
            found.extend(branch.devices)
        return sorted(found, key=lambda d: d.label)

    def unpiped(self, site: str) -> list[Device]:
        """Every device with no lateral, which is a device pulling on nothing."""
        return self.devices.unpiped(site)


__all__ = ["Branch", "PipingDesk", "Trunk"]

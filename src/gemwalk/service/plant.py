"""The blower station: what ran, how hot, and what was down.

The three hour block average is the only figure in the package that can be a
deviation while every reading inside it is fine. The blocks are fixed to the
clock rather than started at the first reading, so a flare lit at ten past nine
has a first block two thirds of an hour short, and the average of that block is
the average of what was recorded in it and not of a full three hours.

Readings taken while the device was not running are left out of the average
entirely. A flare that was down for two hours of a block and hot for one does
not get a low average out of the two hours it was off, because there was no
gas going through it to destroy.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from gemwalk.clock import UTC, hours_between
from gemwalk.errors import RuleError, StateError
from gemwalk.ids import Labels
from gemwalk.model.plant import BLOCK_HOURS, Control, ControlKind, Operation, Outage, block_start
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book
from gemwalk.store.plant import ControlRepository, OperationRepository, OutageRepository


@dataclass(frozen=True)
class Block:
    """One fixed three hour block of a control device's operating record."""

    control: str
    start: dt.datetime
    end: dt.datetime
    readings: int
    running: int
    average: float | None
    floor: float | None

    @property
    def below(self) -> bool:
        """True when the block average fell under the device's floor."""
        if self.average is None or self.floor is None:
            return False
        return self.average < self.floor

    @property
    def is_empty(self) -> bool:
        """True when nothing was recorded in the block while the device ran."""
        return self.running == 0


class PlantDesk:
    """The control devices, their operating record and their outages."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.controls = ControlRepository(book)
        self.operations = OperationRepository(book)
        self.outages = OutageRepository(book)
        self.sites = SiteDesk(book)
        self.labels = Labels(book)

    def install(
        self,
        label: str,
        site: str,
        name: str,
        *,
        kind: ControlKind,
        capacity: float,
        on: dt.date,
        minimum_temp: float | None = None,
    ) -> Control:
        """Put a control device on the system."""
        self.sites.sites.get(site)
        control = Control(
            label=label,
            site=site,
            name=name,
            kind=kind,
            capacity=capacity,
            installed_on=on,
            minimum_temp=minimum_temp,
        )
        with self.book.writing():
            return self.controls.add(control)

    def retire(self, label: str, on: dt.date) -> Control:
        """Take a control device off the system."""
        control = self.controls.get(label)
        if self.outages.open_at(control.site):
            open_here = [o for o in self.outages.open_at(control.site) if o.control == label]
            if open_here:
                raise RuleError("control", f"{label} still has an outage open")
        with self.book.writing():
            return self.controls.put(control.retire(on))

    def log(
        self,
        control: str,
        at: dt.datetime,
        *,
        running: bool,
        flow: float,
        methane: float,
        temperature: float | None = None,
        note: str = "",
    ) -> Operation:
        """Write one line of a device's operating record."""
        found = self.controls.get(control)
        if temperature is not None and not found.kind.has_chamber:
            raise RuleError("operation", f"a {found.kind} has no chamber to measure")
        if temperature is None and found.kind.has_chamber and running:
            raise RuleError("operation", f"a running {found.kind} is measured")
        record = Operation(
            control=control,
            at=at,
            running=running,
            flow=flow,
            methane=methane,
            temperature=temperature,
            note=note,
        )
        with self.book.writing():
            return self.operations.add(record)

    def blocks(self, control: str, first: dt.datetime, last: dt.datetime) -> list[Block]:
        """Every fixed block touching a range, with its average."""
        found = self.controls.get(control)
        start = block_start(first.astimezone(UTC))
        made: list[Block] = []
        while start < last:
            end = start + dt.timedelta(hours=BLOCK_HOURS)
            inside = self.operations.between(control, start, end)
            hot = [o.temperature for o in inside if o.running and o.temperature is not None]
            average = sum(hot) / len(hot) if hot else None
            made.append(
                Block(
                    control=control,
                    start=start,
                    end=end,
                    readings=len(inside),
                    running=sum(1 for o in inside if o.running),
                    average=average,
                    floor=found.minimum_temp,
                )
            )
            start = end
        return made

    def deviations(self, control: str, first: dt.datetime, last: dt.datetime) -> list[Block]:
        """Every block in a range whose average fell under the floor."""
        return [block for block in self.blocks(control, first, last) if block.below]

    def start_outage(
        self,
        control: str,
        at: dt.datetime,
        reason: str,
        *,
        planned: bool = False,
    ) -> Outage:
        """Record a control device going down."""
        found = self.controls.get(control)
        already = [o for o in self.outages.open_at(found.site) if o.control == control]
        if already:
            raise StateError(control, "already down", "running")
        with self.book.writing():
            outage = Outage(
                label=self.labels.next("outage", at.astimezone(UTC).date()),
                control=control,
                site=found.site,
                started_at=at,
                reason=reason,
                planned=planned,
            )
            return self.outages.add(outage)

    def end_outage(self, label: str, at: dt.datetime, note: str = "") -> Outage:
        """Record a control device coming back."""
        outage = self.outages.get(label)
        with self.book.writing():
            return self.outages.put(outage.close(at, note))

    def long_outages(self, site: str, now: dt.datetime) -> list[Outage]:
        """Every outage that has run past the window the standard allows."""
        subpart = self.sites.standard_of(site)
        window = subpart.shutdown_days
        touching = self.outages.overlapping(site, dt.datetime(1970, 1, 1, tzinfo=UTC), now)
        return [o for o in touching if o.over_window(window, now)]

    def down_now(self, site: str) -> list[Outage]:
        """Every control device at a site that is down right now."""
        return self.outages.open_at(site)

    def availability(self, control: str, first: dt.datetime, last: dt.datetime) -> float:
        """The share of a device's records in a range that had it running."""
        inside = self.operations.between(control, first, last)
        if not inside:
            return 0.0
        return sum(1 for o in inside if o.running) / len(inside)

    def downtime_hours(self, control: str, first: dt.datetime, last: dt.datetime) -> float:
        """How many hours of a range a device was down, outages clipped to it."""
        found = self.controls.get(control)
        total = 0.0
        for outage in self.outages.overlapping(found.site, first, last):
            if outage.control != control:
                continue
            began = max(outage.started_at, first)
            ended = min(outage.ended_at or last, last)
            if ended > began:
                total += hours_between(began, ended)
        return total

    def throughput(self, control: str, first: dt.datetime, last: dt.datetime) -> float:
        """The average methane flow through a device while it was running."""
        inside = [o for o in self.operations.between(control, first, last) if o.running]
        if not inside:
            return 0.0
        return sum(o.methane_flow for o in inside) / len(inside)


__all__ = ["Block", "PlantDesk"]

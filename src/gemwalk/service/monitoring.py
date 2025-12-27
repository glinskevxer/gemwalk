"""Walking the wellfield: opening a run, reading each wellhead, closing it.

A run is one pass over one site by one person with one meter. It is opened on
the day the crew starts, readings are written onto it as they are taken, and it
is closed when the last wellhead has been read.

The roster is worked out when the run is closed rather than when it is opened,
because devices come on and off the tree in the middle of a pass. A run cannot
be closed with a device on the roster unread unless somebody says so on the
record, and the reason goes on the run.
"""

from __future__ import annotations

import datetime as dt

from gemwalk.assess import Assessment, assess
from gemwalk.clock import Month
from gemwalk.errors import RuleError, StateError
from gemwalk.ids import Labels
from gemwalk.model.device import Device
from gemwalk.model.reading import Reading, Run
from gemwalk.quality import Character
from gemwalk.service.sites import SiteDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.store.book import Book
from gemwalk.store.readings import ReadingRepository, RunRepository


class MonitoringDesk:
    """The monthly monitoring runs and the readings written onto them."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.runs = RunRepository(book)
        self.readings = ReadingRepository(book)
        self.wellfield = WellfieldDesk(book)
        self.sites = SiteDesk(book)
        self.labels = Labels(book)

    def open_run(self, site: str, on: dt.date, *, monitor: str, meter: str) -> Run:
        """Start a monitoring pass over a site."""
        self.sites.sites.get(site)
        already = self.runs.open_runs(site)
        if already:
            names = ", ".join(r.label for r in already)
            raise RuleError("run", f"{names} is still open at {site}")
        with self.book.writing():
            run = Run(
                label=self.labels.next("run", on),
                site=site,
                started_on=on,
                monitor=monitor,
                meter=meter,
            )
            return self.runs.add(run)

    def record(
        self,
        run: str,
        device: str,
        *,
        on: dt.date,
        methane: float,
        carbon: float,
        oxygen: float,
        balance: float,
        temperature: float,
        static: float,
        applied: float,
        flow: float,
        valve_before: float,
        valve_after: float,
        note: str = "",
    ) -> Reading:
        """Write one wellhead reading onto an open run."""
        pass_ = self.runs.get(run)
        if not pass_.is_open:
            raise StateError(run, "closed", "open")
        found = self.wellfield.devices.get(device)
        if found.site != pass_.site:
            raise RuleError("reading", f"{device} is not a device at {pass_.site}")
        if not found.is_monitored:
            raise StateError(device, str(found.state), "connected")
        if on < pass_.started_on:
            raise RuleError("reading", f"{run} did not start until {pass_.started_on}")
        reading = Reading(
            run=run,
            device=device,
            taken_on=on,
            methane=methane,
            carbon=carbon,
            oxygen=oxygen,
            balance=balance,
            temperature=temperature,
            static=static,
            applied=applied,
            flow=flow,
            valve_before=valve_before,
            valve_after=valve_after,
            note=note,
        )
        with self.book.writing():
            return self.readings.add(reading)

    def missing(self, run: str) -> list[Device]:
        """Every device on the roster that this run has no reading for."""
        pass_ = self.runs.get(run)
        read = {r.device for r in self.readings.of_run(run)}
        return [d for d in self.wellfield.roster(pass_.site) if d.label not in read]

    def close_run(self, run: str, on: dt.date, *, note: str = "") -> Run:
        """Shut a run, once every wellhead on the roster has been read."""
        pass_ = self.runs.get(run)
        short = self.missing(run)
        if short and not note:
            names = ", ".join(d.label for d in short)
            raise RuleError("run", f"{names} unread and no reason given")
        with self.book.writing():
            closed = pass_.close(on)
            if note:
                closed = Run(
                    label=closed.label,
                    site=closed.site,
                    started_on=closed.started_on,
                    monitor=closed.monitor,
                    meter=closed.meter,
                    closed_on=closed.closed_on,
                    note=note,
                )
            return self.runs.put(closed)

    def assessment(self, run: str, device: str) -> Assessment:
        """Read one wellhead on one run against the site's standard."""
        reading = self.readings.on_run_for(run, device)
        if reading is None:
            raise RuleError("reading", f"{device} was not read on {run}")
        return self._assess(reading)

    def assessments(self, run: str) -> list[Assessment]:
        """Read every wellhead on one run, in device order."""
        return [self._assess(reading) for reading in self.readings.of_run(run)]

    def exceedances(self, run: str) -> list[Assessment]:
        """Only the wellheads on one run that are over something."""
        return [a for a in self.assessments(run) if not a.is_clear]

    def characters(self, run: str) -> dict[str, Character]:
        """What each wellhead's analysis says is going on, in device order."""
        return {
            reading.device: reading.analysis.character() for reading in self.readings.of_run(run)
        }

    def of_character(self, run: str, character: Character) -> list[Reading]:
        """Every reading on a run whose analysis has one shape."""
        return [r for r in self.readings.of_run(run) if r.analysis.character() is character]

    def energy(self, run: str) -> float:
        """Million british thermal units an hour the whole field was giving."""
        return sum(r.analysis.energy(r.gas_flow) for r in self.readings.of_run(run))

    def field_flow(self, run: str) -> float:
        """Standard cubic feet a minute the whole field was giving."""
        return sum(r.flow for r in self.readings.of_run(run))

    def drifting(self, device: str, back: int = 3) -> float | None:
        """How far corrected methane has moved over the last *back* readings.

        Corrected methane rather than methane, because a well that is leaking
        harder every month reads as falling methane and flat corrected methane,
        and only one of those is a problem with the well.
        """
        history = self.readings.of_device(device)[-back:]
        if len(history) < 2:
            return None
        first = history[0].analysis.corrected_methane.value
        last = history[-1].analysis.corrected_methane.value
        return last - first

    def runs_in(self, site: str, month: Month) -> list[Run]:
        """Every run at a site started inside one month."""
        return self.runs.between(site, month.first_day.isoformat(), month.last_day.isoformat())

    def months_missed(self, site: str, first: Month, last: Month) -> list[Month]:
        """Every month in a range with no monitoring run at all."""
        missed: list[Month] = []
        month = first
        while month <= last:
            if not self.runs_in(site, month):
                missed.append(month)
            month = month.next
        return missed

    def _assess(self, reading: Reading) -> Assessment:
        device = self.wellfield.devices.get(reading.device)
        subpart = self.sites.standard_of(device.site)
        election = self.sites.election_of(device.site, reading.taken_on)
        return assess(reading, device, subpart, election)


__all__ = ["MonitoringDesk"]

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
from gemwalk.service.instruments import InstrumentDesk
from gemwalk.service.liquids import LiquidsDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.spread import Spread, share_over, share_under, spread
from gemwalk.store.book import Book
from gemwalk.store.readings import ReadingRepository, RunRepository
from gemwalk.tuning import Advice, plan


class MonitoringDesk:
    """The monthly monitoring runs and the readings written onto them."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.runs = RunRepository(book)
        self.readings = ReadingRepository(book)
        self.wellfield = WellfieldDesk(book)
        self.sites = SiteDesk(book)
        self.instruments = InstrumentDesk(book)
        self.liquids = LiquidsDesk(book)
        self.labels = Labels(book)

    def open_run(self, site: str, on: dt.date, *, monitor: str, meter: str) -> Run:
        """Start a monitoring pass over a site.

        A meter the book knows about has to have been fit to use that day. A
        meter it does not know about is a serial off an old paper sheet and is
        taken as written, because refusing those would make it impossible to
        type in the years that came before this package.
        """
        self.sites.sites.get(site)
        if self.instruments.instruments.find(meter) is not None:
            self.instruments.must_be_good(meter, on)
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

    def tuning(self, run: str) -> list[Advice]:
        """What to do to every valve on a run, the ones that matter first.

        Whether a wellhead is standing full of water comes off the tape drops
        and not off the gas reading, which is why the advice is worked out here
        rather than in the run itself. A dead reading with no tape drop behind
        it gets a valve answer, and a dead reading with a flooded well behind it
        gets told to dewater instead. They look identical on the field sheet.
        """
        pass_ = self.runs.get(run)
        subpart = self.sites.standard_of(pass_.site)
        rows: list[tuple[Reading, Device, bool]] = []
        for reading in self.readings.of_run(run):
            device = self.wellfield.devices.get(reading.device)
            water = self.liquids.water_in(reading.device, reading.taken_on)
            rows.append((reading, device, bool(water and water.flooded)))
        return plan(rows, subpart)

    def to_touch(self, run: str) -> list[Advice]:
        """Only the wellheads on a run that somebody has to go and turn."""
        return [given for given in self.tuning(run) if given.is_action]

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

    def shape_of(self, run: str, figure: str) -> Spread | None:
        """The shape of one column of a run's readings, or nothing when empty."""
        values = self.column(run, figure)
        return spread(values) if values else None

    def column(self, run: str, figure: str) -> list[float]:
        """One figure off every reading on a run, in device order."""
        readings = self.readings.of_run(run)
        if figure == "corrected":
            return [r.analysis.corrected_methane.value for r in readings]
        return [float(getattr(r, figure)) for r in self.readings.of_run(run)]

    def outliers(self, run: str, figure: str) -> list[str]:
        """The wellheads whose figure sits well outside the middle of the field."""
        shape = self.shape_of(run, figure)
        if shape is None:
            return []
        odd = set(shape.outliers(self.column(run, figure)))
        return [r.device for r in self.readings.of_run(run) if float(getattr(r, figure)) in odd]

    def share_of_field(self, run: str, figure: str, threshold: float, *, over: bool) -> float:
        """What share of the field is over or under a threshold on one figure."""
        values = self.column(run, figure)
        if not values:
            return 0.0
        return share_over(values, threshold) if over else share_under(values, threshold)

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

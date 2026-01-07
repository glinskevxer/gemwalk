"""The meters, their calibrations, and whether a reading rests on one.

The desk answers one question the rest of the package keeps asking: was this
meter calibrated on the day it was used. It answers it in three parts, because
there are three different answers and they mean different things. There was no
calibration at all. There was one and the meter failed it. There was one, the
meter passed, and it had drifted far enough that the readings taken since the
previous check are in doubt.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from gemwalk.errors import RuleError, StateError
from gemwalk.model.instrument import Calibration, Instrument, Meter
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book
from gemwalk.store.instruments import CalibrationRepository, InstrumentRepository


@dataclass(frozen=True)
class Standing:
    """Whether one meter was fit to use on one day, and why."""

    instrument: str
    day: dt.date
    calibration: Calibration | None
    covered: bool
    passed: bool
    drifted: bool

    @property
    def is_good(self) -> bool:
        """True when a reading taken on this meter that day can be defended."""
        return self.covered and self.passed

    def __str__(self) -> str:
        if self.calibration is None:
            return f"{self.instrument} has no calibration on file at all"
        if not self.covered:
            return (
                f"{self.instrument} was last calibrated on {self.calibration.day}, "
                f"which does not cover {self.day}"
            )
        if not self.passed:
            return (
                f"{self.instrument} was {self.calibration.error:.1f}% out after "
                f"the check on {self.day}"
            )
        if self.drifted:
            return (
                f"{self.instrument} had drifted {self.calibration.drift:.1f}% by "
                f"{self.day}, so the readings before it are in doubt"
            )
        return f"{self.instrument} was calibrated on {self.day} and passed"


class InstrumentDesk:
    """The meters and the calibrations behind them."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.instruments = InstrumentRepository(book)
        self.calibrations = CalibrationRepository(book)
        self.sites = SiteDesk(book)

    def add(
        self,
        label: str,
        site: str,
        *,
        kind: Meter,
        maker: str,
        model: str,
        serial: str,
        on: dt.date,
    ) -> Instrument:
        """Put a meter in the book."""
        self.sites.sites.get(site)
        meter = Instrument(
            label=label,
            site=site,
            kind=kind,
            maker=maker,
            model=model,
            serial=serial,
            in_service=on,
        )
        with self.book.writing():
            return self.instruments.add(meter)

    def retire(self, label: str, on: dt.date) -> Instrument:
        """Take a meter out of service."""
        meter = self.instruments.get(label)
        with self.book.writing():
            return self.instruments.put(meter.retire(on))

    def calibrate(
        self,
        label: str,
        at: dt.datetime,
        *,
        standard: str,
        expected: float,
        before: float,
        after: float,
        by_whom: str,
        note: str = "",
    ) -> Calibration:
        """Write down a calibration of one meter."""
        meter = self.instruments.get(label)
        if not meter.in_service_on(at.date()):
            raise StateError(label, "out of service", "in service")
        check = Calibration(
            instrument=label,
            at=at,
            standard=standard,
            expected=expected,
            before=before,
            after=after,
            by_whom=by_whom,
            note=note,
        )
        with self.book.writing():
            return self.calibrations.add(check)

    def standing(self, label: str, day: dt.date) -> Standing:
        """Whether a meter was fit to use on one day, and why."""
        meter = self.instruments.get(label)
        latest = self.calibrations.latest_before(label, day)
        if latest is None:
            return Standing(label, day, None, covered=False, passed=False, drifted=False)
        covered = meter.covers(latest, day)
        return Standing(
            instrument=label,
            day=day,
            calibration=latest,
            covered=covered,
            passed=latest.passed,
            drifted=latest.drifted,
        )

    def due(self, site: str, day: dt.date) -> list[Instrument]:
        """Every meter in service whose calibration does not cover *day*."""
        found: list[Instrument] = []
        for meter in self.instruments.live(site):
            if not meter.in_service_on(day):
                continue
            if not self.standing(meter.label, day).is_good:
                found.append(meter)
        return found

    def history(self, label: str) -> list[Calibration]:
        """Every calibration of one meter, oldest first."""
        self.instruments.get(label)
        return self.calibrations.of_instrument(label)

    def used_on(self, label: str, day: dt.date) -> list[Calibration]:
        """Every calibration of one meter on one day."""
        return self.calibrations.on_day(label, day)

    def must_be_good(self, label: str, day: dt.date) -> Standing:
        """The standing of a meter, refusing outright if it was not fit to use."""
        found = self.standing(label, day)
        if not found.is_good:
            raise RuleError("calibration", str(found))
        return found


__all__ = ["InstrumentDesk", "Standing"]

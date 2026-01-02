"""The instruments, and the calibration a reading is only as good as.

Every number in this package came off a meter, and a meter that was not
calibrated that morning produced a number nobody can defend. The regulation
says so about the flame ionisation detector in as many words, and the
analyser's own manual says so about the analyser.

A calibration is two readings of one known gas: what the meter said before it
was adjusted and what it said after. The first is the drift, which is what tells
you whether the readings taken since the last calibration are any good, and the
second is whether the meter is fit to use now. Recording only the second is the
usual mistake, and it throws away the only evidence about the readings already
taken.

How long a calibration lasts is a property of the instrument, not of the
calibration. An analyser is good for the day. A detector taken out on a
walkover is calibrated before the walk and drift checked after it, so its window
is one walk and not one day.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import Enum

from gemwalk.errors import OrderError, RuleError, StateError

DRIFT_LIMIT = 10.0
CALIBRATION_LIMIT = 5.0


class Meter(Enum):
    """What kind of instrument it is, which is what says how long a check lasts."""

    ANALYSER = "gas analyser"
    DETECTOR = "flame ionisation detector"
    THERMOCOUPLE = "thermocouple"
    ANEMOMETER = "anemometer"

    def __str__(self) -> str:
        return self.value

    @property
    def good_for_days(self) -> int:
        """How many days a calibration on this kind of instrument stands for."""
        if self is Meter.ANALYSER:
            return 1
        if self is Meter.DETECTOR:
            return 1
        return 365


@dataclass(frozen=True)
class Calibration:
    """One check of one instrument against one known gas."""

    instrument: str
    at: dt.datetime
    standard: str
    expected: float
    before: float
    after: float
    by_whom: str
    note: str = ""
    id: int = 0

    def __post_init__(self) -> None:
        if self.at.tzinfo is None:
            raise RuleError("calibration", "a calibration is stamped with an offset")
        if self.expected <= 0:
            raise RuleError("calibration", "a calibration gas has a value on the bottle")
        if not self.by_whom.strip():
            raise RuleError("calibration", "a calibration is done by somebody")
        if self.before < 0 or self.after < 0:
            raise RuleError("calibration", "a meter cannot read below nothing")

    @property
    def drift(self) -> float:
        """How far out the meter was before it was touched, as a percentage."""
        return abs(self.before - self.expected) / self.expected * 100.0

    @property
    def error(self) -> float:
        """How far out the meter still is after it was adjusted, as a percentage."""
        return abs(self.after - self.expected) / self.expected * 100.0

    @property
    def drifted(self) -> bool:
        """True when the readings taken since the last check are in doubt."""
        return self.drift > DRIFT_LIMIT

    @property
    def passed(self) -> bool:
        """True when the meter is fit to use after the check."""
        return self.error <= CALIBRATION_LIMIT

    @property
    def day(self) -> dt.date:
        """The day the check was made, in utc, which is how it is filed."""
        return self.at.date()


@dataclass(frozen=True)
class Instrument:
    """One meter, with what it is and when it went into service."""

    label: str
    site: str
    kind: Meter
    maker: str
    model: str
    serial: str
    in_service: dt.date
    retired_on: dt.date | None = None

    def __post_init__(self) -> None:
        if not self.serial.strip():
            raise RuleError("instrument", "an instrument has a serial number")
        if self.retired_on is not None and self.retired_on < self.in_service:
            raise OrderError("instrument", str(self.in_service), str(self.retired_on))

    @property
    def is_live(self) -> bool:
        """True while the instrument is still in service."""
        return self.retired_on is None

    def in_service_on(self, day: dt.date) -> bool:
        """True when the instrument was in service on *day*."""
        if day < self.in_service:
            return False
        return self.retired_on is None or day <= self.retired_on

    def covers(self, calibration: Calibration, day: dt.date) -> bool:
        """True when a calibration still stands on *day* for this instrument."""
        gap = (day - calibration.day).days
        return 0 <= gap < self.kind.good_for_days

    def retire(self, on: dt.date) -> Instrument:
        """Take the instrument out of service."""
        if not self.is_live:
            raise StateError(self.label, "retired", "in service")
        return replace(self, retired_on=on)


__all__ = [
    "CALIBRATION_LIMIT",
    "DRIFT_LIMIT",
    "Calibration",
    "Instrument",
    "Meter",
]

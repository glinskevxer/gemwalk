"""The blower station, the devices that burn the gas, and their operating record.

Everything the wellfield pulls ends up at one of these. An enclosed flare has a
chamber with a thermocouple in it and a minimum temperature it has to hold. A
candlestick flare has a flame and no chamber, so there is nothing to measure
and nothing to hold. An engine burns the gas for money and is held to the same
destruction requirement by a different route.

The minimum temperature is not an instantaneous limit. It is a three hour block
average, and the blocks are fixed to the clock rather than started wherever the
reading happens to be: midnight to three, three to six, and so on. A flare that
dips for twenty minutes and recovers has not deviated. A flare that sits four
degrees low for the whole block has, and no single reading on it looks alarming.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import Enum
from zoneinfo import ZoneInfo

from gemwalk.clock import elapsed, hours_between
from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.units import Flow, Percent, Temperature

BLOCK_HOURS = 3


class ControlKind(Enum):
    """What burns the gas."""

    ENCLOSED_FLARE = "enclosed flare"
    CANDLESTICK = "candlestick flare"
    ENGINE = "engine"
    BOILER = "boiler"

    def __str__(self) -> str:
        return self.value

    @property
    def has_chamber(self) -> bool:
        """True when there is a combustion chamber with a temperature to hold."""
        return self in (ControlKind.ENCLOSED_FLARE, ControlKind.BOILER)


@dataclass(frozen=True)
class Control:
    """One device that destroys the gas, with the limit it is held to."""

    label: str
    site: str
    name: str
    kind: ControlKind
    capacity: float
    installed_on: dt.date
    floor_degrees: float | None = None
    retired_on: dt.date | None = None

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise RuleError("control", "a control device has a capacity")
        if self.kind.has_chamber and self.floor_degrees is None:
            raise RuleError("control", f"a {self.kind} has a minimum chamber temperature")
        if not self.kind.has_chamber and self.floor_degrees is not None:
            raise RuleError("control", f"a {self.kind} has no chamber to measure")
        if self.retired_on is not None and self.retired_on < self.installed_on:
            raise OrderError("control", str(self.installed_on), str(self.retired_on))

    @property
    def is_live(self) -> bool:
        """True while the device is still on the system."""
        return self.retired_on is None

    @property
    def rated_flow(self) -> Flow:
        """What the device can take, in standard cubic feet a minute."""
        return Flow(self.capacity)

    @property
    def floor(self) -> Temperature | None:
        """The minimum chamber temperature, where there is a chamber."""
        return None if self.floor_degrees is None else Temperature(self.floor_degrees)

    def retire(self, on: dt.date) -> Control:
        """Take the device off the system."""
        if not self.is_live:
            raise StateError(self.label, "retired", "live")
        return replace(self, retired_on=on)


@dataclass(frozen=True)
class Operation:
    """One line of the operating record: what the device was doing at a moment."""

    control: str
    at: dt.datetime
    running: bool
    flow: float
    methane: float
    temperature: float | None = None
    note: str = ""
    id: int = 0

    def __post_init__(self) -> None:
        if self.at.tzinfo is None:
            raise RuleError("operation", "an operating record is stamped with an offset")
        if self.flow < 0:
            raise RuleError("operation", "a blower cannot pull backwards")
        if not 0.0 <= self.methane <= 100.0:
            raise RuleError("operation", "methane off the analyser scale")

    @property
    def inlet_flow(self) -> Flow:
        """What the blower was pulling."""
        return Flow(self.flow)

    @property
    def inlet_methane(self) -> Percent:
        """The methane in what the blower was pulling."""
        return Percent(self.methane)

    @property
    def chamber(self) -> Temperature | None:
        """The chamber temperature, where the device has a chamber."""
        return None if self.temperature is None else Temperature(self.temperature)

    @property
    def methane_flow(self) -> float:
        """Standard cubic feet a minute of methane, which is what is destroyed."""
        return self.flow * self.methane / 100.0


@dataclass(frozen=True)
class Outage:
    """A stretch of time a control device was not available."""

    label: str
    control: str
    site: str
    started_at: dt.datetime
    reason: str
    ended_at: dt.datetime | None = None
    planned: bool = False
    note: str = ""

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None:
            raise RuleError("outage", "an outage is stamped with an offset")
        if not self.reason.strip():
            raise RuleError("outage", "an outage has a reason")
        if self.ended_at is not None:
            if self.ended_at.tzinfo is None:
                raise RuleError("outage", "an outage is stamped with an offset")
            if self.ended_at < self.started_at:
                raise OrderError("outage", str(self.started_at), str(self.ended_at))

    @property
    def is_open(self) -> bool:
        """True while the device is still down."""
        return self.ended_at is None

    def hours(self, now: dt.datetime) -> float:
        """How long the outage has run, in real hours across any clock change."""
        return hours_between(self.started_at, self.ended_at or now)

    def days(self, now: dt.datetime) -> float:
        """How long the outage has run, in days."""
        return elapsed(self.started_at, self.ended_at or now).total_seconds() / 86400.0

    def over_window(self, days: int, now: dt.datetime) -> bool:
        """True when the outage has run past the window the standard allows."""
        return self.days(now) > days

    def close(self, at: dt.datetime, note: str = "") -> Outage:
        """Record the device coming back."""
        if not self.is_open:
            raise StateError(self.label, "closed", "open")
        if at < self.started_at:
            raise OrderError(self.label, str(self.started_at), str(at))
        return replace(self, ended_at=at, note=note or self.note)


def block_start(at: dt.datetime, zone: str = "UTC") -> dt.datetime:
    """The start of the fixed three hour block a moment falls in.

    The blocks are pinned to the clock and not to the reading, so the first
    reading after an outage lands part way into a block that has already begun.

    The clock they are pinned to is the **site's**, not utc. Flooring a utc
    moment instead puts the boundaries at seven, ten and one in the afternoon
    on a site five hours behind, which splits an ordinary morning across two
    blocks and averages the wrong readings together. It was wrong here until
    the command line was wired up and a site with a real zone ran through it.
    """
    local = at.astimezone(ZoneInfo(zone))
    hour = (local.hour // BLOCK_HOURS) * BLOCK_HOURS
    floor = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    return floor.astimezone(dt.UTC)


__all__ = [
    "BLOCK_HOURS",
    "Control",
    "ControlKind",
    "Operation",
    "Outage",
    "block_start",
]

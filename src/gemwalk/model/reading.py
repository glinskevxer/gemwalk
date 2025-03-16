"""One wellhead read on one day, and the run it was read on.

The meter gives four gas figures at once and they are not independent: methane,
carbon dioxide and oxygen are measured, and the balance is whatever is left of
a hundred. Nitrogen is not measured at all, it is read off the balance, which
is why a standard that lets nitrogen stand in for oxygen is letting a derived
number carry a limit.

A reading also carries what the crew did about it. The valve position before
and after says whether the wellhead was turned, and turning it is what makes
the difference between a finding that was corrected in the field and one that
starts a clock.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace

from gemwalk.errors import OrderError, RuleError
from gemwalk.units import Flow, Percent, Pressure, Temperature

BALANCE_TOLERANCE = 2.0
VALVE_TURNS = 10.0


@dataclass(frozen=True)
class Run:
    """One monthly pass over the wellfield by one person with one meter."""

    label: str
    site: str
    started_on: dt.date
    monitor: str
    meter: str
    closed_on: dt.date | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if not self.monitor.strip():
            raise RuleError("run", "a run is walked by somebody")
        if not self.meter.strip():
            raise RuleError("run", "a run is read with a meter that has a serial")
        if self.closed_on is not None and self.closed_on < self.started_on:
            raise OrderError("run", str(self.started_on), str(self.closed_on))

    @property
    def is_open(self) -> bool:
        """True while readings can still be added to the run."""
        return self.closed_on is None

    def close(self, on: dt.date) -> Run:
        """Shut the run so no more readings can be added to it."""
        if not self.is_open:
            raise RuleError("run", f"{self.label} closed on {self.closed_on}")
        return replace(self, closed_on=on)


@dataclass(frozen=True)
class Reading:
    """What the meter and the gauge said at one wellhead."""

    run: str
    device: str
    taken_on: dt.date
    methane: float
    carbon: float
    oxygen: float
    balance: float
    temperature: float
    static: float
    applied: float
    flow: float
    valve_before: float
    valve_after: float
    note: str = ""
    id: int = 0

    def __post_init__(self) -> None:
        for name, value in (
            ("methane", self.methane),
            ("carbon dioxide", self.carbon),
            ("oxygen", self.oxygen),
            ("balance", self.balance),
        ):
            if not 0.0 <= value <= 100.0:
                raise RuleError("reading", f"{name} of {value:g} is off the analyser scale")
        for name, turns in (("before", self.valve_before), ("after", self.valve_after)):
            if not 0.0 <= turns <= VALVE_TURNS:
                raise RuleError("reading", f"a valve {name} the visit cannot be at {turns:g} turns")
        if self.flow < 0:
            raise RuleError("reading", "a wellhead cannot flow backwards")

    @property
    def total(self) -> float:
        """The four gas figures added up, which the meter says is a hundred."""
        return self.methane + self.carbon + self.oxygen + self.balance

    @property
    def balances(self) -> bool:
        """True when the four gas figures add up to a hundred, near enough."""
        return abs(self.total - 100.0) <= BALANCE_TOLERANCE

    @property
    def nitrogen(self) -> Percent:
        """The nitrogen figure, which is the balance and is not measured."""
        return Percent(self.balance)

    @property
    def methane_reading(self) -> Percent:
        """The methane figure as a concentration."""
        return Percent(self.methane)

    @property
    def oxygen_reading(self) -> Percent:
        """The oxygen figure as a concentration."""
        return Percent(self.oxygen)

    @property
    def wellhead_temperature(self) -> Temperature:
        """The temperature at the wellhead."""
        return Temperature(self.temperature)

    @property
    def gauge(self) -> Pressure:
        """The static gauge pressure, which is the one the standard is about."""
        return Pressure(self.static)

    @property
    def vacuum(self) -> Pressure:
        """The applied vacuum on the wellhead side of the valve."""
        return Pressure(self.applied)

    @property
    def gas_flow(self) -> Flow:
        """What the wellhead gave, in standard cubic feet a minute."""
        return Flow(self.flow)

    @property
    def was_turned(self) -> bool:
        """True when the crew moved the valve while they were standing there."""
        return abs(self.valve_after - self.valve_before) > 1e-9

    @property
    def was_opened(self) -> bool:
        """True when the crew opened the valve further than they found it."""
        return self.valve_after > self.valve_before

    @property
    def is_shut(self) -> bool:
        """True when the crew left the wellhead valve closed."""
        return self.valve_after == 0.0

    @property
    def methane_share(self) -> float:
        """Methane as a share of the methane and carbon dioxide together."""
        both = self.methane + self.carbon
        return 0.0 if both <= 0 else self.methane / both


__all__ = ["BALANCE_TOLERANCE", "VALVE_TURNS", "Reading", "Run"]

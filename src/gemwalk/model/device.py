"""The devices sunk into the refuse, and the states one goes through.

A device is drilled, then connected to a lateral, and only then does it appear
on a monitoring run. It can be taken offline for a raise when the area around
it is filled higher, and it goes back on when the raise is finished. At the end
of its life it is abandoned, and its label is never handed out again.

The temperature limit at a wellhead can be lifted for one device by an approved
higher operating value. It applies to that device only, from the day it was
approved, and it never lifts the oxygen or pressure limits.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import Enum

from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.rules import Standard
from gemwalk.units import Temperature


class Kind(Enum):
    """What was put in the ground."""

    VERTICAL = "vertical well"
    HORIZONTAL = "horizontal collector"
    CLEANOUT = "leachate cleanout"
    TRENCH = "gas trench"

    def __str__(self) -> str:
        return self.value


class State(Enum):
    """Where a device is in its life."""

    DRILLED = "drilled"
    CONNECTED = "connected"
    OFFLINE = "offline"
    ABANDONED = "abandoned"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Device:
    """One extraction point, with its construction and its state."""

    label: str
    site: str
    area: str
    kind: Kind
    station: str
    total_depth: float
    screen_top: float
    screen_bottom: float
    state: State = State.DRILLED
    drilled_on: dt.date = dt.date(2000, 1, 1)
    connected_on: dt.date | None = None
    offline_since: dt.date | None = None
    abandoned_on: dt.date | None = None
    hov_degrees: float | None = None
    hov_approved: dt.date | None = None

    def __post_init__(self) -> None:
        if self.total_depth <= 0:
            raise RuleError("device", "a device has some depth")
        if self.screen_top < 0:
            raise RuleError("device", "a screen starts below the surface")
        if self.screen_bottom <= self.screen_top:
            raise OrderError("screen", f"{self.screen_top} ft", f"{self.screen_bottom} ft")
        if self.screen_bottom > self.total_depth:
            raise RuleError(
                "device",
                f"a screen to {self.screen_bottom:g} ft cannot sit in a {self.total_depth:g} ft "
                "borehole",
            )
        if self.connected_on is not None and self.connected_on < self.drilled_on:
            raise OrderError("device", str(self.drilled_on), str(self.connected_on))

    @property
    def screen_length(self) -> float:
        """How much slotted pipe is pulling on the refuse, in feet."""
        return self.screen_bottom - self.screen_top

    @property
    def is_connected(self) -> bool:
        """True when the device is on the pipe tree and being pulled on."""
        return self.state is State.CONNECTED

    @property
    def is_monitored(self) -> bool:
        """True when the device has to appear on the monthly run."""
        return self.state is State.CONNECTED

    def temperature_limit(self, standard: Standard, on: dt.date) -> Temperature:
        """The temperature this wellhead is held to on *on*.

        An approved higher operating value replaces the standard's limit, but
        only from the day it was approved and only where the standard allows
        one at all.
        """
        if self.hov_degrees is None or self.hov_approved is None:
            return standard.temperature_limit
        if not standard.allows_higher_temperature:
            return standard.temperature_limit
        if on < self.hov_approved:
            return standard.temperature_limit
        return Temperature(self.hov_degrees)

    def connect(self, on: dt.date) -> Device:
        """Put the device on the pipe tree."""
        if self.state is not State.DRILLED:
            raise StateError(self.label, str(self.state), "drilled")
        if on < self.drilled_on:
            raise OrderError(self.label, str(self.drilled_on), str(on))
        return replace(self, state=State.CONNECTED, connected_on=on)

    def take_offline(self, on: dt.date) -> Device:
        """Shut the valve and take the device off the run, for a raise or a repair."""
        if self.state is not State.CONNECTED:
            raise StateError(self.label, str(self.state), "connected")
        return replace(self, state=State.OFFLINE, offline_since=on)

    def put_online(self, on: dt.date) -> Device:
        """Put a device that was offline back on the run."""
        if self.state is not State.OFFLINE:
            raise StateError(self.label, str(self.state), "offline")
        if self.offline_since is not None and on < self.offline_since:
            raise OrderError(self.label, str(self.offline_since), str(on))
        return replace(self, state=State.CONNECTED, offline_since=None)

    def abandon(self, on: dt.date) -> Device:
        """Take the device out of service for good."""
        if self.state is State.ABANDONED:
            raise StateError(self.label, "abandoned", "in service")
        return replace(self, state=State.ABANDONED, abandoned_on=on, offline_since=None)

    def approve_higher_temperature(self, degrees: Temperature, on: dt.date) -> Device:
        """Record an approved higher operating value for this wellhead."""
        return replace(self, hov_degrees=degrees.fahrenheit, hov_approved=on)

    def offline_days(self, on: dt.date) -> int:
        """How long the device has been off the run, zero when it is on it."""
        if self.state is not State.OFFLINE or self.offline_since is None:
            return 0
        return (on - self.offline_since).days

    def offline_too_long(self, standard: Standard, on: dt.date) -> bool:
        """True when a device has been off the run past the window for a raise."""
        return self.offline_days(on) > standard.raising_days


__all__ = ["Device", "Kind", "State"]

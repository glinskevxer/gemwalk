"""Liquid in the wells, and the condensate that comes back down the pipe.

A gas well is a hole in wet refuse, and the water finds it. The crew drops a
tape down the casing and writes down the depth to liquid from the top of the
casing, which is the one number they can actually measure. Everything anybody
wants to know is worked out from it and the well's own construction.

What matters is how much of the slotted pipe is under water. A well with two
feet of liquid in the bottom of a sixty four foot screen is a well doing almost
all of its job. A well with liquid up over the top of the screen is a well
pulling on nothing at all, and it will read no flow, no methane and a suspicious
amount of air, which reads at the desk exactly like a well with a leaking seal.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import Enum

from gemwalk.errors import OrderError, RuleError, StateError
from gemwalk.model.device import Device


class SumpKind(Enum):
    """What the condensate is being caught in."""

    KNOCKOUT = "knockout pot"
    SUMP = "condensate sump"
    TANK = "storage tank"
    TRAP = "drip trap"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Sump:
    """One place on the pipe tree that condensate collects in."""

    label: str
    site: str
    station: str
    kind: SumpKind
    capacity: float
    installed_on: dt.date
    retired_on: dt.date | None = None

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise RuleError("sump", "a sump holds something")
        if self.retired_on is not None and self.retired_on < self.installed_on:
            raise OrderError("sump", str(self.installed_on), str(self.retired_on))

    @property
    def is_live(self) -> bool:
        """True while the sump is still on the system."""
        return self.retired_on is None

    def retire(self, on: dt.date) -> Sump:
        """Take the sump off the system."""
        if not self.is_live:
            raise StateError(self.label, "retired", "live")
        return replace(self, retired_on=on)


@dataclass(frozen=True)
class Level:
    """One tape drop down a well casing."""

    device: str
    taken_on: dt.date
    depth: float
    pumped: bool = False
    note: str = ""
    id: int = 0

    def __post_init__(self) -> None:
        if self.depth < 0:
            raise RuleError("level", "a depth to liquid is measured downwards")

    def liquid_column(self, device: Device) -> float:
        """How many feet of water are standing in the hole."""
        return max(0.0, device.total_depth - self.depth)

    def submerged(self, device: Device) -> float:
        """How many feet of the slotted screen are under water.

        Everything here is a depth below the top of the casing, so the water
        occupies the range from the tape reading down to the bottom of the
        hole and the screen occupies the range between its two depths. What is
        wanted is the overlap, and getting the sign of it the wrong way round
        turns a well with a foot of water in it into a flooded one.
        """
        wet_top = max(self.depth, device.screen_top)
        wet_bottom = min(device.total_depth, device.screen_bottom)
        return max(0.0, wet_bottom - wet_top)

    def submerged_share(self, device: Device) -> float:
        """What share of the screen is under water, from nothing to all of it."""
        if device.screen_length <= 0:
            return 0.0
        return self.submerged(device) / device.screen_length

    def is_flooded(self, device: Device) -> bool:
        """True when the whole screen is under water and the well pulls nothing."""
        return self.submerged_share(device) >= 1.0

    def is_dry(self, device: Device) -> bool:
        """True when there is no water standing in the screen at all."""
        return self.submerged(device) <= 0.0

    def above_screen(self, device: Device) -> float:
        """How many feet of water stand above the top of the screen."""
        return max(0.0, device.screen_top - self.depth)


@dataclass(frozen=True)
class Pumpout:
    """One load of condensate taken off a sump."""

    sump: str
    at: dt.datetime
    gallons: float
    hauler: str
    bound_for: str
    note: str = ""
    id: int = 0

    def __post_init__(self) -> None:
        if self.at.tzinfo is None:
            raise RuleError("pumpout", "a pumpout is stamped with an offset")
        if self.gallons <= 0:
            raise RuleError("pumpout", "a load has some volume")
        if not self.hauler.strip():
            raise RuleError("pumpout", "a load is taken by somebody")
        if not self.bound_for.strip():
            raise RuleError("pumpout", "a load goes somewhere")

    def fills(self, sump: Sump) -> float:
        """What share of the sump's capacity this load was."""
        return self.gallons / sump.capacity


__all__ = ["Level", "Pumpout", "Sump", "SumpKind"]

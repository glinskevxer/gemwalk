"""The pipe between a wellhead and the blower.

Gas leaves a device through a lateral, the lateral ties into a header, and the
header runs back to the blower and flare station. Nothing is pulled on that is
not on that tree, so a device with no lateral is a device that was drilled and
never wired up, whatever its state column says.

Pipe is sized by its outside diameter in inches and rated by its standard
dimension ratio, and the only thing this package does with either is print them
and refuse a lateral bigger than the header it ties into.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace

from gemwalk.errors import OrderError, RuleError

MATERIALS = ("HDPE SDR11", "HDPE SDR17", "HDPE SDR21", "PVC SCH40", "PVC SCH80")


def _check_pipe(what: str, diameter: float, length: float, material: str) -> None:
    if diameter <= 0:
        raise RuleError(what, "pipe has a diameter")
    if length <= 0:
        raise RuleError(what, "pipe has a length")
    if material not in MATERIALS:
        raise RuleError(what, f"{material} is not a pipe this site uses")


@dataclass(frozen=True)
class Header:
    """A trunk line running from the blower station out into the field."""

    label: str
    site: str
    name: str
    diameter: float
    material: str
    length_feet: float
    installed_on: dt.date
    retired_on: dt.date | None = None

    def __post_init__(self) -> None:
        _check_pipe("header", self.diameter, self.length_feet, self.material)
        if self.retired_on is not None and self.retired_on < self.installed_on:
            raise OrderError("header", str(self.installed_on), str(self.retired_on))

    @property
    def is_live(self) -> bool:
        """True while the header is still on the system."""
        return self.retired_on is None

    def in_service_on(self, day: dt.date) -> bool:
        """True when the header was carrying gas on *day*."""
        if day < self.installed_on:
            return False
        return self.retired_on is None or day <= self.retired_on

    def retire(self, on: dt.date) -> Header:
        """Take the header off the system."""
        if not self.is_live:
            raise RuleError("header", f"{self.label} came out on {self.retired_on}")
        return replace(self, retired_on=on)


@dataclass(frozen=True)
class Lateral:
    """A branch line tying a group of devices into one header."""

    label: str
    site: str
    header: str
    diameter: float
    material: str
    length_feet: float
    installed_on: dt.date
    retired_on: dt.date | None = None

    def __post_init__(self) -> None:
        _check_pipe("lateral", self.diameter, self.length_feet, self.material)
        if self.retired_on is not None and self.retired_on < self.installed_on:
            raise OrderError("lateral", str(self.installed_on), str(self.retired_on))

    @property
    def is_live(self) -> bool:
        """True while the lateral is still on the system."""
        return self.retired_on is None

    def in_service_on(self, day: dt.date) -> bool:
        """True when the lateral was carrying gas on *day*."""
        if day < self.installed_on:
            return False
        return self.retired_on is None or day <= self.retired_on

    def retire(self, on: dt.date) -> Lateral:
        """Take the lateral off the system."""
        if not self.is_live:
            raise RuleError("lateral", f"{self.label} came out on {self.retired_on}")
        return replace(self, retired_on=on)

    def fits(self, header: Header) -> bool:
        """True when the lateral is no bigger than the header it ties into."""
        return self.diameter <= header.diameter


__all__ = ["MATERIALS", "Header", "Lateral"]

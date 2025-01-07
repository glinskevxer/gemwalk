"""The quantities a wellhead reading is written in, and how they are read back.

A field sheet is written by hand in the units the meter shows, and the meter
shows five different ones. Methane and oxygen come off the analyser as percent
by volume, surface readings come off the flame ionisation detector as parts per
million, the thermocouple reads degrees Fahrenheit on this site and Celsius on
the regulation, wellhead pressure is inches of water column and is signed, and
flow is standard cubic feet a minute.

Every one of them is stored as a plain float in one canonical unit and printed
back the way the sheet was written. The canonical units are: percent by volume,
parts per million by volume, degrees Fahrenheit, inches of water column, and
standard cubic feet a minute.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from gemwalk.errors import RangeError, UnitError

_NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)"


def _split(text: str, wanted: str) -> tuple[float, str]:
    """Split a written quantity into its number and its trailing unit word."""
    match = re.fullmatch(rf"\s*({_NUMBER})\s*([^\s].*?)?\s*", text)
    if match is None:
        raise UnitError(text, wanted)
    return float(match.group(1)), (match.group(2) or "").strip().lower()


@dataclass(frozen=True, order=True)
class Percent:
    """A gas concentration by volume, as the analyser shows it."""

    value: float

    LOW: ClassVar[float] = 0.0
    HIGH: ClassVar[float] = 100.0

    def __post_init__(self) -> None:
        if not self.LOW <= self.value <= self.HIGH:
            raise RangeError("concentration", self.value, self.LOW, self.HIGH)

    @classmethod
    def parse(cls, text: str) -> Percent:
        """Read ``"52.4"``, ``"52.4%"`` or ``"52.4 pct"`` as a concentration."""
        number, unit = _split(text, "a percentage")
        if unit not in {"", "%", "pct", "percent", "%v/v", "v/v"}:
            raise UnitError(text, "a percentage")
        return cls(number)

    def __str__(self) -> str:
        return f"{self.value:.1f}%"


@dataclass(frozen=True, order=True)
class Ppmv:
    """A surface reading in parts per million by volume of methane."""

    value: float

    def __post_init__(self) -> None:
        if self.value < 0:
            raise RangeError("surface reading", self.value, 0.0, 1_000_000.0)
        if self.value > 1_000_000:
            raise RangeError("surface reading", self.value, 0.0, 1_000_000.0)

    @classmethod
    def parse(cls, text: str) -> Ppmv:
        """Read ``"480"``, ``"480 ppm"`` or ``"480 ppmv"`` as a surface reading."""
        number, unit = _split(text, "a surface reading")
        if unit in {"", "ppm", "ppmv"}:
            return cls(number)
        if unit in {"%", "pct", "percent"}:
            return cls(number * 10_000)
        raise UnitError(text, "a surface reading")

    def as_percent(self) -> Percent:
        """The same reading as a concentration, which is what the analyser shows."""
        return Percent(self.value / 10_000)

    def __str__(self) -> str:
        return f"{self.value:.0f} ppmv"


@dataclass(frozen=True, order=True)
class Temperature:
    """A wellhead temperature, held in Fahrenheit because the sheet is."""

    fahrenheit: float

    LOW: ClassVar[float] = -40.0
    HIGH: ClassVar[float] = 400.0

    def __post_init__(self) -> None:
        if not self.LOW <= self.fahrenheit <= self.HIGH:
            raise RangeError("temperature", self.fahrenheit, self.LOW, self.HIGH)

    @classmethod
    def parse(cls, text: str) -> Temperature:
        """Read ``"118"``, ``"118 F"`` or ``"47.8 C"`` as a wellhead temperature."""
        number, unit = _split(text, "a temperature")
        if unit in {"", "f", "degf", "deg f", "°f"}:
            return cls(number)
        if unit in {"c", "degc", "deg c", "°c"}:
            return cls(number * 9.0 / 5.0 + 32.0)
        raise UnitError(text, "a temperature")

    @property
    def celsius(self) -> float:
        """The same temperature in the unit the regulation is written in."""
        return (self.fahrenheit - 32.0) * 5.0 / 9.0

    def __str__(self) -> str:
        return f"{self.fahrenheit:.1f} F"


@dataclass(frozen=True, order=True)
class Pressure:
    """A wellhead gauge pressure in inches of water column, sign and all.

    The sign is the whole point. A well under vacuum reads negative, and a well
    reading zero or above is pushing gas out through the cover.
    """

    inches: float

    LOW: ClassVar[float] = -200.0
    HIGH: ClassVar[float] = 200.0

    def __post_init__(self) -> None:
        if not self.LOW <= self.inches <= self.HIGH:
            raise RangeError("pressure", self.inches, self.LOW, self.HIGH)

    @classmethod
    def parse(cls, text: str) -> Pressure:
        """Read ``"-1.4"``, ``"-1.4 in wc"`` or ``"-1.4 in. w.c."`` as a pressure."""
        number, unit = _split(text, "a pressure")
        flat = unit.replace(".", "").replace(" ", "")
        if flat in {"", "inwc", "inchwc", "incheswc", "wc", "iwc", "inh2o"}:
            return cls(number)
        raise UnitError(text, "a pressure")

    @property
    def is_positive(self) -> bool:
        """True when the wellhead is at or above atmosphere, which is a finding."""
        return self.inches >= 0.0

    def __str__(self) -> str:
        return f'{self.inches:+.2f}" w.c.'


@dataclass(frozen=True, order=True)
class Flow:
    """A gas flow in standard cubic feet a minute."""

    scfm: float

    def __post_init__(self) -> None:
        if self.scfm < 0:
            raise RangeError("flow", self.scfm, 0.0, 100_000.0)

    @classmethod
    def parse(cls, text: str) -> Flow:
        """Read ``"42"``, ``"42 scfm"`` or ``"2520 scfh"`` as a flow."""
        number, unit = _split(text, "a flow")
        if unit in {"", "scfm", "cfm"}:
            return cls(number)
        if unit in {"scfh", "cfh"}:
            return cls(number / 60.0)
        raise UnitError(text, "a flow")

    def __str__(self) -> str:
        return f"{self.scfm:.1f} scfm"


__all__ = ["Flow", "Percent", "Ppmv", "Pressure", "Temperature"]

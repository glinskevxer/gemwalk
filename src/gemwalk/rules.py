"""The federal standards a landfill gas collection system is run against.

Three standards are in play on real sites and they are not interchangeable. A
landfill that took waste before May 1991 and stopped before 1996 sits under one
of them, a modern one sits under another, and a site whose state has adopted the
emission guidelines sits under a third. They agree about the temperature at a
wellhead and they disagree about almost everything else: whether nitrogen may
stand in for oxygen, how big the non methane emission rate has to be before a
system is required at all, and how long the operator has after a bad reading.

Nothing in this module reads or writes anything. It is a table of numbers with
the paragraph each one comes from written beside it, and it is the only place
in the package where any of those numbers appear.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from gemwalk.errors import DesignError, UnknownError
from gemwalk.units import Percent, Ppmv, Pressure, Temperature


class Finding(Enum):
    """The kinds of reading that put a device out of compliance."""

    TEMPERATURE = "temperature"
    OXYGEN = "oxygen"
    NITROGEN = "nitrogen"
    PRESSURE = "pressure"
    SURFACE = "surface"

    def __str__(self) -> str:
        return self.value

    @property
    def family(self) -> str:
        """The limit this finding is one of the two readings of.

        Oxygen and nitrogen are the same limit read two ways, and a site can
        move from one to the other while a clock is running. Matching a new
        reading to an open clock has to be done on the family, or a site that
        elects the alternative half way through leaves an oxygen clock that
        nothing will ever close.
        """
        if self in (Finding.OXYGEN, Finding.NITROGEN):
            return "gas"
        return self.value


@dataclass(frozen=True)
class Windows:
    """How long the operator has, in calendar days, after a wellhead finding.

    The three run in sequence off the same reading. The first is a valve turn
    and a recheck, the second is real work on the well, and the third is the
    one that means drilling.
    """

    correct: int
    action: int
    expand: int

    def __post_init__(self) -> None:
        if not self.correct < self.action < self.expand:
            raise DesignError("windows", "the three windows have to widen")


@dataclass(frozen=True)
class SurfaceWindows:
    """How long the operator has after a surface reading over the limit.

    These do not work the way the wellhead windows do, and the difference is
    the whole trick of the surface programme. A wellhead's three windows are all
    counted from the one bad reading. A surface hit's repair window is counted
    from the day it was found, but its remonitor window is counted from the day
    the repair was made, so a crew that fixes a spot on day one has to be back
    on it by day eleven and a crew that fixes it on day ten has until day
    twenty. Only the last window, the one that means drilling, goes back to the
    day the hit was found.
    """

    repair: int
    remonitor: int
    expand: int
    attempts: int = 2


@dataclass(frozen=True)
class Election:
    """What a site has chosen, where its standard leaves it a choice.

    It sits here rather than with the assessment because a site records it
    long before anybody reads a wellhead against it.
    """

    nitrogen_alternative: bool = False
    higher_pressure: bool = False


@dataclass(frozen=True)
class Standard:
    """One federal standard, with every number it fixes."""

    code: str
    name: str
    citation: str
    temperature_limit: Temperature
    oxygen_limit: Percent
    nitrogen_limit: Percent | None
    pressure_limit: Pressure
    surface_limit: Ppmv
    nmoc_threshold_mg: float
    design_capacity_mg: float
    wind_average_mph: float
    wind_gust_mph: float
    sem_spacing_metres: float
    windows: Windows
    surface_windows: SurfaceWindows
    active_install_years: int
    closed_install_years: int
    shutdown_days: int
    raising_days: int
    allows_higher_temperature: bool
    allows_higher_pressure: bool

    @property
    def allows_nitrogen(self) -> bool:
        """True when nitrogen may be read in place of oxygen at the wellhead."""
        return self.nitrogen_limit is not None


WWW = Standard(
    code="WWW",
    name="new source performance standards for landfills built 1991 to 2016",
    citation="40 CFR 60 subpart WWW",
    temperature_limit=Temperature(131.0),
    oxygen_limit=Percent(5.0),
    nitrogen_limit=None,
    pressure_limit=Pressure(0.0),
    surface_limit=Ppmv(500.0),
    nmoc_threshold_mg=50.0,
    design_capacity_mg=2_500_000.0,
    wind_average_mph=5.0,
    wind_gust_mph=10.0,
    sem_spacing_metres=30.0,
    windows=Windows(correct=5, action=15, expand=120),
    surface_windows=SurfaceWindows(repair=10, remonitor=10, expand=120),
    active_install_years=5,
    closed_install_years=2,
    shutdown_days=5,
    raising_days=60,
    allows_higher_temperature=True,
    allows_higher_pressure=False,
)

XXX = Standard(
    code="XXX",
    name="new source performance standards for landfills built after July 2014",
    citation="40 CFR 60 subpart XXX",
    temperature_limit=Temperature(131.0),
    oxygen_limit=Percent(5.0),
    nitrogen_limit=Percent(20.0),
    pressure_limit=Pressure(0.0),
    surface_limit=Ppmv(500.0),
    nmoc_threshold_mg=34.0,
    design_capacity_mg=2_500_000.0,
    wind_average_mph=5.0,
    wind_gust_mph=10.0,
    sem_spacing_metres=30.0,
    windows=Windows(correct=5, action=15, expand=120),
    surface_windows=SurfaceWindows(repair=10, remonitor=10, expand=120),
    active_install_years=5,
    closed_install_years=2,
    shutdown_days=5,
    raising_days=60,
    allows_higher_temperature=True,
    allows_higher_pressure=True,
)

CF = Standard(
    code="Cf",
    name="emission guidelines for landfills that stopped taking waste before July 2014",
    citation="40 CFR 60 subpart Cf",
    temperature_limit=Temperature(131.0),
    oxygen_limit=Percent(5.0),
    nitrogen_limit=Percent(20.0),
    pressure_limit=Pressure(0.0),
    surface_limit=Ppmv(500.0),
    nmoc_threshold_mg=34.0,
    design_capacity_mg=2_500_000.0,
    wind_average_mph=5.0,
    wind_gust_mph=10.0,
    sem_spacing_metres=30.0,
    windows=Windows(correct=5, action=15, expand=120),
    surface_windows=SurfaceWindows(repair=10, remonitor=10, expand=120),
    active_install_years=5,
    closed_install_years=2,
    shutdown_days=5,
    raising_days=60,
    allows_higher_temperature=True,
    allows_higher_pressure=True,
)

STANDARDS: dict[str, Standard] = {WWW.code: WWW, XXX.code: XXX, CF.code: CF}


def standard(code: str) -> Standard:
    """The standard a site is subject to, by its subpart letter."""
    try:
        return STANDARDS[code]
    except KeyError:
        raise UnknownError("standard", code) from None


def codes() -> list[str]:
    """Every subpart letter the package knows, in the order they were written."""
    return list(STANDARDS)


__all__ = [
    "CF",
    "STANDARDS",
    "WWW",
    "XXX",
    "Election",
    "Finding",
    "Standard",
    "SurfaceWindows",
    "Windows",
    "codes",
    "standard",
]

"""Reading a gas analysis for what it says about the well, not the regulation.

The four figures on a field sheet answer a compliance question and a mechanical
one, and the mechanical one is the useful half day to day.

Air is 20.9 percent oxygen and the balance is everything else, so the nitrogen
it brings with it is 3.78 times the oxygen. That ratio is the whole trick. A wellhead
reading a lot of oxygen with about 3.7 times as much nitrogen behind it is
pulling air, and the fix is a valve or a cover repair. A wellhead reading a lot
of nitrogen with almost no oxygen is not pulling air at all: either the oxygen
is being consumed in the refuse before it reaches the wellhead, which means the
well is being over pulled and is heading for a fire, or the meter is wrong.
Those are three different jobs and the numbers tell them apart.

Subtracting the air out gives what the refuse is actually producing, which is
the number worth trending. A well whose methane fell from fifty two to forty
four looks like it is dying until the air is taken out and both readings come
back at fifty eight.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from gemwalk.errors import RuleError
from gemwalk.units import Flow, Percent

AIR_OXYGEN = 20.9
# The balance figure lumps argon and everything else in with the nitrogen, so
# the complement of the oxygen is what belongs here. Using the 78.1 that a
# textbook gives for nitrogen alone leaves a percent of pure air unaccounted
# for, and taking the air back out of a sample that is nothing but air then
# leaves a percent of something behind.
AIR_NITROGEN = 79.1
AIR_RATIO = AIR_NITROGEN / AIR_OXYGEN
METHANE_BTU = 1_012.0
RATIO_SLACK = 0.9


class Character(Enum):
    """What the shape of an analysis says is going on at the wellhead."""

    SETTLED = "gas the way the refuse makes it"
    AIR = "air being pulled in"
    STARVED = "nitrogen with no oxygen behind it, so the well is over pulled"
    THIN = "hardly any gas at all"
    IMPOSSIBLE = "the four figures cannot have come off one sample"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Quality:
    """One gas analysis, read for what it says about the well."""

    methane: float
    carbon: float
    oxygen: float
    balance: float

    def __post_init__(self) -> None:
        for name, value in (
            ("methane", self.methane),
            ("carbon dioxide", self.carbon),
            ("oxygen", self.oxygen),
            ("balance", self.balance),
        ):
            if not 0.0 <= value <= 100.0:
                raise RuleError("quality", f"{name} of {value:g} is off the analyser scale")

    @property
    def total(self) -> float:
        """The four figures added up."""
        return self.methane + self.carbon + self.oxygen + self.balance

    @property
    def air(self) -> float:
        """How much of the sample is air, worked back from the oxygen."""
        return min(100.0, self.oxygen * (1.0 + AIR_RATIO))

    @property
    def nitrogen_ratio(self) -> float:
        """Nitrogen over oxygen, which is 3.78 when the nitrogen came from air."""
        return self.balance / self.oxygen if self.oxygen > 0 else float("inf")

    @property
    def looks_like_air(self) -> bool:
        """True when there is about as much nitrogen as the oxygen brought with it."""
        if self.oxygen <= 0.1:
            return False
        return abs(self.nitrogen_ratio - AIR_RATIO) <= RATIO_SLACK

    @property
    def excess_nitrogen(self) -> float:
        """Nitrogen beyond what the oxygen accounts for, which air cannot explain."""
        return max(0.0, self.balance - self.oxygen * AIR_RATIO)

    def without_air(self) -> Quality:
        """The same sample with the air taken back out and the rest re scaled.

        This is what the refuse is producing, which is the figure to trend. A
        well that has been leaking harder each month reads as falling methane
        and flat corrected methane, and only one of those is a well problem.
        """
        left = 100.0 - self.air
        if left <= 0:
            return Quality(methane=0.0, carbon=0.0, oxygen=0.0, balance=0.0)
        scale = 100.0 / left
        return Quality(
            methane=min(100.0, self.methane * scale),
            carbon=min(100.0, self.carbon * scale),
            oxygen=0.0,
            balance=min(100.0, max(0.0, self.excess_nitrogen) * scale),
        )

    @property
    def corrected_methane(self) -> Percent:
        """Methane with the air taken out, which is what the refuse is making."""
        return Percent(self.without_air().methane)

    def heat_value(self) -> float:
        """British thermal units in a standard cubic foot of this gas."""
        return self.methane / 100.0 * METHANE_BTU

    def energy(self, flow: Flow) -> float:
        """Million british thermal units an hour at this flow."""
        return self.heat_value() * flow.scfm * 60.0 / 1_000_000.0

    def character(self) -> Character:
        """What the shape of the analysis says is going on."""
        if abs(self.total - 100.0) > 5.0:
            return Character.IMPOSSIBLE
        if self.methane < 5.0:
            return Character.THIN
        if self.looks_like_air and self.oxygen >= 1.0:
            return Character.AIR
        if self.excess_nitrogen >= 15.0 and self.oxygen < 1.0:
            return Character.STARVED
        return Character.SETTLED


__all__ = [
    "AIR_NITROGEN",
    "AIR_OXYGEN",
    "AIR_RATIO",
    "METHANE_BTU",
    "RATIO_SLACK",
    "Character",
    "Quality",
]

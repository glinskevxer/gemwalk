"""The non methane organic compound emission rate, and the tier it was got at.

This is the number that decides whether a landfill needs a collection system at
all. It is not measured. It is calculated out of how much waste went in, how
long ago, and one concentration figure, and the whole regulatory argument is
about where that concentration figure comes from.

The equation is the one in the standard:

    M = 2 * L0 * R * (e^(-k c) - e^(-k t)) * C * 3.6e-9

with M in megagrams a year, L0 the methane generation potential in cubic metres
a megagram, R the average annual acceptance rate in megagrams a year, k the
generation rate constant a year, t the age of the landfill in years, c the years
since it closed, and C the concentration as hexane in parts per million.

The three tiers differ only in which of those the operator is allowed to make
up. Tier one takes every default. Tier two keeps the default rate constant and
substitutes a concentration measured at the site, which is usually far under the
default and is why most sites bother. Tier three measures the rate constant as
well. A site whose tier one number is over the threshold and whose tier two
number is under it is not required to collect, and that is the entire point of
the exercise.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import Enum

from gemwalk.errors import RuleError
from gemwalk.rules import Standard

CONVERSION = 3.6e-9
DEFAULT_K = 0.05
DEFAULT_ARID_K = 0.02
DEFAULT_L0 = 170.0
DEFAULT_NMOC = 4_000.0


class Tier(Enum):
    """How much of the calculation the site measured for itself."""

    ONE = "tier 1"
    TWO = "tier 2"
    THREE = "tier 3"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Inputs:
    """Everything the equation needs, and where each figure came from."""

    acceptance: float
    age: float
    closed_years: float = 0.0
    generation_potential: float = DEFAULT_L0
    rate_constant: float = DEFAULT_K
    concentration: float = DEFAULT_NMOC
    tier: Tier = Tier.ONE

    def __post_init__(self) -> None:
        if self.acceptance <= 0:
            raise RuleError("nmoc", "a landfill that took no waste generates nothing")
        if self.age <= 0:
            raise RuleError("nmoc", "an age is measured in years since the first load")
        if self.closed_years < 0:
            raise RuleError("nmoc", "a closure cannot be in the future")
        if self.closed_years > self.age:
            raise RuleError("nmoc", "a landfill cannot have closed before it opened")
        if self.rate_constant <= 0:
            raise RuleError("nmoc", "a generation rate constant is positive")
        if self.generation_potential <= 0:
            raise RuleError("nmoc", "a generation potential is positive")
        if self.concentration <= 0:
            raise RuleError("nmoc", "a concentration is positive")
        if self.tier is Tier.ONE and self.concentration != DEFAULT_NMOC:
            raise RuleError("nmoc", "tier 1 uses the default concentration")
        if self.tier is not Tier.THREE and self.rate_constant not in (
            DEFAULT_K,
            DEFAULT_ARID_K,
        ):
            raise RuleError("nmoc", "only tier 3 measures the rate constant")

    def measure_concentration(self, ppmv: float) -> Inputs:
        """The same site with a concentration sampled at the wellheads."""
        return replace(self, concentration=ppmv, tier=Tier.TWO)

    def measure_rate(self, constant: float) -> Inputs:
        """The same site with a rate constant worked out from its own gas."""
        return replace(self, rate_constant=constant, tier=Tier.THREE)


@dataclass(frozen=True)
class Estimate:
    """One emission rate, with what it was worked out from."""

    inputs: Inputs
    megagrams: float

    @property
    def tier(self) -> Tier:
        """Which tier the estimate was got at."""
        return self.inputs.tier

    def over(self, standard: Standard) -> bool:
        """True when the rate is at or over the threshold in the standard."""
        return self.megagrams >= standard.nmoc_threshold_mg

    def margin(self, standard: Standard) -> float:
        """How far the rate sits over the threshold, negative when under."""
        return self.megagrams - standard.nmoc_threshold_mg


def rate(inputs: Inputs) -> Estimate:
    """Work the emission rate out of one set of inputs."""
    decayed = math.exp(-inputs.rate_constant * inputs.closed_years) - math.exp(
        -inputs.rate_constant * inputs.age
    )
    megagrams = (
        2.0
        * inputs.generation_potential
        * inputs.acceptance
        * decayed
        * inputs.concentration
        * CONVERSION
    )
    return Estimate(inputs=inputs, megagrams=megagrams)


def tier_one(acceptance: float, age: float, *, arid: bool = False) -> Estimate:
    """The rate with every default in the standard taken as written."""
    return rate(
        Inputs(
            acceptance=acceptance,
            age=age,
            rate_constant=DEFAULT_ARID_K if arid else DEFAULT_K,
        )
    )


def needed(estimate: Estimate, standard: Standard, design_capacity: float) -> bool:
    """True when the site is big enough and gassy enough to need collection.

    Both have to be true. A small landfill over the emission threshold is not
    caught, and a very large one under it is not caught either.
    """
    return design_capacity >= standard.design_capacity_mg and estimate.over(standard)


__all__ = [
    "CONVERSION",
    "DEFAULT_ARID_K",
    "DEFAULT_K",
    "DEFAULT_L0",
    "DEFAULT_NMOC",
    "Estimate",
    "Inputs",
    "Tier",
    "needed",
    "rate",
    "tier_one",
]

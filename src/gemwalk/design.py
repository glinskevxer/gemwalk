"""Whether an area has enough collection in it, and how much more it needs.

A vertical well pulls on a circle of refuse around itself. The radius depends
on how wet and how compacted the refuse is and on how hard the well is being
pulled, so it is a number the site measures and records rather than one this
package invents.

Adding the circles up and comparing them with the acreage is the crude way to
answer "is there enough collection here", and it is crude in a known direction:
circles laid out on a grid overlap, so the sum of the circles overstates the
ground actually covered. The overlap of a triangular layout at the usual
spacing is about ten percent, and that is what the packing factor is for.

The number this produces is not a regulatory finding. The regulation asks
whether collection was installed by a deadline, not whether it was installed
densely enough. What this answers is the operator's question, which is how many
more wells the hundred and twenty day window is going to have to pay for.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from gemwalk.errors import RuleError
from gemwalk.model.device import SQUARE_FEET_IN_AN_ACRE, Device
from gemwalk.model.landfill import Area

PACKING = 0.9


def acres_for(radius: float) -> float:
    """How much ground one device of this radius pulls on, in acres."""
    if radius <= 0:
        raise RuleError("design", "a radius is a real distance")
    return math.pi * radius**2 / SQUARE_FEET_IN_AN_ACRE


def wells_for(acres: float, radius: float, *, packing: float = PACKING) -> int:
    """How many devices of this radius an area of this size wants."""
    if acres <= 0:
        raise RuleError("design", "an area covers some ground")
    return math.ceil(acres / (acres_for(radius) * packing))


@dataclass(frozen=True)
class Coverage:
    """What one area has in it against what it was designed to have."""

    area: str
    acres: float
    radius: float
    devices: tuple[str, ...]
    covered: float
    wanted: int

    @property
    def share(self) -> float:
        """What share of the area the devices in it reach, capped at all of it."""
        return min(1.0, self.covered / self.acres) if self.acres > 0 else 0.0

    @property
    def short_by(self) -> int:
        """How many more devices the area wants, zero when it has enough."""
        return max(0, self.wanted - len(self.devices))

    @property
    def is_enough(self) -> bool:
        """True when the area has at least the devices it was designed for."""
        return self.short_by == 0

    def __str__(self) -> str:
        return (
            f"{self.area}: {len(self.devices)} of {self.wanted} devices, "
            f"{self.share * 100:.0f}% of {self.acres:g} acres"
        )


def coverage(area: Area, devices: list[Device], *, packing: float = PACKING) -> Coverage:
    """Read one area against the devices that are actually in it."""
    live = [device for device in devices if device.area == area.label]
    return Coverage(
        area=area.label,
        acres=area.acres,
        radius=area.target_radius,
        devices=tuple(device.label for device in live),
        covered=sum(device.acres_pulled for device in live) * packing,
        wanted=wells_for(area.acres, area.target_radius, packing=packing),
    )


__all__ = ["PACKING", "Coverage", "acres_for", "coverage", "wells_for"]

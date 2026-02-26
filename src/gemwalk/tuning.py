"""What to do to the valve, worked out from what the wellhead read.

This is the part of the job that is judgement rather than regulation, and the
judgement is mostly one idea applied in two directions. A well that is being
pulled too hard drags air in through the cover and heats up, and both of those
show in the analysis. A well that is not being pulled hard enough sits at or
above atmosphere and lets gas out through the cover instead, which shows on the
gauge.

So the same wellhead can be over pulled and under pulled in the same month at
different valve positions, and the numbers that say which are not the same
numbers the regulation looks at. Temperature is on both lists. Oxygen is on
both lists. Pressure is on both lists. What differs is which way they point.

Two cases have no valve answer at all and it is important not to give them one.
A well standing full of water is not a valve problem, and turning it will not
change the reading. A well whose four gas figures do not add up has not been
measured, and acting on a number nobody can defend is worse than acting on
nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from gemwalk.model.device import Device
from gemwalk.model.reading import Reading
from gemwalk.quality import Character
from gemwalk.rules import Standard

CLOSE_STEP = 0.5
OPEN_STEP = 0.5
BIG_STEP = 1.0
HOT_MARGIN = 5.0


class Move(Enum):
    """Which way the valve should go, if it should go anywhere."""

    CLOSE = "close in"
    OPEN = "open up"
    HOLD = "leave it where it is"
    SHUT = "shut it in"
    NONE = "no valve move will help this"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Advice:
    """One wellhead, one thing to do to it, and why."""

    device: str
    move: Move
    turns: float
    because: str

    @property
    def is_action(self) -> bool:
        """True when somebody has to touch the valve."""
        return self.move in (Move.CLOSE, Move.OPEN, Move.SHUT)

    def position(self, reading: Reading) -> float:
        """Where the valve would end up, kept on the stem."""
        if self.move is Move.CLOSE:
            return max(0.0, reading.valve_after - self.turns)
        if self.move is Move.OPEN:
            return min(10.0, reading.valve_after + self.turns)
        if self.move is Move.SHUT:
            return 0.0
        return reading.valve_after

    def __str__(self) -> str:
        if not self.is_action:
            return f"{self.device}: {self.move} ({self.because})"
        return f"{self.device}: {self.move} {self.turns:g} turns ({self.because})"


def advise(
    reading: Reading,
    device: Device,
    standard: Standard,
    *,
    flooded: bool = False,
) -> Advice:
    """Say what to do to one wellhead's valve, and why."""
    analysis = reading.analysis
    if not reading.balances:
        return Advice(reading.device, Move.NONE, 0.0, "the four gas figures do not add up")
    if flooded:
        return Advice(reading.device, Move.NONE, 0.0, "it is standing full of water, so dewater it")
    limit = device.temperature_limit(standard, reading.taken_on)
    if reading.temperature > limit.fahrenheit:
        return Advice(
            reading.device,
            Move.CLOSE,
            BIG_STEP,
            f"{reading.wellhead_temperature} is over the {limit} limit",
        )
    if analysis.character() is Character.AIR:
        return Advice(
            reading.device,
            Move.CLOSE,
            BIG_STEP if reading.oxygen > standard.oxygen_limit.value else CLOSE_STEP,
            f"{analysis.air:.1f}% of the sample is air",
        )
    if analysis.character() is Character.STARVED:
        return Advice(
            reading.device,
            Move.CLOSE,
            CLOSE_STEP,
            f"{analysis.excess_nitrogen:.1f}% nitrogen with no oxygen behind it",
        )
    if reading.gauge.is_positive:
        return Advice(
            reading.device,
            Move.OPEN,
            OPEN_STEP,
            f"the wellhead is at {reading.gauge}, so gas is going out through the cover",
        )
    if reading.temperature > limit.fahrenheit - HOT_MARGIN:
        return Advice(
            reading.device,
            Move.CLOSE,
            CLOSE_STEP,
            f"{reading.wellhead_temperature} is within {HOT_MARGIN:g} of the {limit} limit",
        )
    if analysis.character() is Character.THIN and reading.flow > 0:
        return Advice(reading.device, Move.SHUT, 0.0, "it is giving almost no methane at all")
    return Advice(reading.device, Move.HOLD, 0.0, "nothing about it wants moving")


def plan(readings: list[tuple[Reading, Device, bool]], standard: Standard) -> list[Advice]:
    """Advise a whole run, the wellheads that need touching first."""
    given = [
        advise(reading, device, standard, flooded=flooded) for reading, device, flooded in readings
    ]
    order = {Move.CLOSE: 0, Move.OPEN: 1, Move.SHUT: 2, Move.NONE: 3, Move.HOLD: 4}
    return sorted(given, key=lambda a: (order[a.move], -a.turns, a.device))


__all__ = ["BIG_STEP", "CLOSE_STEP", "HOT_MARGIN", "OPEN_STEP", "Advice", "Move", "advise", "plan"]

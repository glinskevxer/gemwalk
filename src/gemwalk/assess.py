"""Reading one wellhead reading against the standard the site is run under.

This is the only place in the package where a number is compared with a limit.
It touches no book and no clock: hand it a reading, the device it came off, the
standard and what the site has elected, and it says what is over.

Three of the comparisons are the regulation's and one is not.

The temperature comparison uses the device's own limit, which is the standard's
unless a higher operating value has been approved for that wellhead and the day
of the reading is on or after the day it was approved.

The oxygen comparison is the one that moves. Under the older standard it is
always oxygen against five percent. Under the newer ones the site may elect to
read nitrogen against twenty instead, and nitrogen is not measured: it is the
balance left after methane, carbon dioxide and oxygen. So electing the
alternative moves the limit onto a number the analyser derived, and a sheet
whose four figures do not add up to a hundred is a sheet whose nitrogen figure
means nothing.

The pressure comparison is against zero, and a wellhead at exactly zero is
over. Under the newer standards a site with an approved alternative may run a
wellhead at or above atmosphere in specified conditions, and then the
comparison is not made at all.

The fourth is the package's own, and it produces concerns rather than findings.
A concern is never reported to anybody: it is what the desk looks at before it
believes the other three.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum

from gemwalk.model.device import Device
from gemwalk.model.reading import Reading
from gemwalk.rules import Election, Finding, Standard


class Concern(Enum):
    """Something about a reading that makes the desk look at it twice."""

    UNBALANCED = "the four gas figures do not add up"
    SHUT = "the wellhead was left shut"
    NO_FLOW = "gas in the wellhead and nothing coming out"
    DEAD = "no methane at all"
    RICH_AIR = "oxygen high enough to be an air leak at the fitting"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Judgement:
    """One comparison of one number against one limit."""

    finding: Finding
    value: float
    limit: float
    over: bool
    citation: str
    words: str

    def __str__(self) -> str:
        return self.words


@dataclass(frozen=True)
class Assessment:
    """Everything one reading says about one wellhead."""

    device: str
    taken_on: dt.date
    judgements: tuple[Judgement, ...]
    concerns: tuple[Concern, ...]

    @property
    def exceedances(self) -> tuple[Judgement, ...]:
        """The comparisons that came out over the limit."""
        return tuple(j for j in self.judgements if j.over)

    @property
    def is_clear(self) -> bool:
        """True when nothing on this wellhead is over a limit."""
        return not self.exceedances

    def of(self, finding: Finding) -> Judgement | None:
        """The comparison for one kind of finding, if it was made."""
        for judgement in self.judgements:
            if judgement.finding is finding:
                return judgement
        return None

    @property
    def kinds(self) -> tuple[Finding, ...]:
        """The kinds of finding this reading is over on, in report order."""
        return tuple(j.finding for j in self.exceedances)


def _temperature(reading: Reading, device: Device, standard: Standard) -> Judgement:
    limit = device.temperature_limit(standard, reading.taken_on)
    over = reading.temperature > limit.fahrenheit
    return Judgement(
        finding=Finding.TEMPERATURE,
        value=reading.temperature,
        limit=limit.fahrenheit,
        over=over,
        citation=standard.citation,
        words=(
            f"{reading.wellhead_temperature} at the wellhead against a {limit} limit"
            if over
            else f"{reading.wellhead_temperature}, under the {limit} limit"
        ),
    )


def _oxygen(reading: Reading, standard: Standard, election: Election) -> Judgement:
    if election.nitrogen_alternative and standard.nitrogen_limit is not None:
        limit = standard.nitrogen_limit
        over = reading.balance > limit.value
        return Judgement(
            finding=Finding.NITROGEN,
            value=reading.balance,
            limit=limit.value,
            over=over,
            citation=standard.citation,
            words=(
                f"nitrogen {reading.nitrogen} off the balance against a {limit} limit"
                if over
                else f"nitrogen {reading.nitrogen}, under the {limit} limit"
            ),
        )
    limit = standard.oxygen_limit
    over = reading.oxygen > limit.value
    return Judgement(
        finding=Finding.OXYGEN,
        value=reading.oxygen,
        limit=limit.value,
        over=over,
        citation=standard.citation,
        words=(
            f"oxygen {reading.oxygen_reading} against a {limit} limit"
            if over
            else f"oxygen {reading.oxygen_reading}, under the {limit} limit"
        ),
    )


def _pressure(reading: Reading, standard: Standard) -> Judgement:
    limit = standard.pressure_limit
    over = reading.gauge.is_positive
    return Judgement(
        finding=Finding.PRESSURE,
        value=reading.static,
        limit=limit.inches,
        over=over,
        citation=standard.citation,
        words=(
            f"wellhead at {reading.gauge}, which is not under vacuum"
            if over
            else f"wellhead at {reading.gauge}"
        ),
    )


def concerns(reading: Reading) -> tuple[Concern, ...]:
    """Everything about a reading that makes the desk look at it twice."""
    found: list[Concern] = []
    if not reading.balances:
        found.append(Concern.UNBALANCED)
    if reading.is_shut:
        found.append(Concern.SHUT)
    elif reading.methane > 0 and reading.flow == 0:
        found.append(Concern.NO_FLOW)
    if reading.methane == 0:
        found.append(Concern.DEAD)
    if reading.oxygen >= 10.0:
        found.append(Concern.RICH_AIR)
    return tuple(found)


def assess(
    reading: Reading,
    device: Device,
    standard: Standard,
    election: Election | None = None,
) -> Assessment:
    """Read one wellhead reading against the standard the site is run under."""
    chosen = election or Election()
    judgements = [
        _temperature(reading, device, standard),
        _oxygen(reading, standard, chosen),
    ]
    if not (chosen.higher_pressure and standard.allows_higher_pressure):
        judgements.append(_pressure(reading, standard))
    return Assessment(
        device=reading.device,
        taken_on=reading.taken_on,
        judgements=tuple(judgements),
        concerns=concerns(reading),
    )


__all__ = ["Assessment", "Concern", "Election", "Judgement", "assess", "concerns"]

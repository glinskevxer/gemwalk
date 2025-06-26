"""The landfill, and the areas waste was put into.

An area is the unit the collection deadline is counted against. The regulation
does not ask when the landfill opened, it asks when waste was first placed in
*this* area, and then it asks whether the area is still taking waste: an active
area has five years to have collection in it and a closed one has two. So an
area that stopped taking waste can have a deadline that lands earlier than one
next to it that started later.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import Enum

from gemwalk.errors import OrderError, RuleError
from gemwalk.rules import Election, Standard


class Cover(Enum):
    """What is on top of an area, which is what a surface reading crosses."""

    DAILY = "daily"
    INTERMEDIATE = "intermediate"
    FINAL = "final"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Site:
    """One landfill, subject to one standard, on one wall clock."""

    label: str
    name: str
    standard: str
    permit: str
    zone: str
    design_capacity: float
    opened_on: dt.date
    closed_on: dt.date | None = None
    nitrogen_alternative: bool = False
    higher_pressure: bool = False
    elected_on: dt.date | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise RuleError("site", "a site needs a label")
        if self.design_capacity <= 0:
            raise RuleError("site", "a design capacity has to be a real tonnage")
        if self.closed_on is not None and self.closed_on < self.opened_on:
            raise OrderError("site", str(self.opened_on), str(self.closed_on))

    @property
    def is_closed(self) -> bool:
        """True once the site has stopped taking waste altogether."""
        return self.closed_on is not None

    def is_open_on(self, day: dt.date) -> bool:
        """True when the site was taking waste on *day*."""
        if day < self.opened_on:
            return False
        return self.closed_on is None or day <= self.closed_on

    def close(self, on: dt.date) -> Site:
        """The same site, recorded as having stopped taking waste."""
        if self.is_closed:
            raise RuleError("site", f"{self.label} closed on {self.closed_on}")
        return replace(self, closed_on=on)

    def over_design_capacity(self, standard: Standard) -> bool:
        """True when the site is big enough for the standard to reach it."""
        return self.design_capacity >= standard.design_capacity_mg

    def election(self, standard: Standard, on: dt.date | None = None) -> Election:
        """What the site has elected, as the assessment reads it.

        An election is only worth anything where the standard offers it, and
        only from the day it was made. A site that elected the nitrogen
        alternative and then moved under a standard that has none reads back as
        having elected nothing.
        """
        if self.elected_on is None:
            return Election()
        if on is not None and on < self.elected_on:
            return Election()
        return Election(
            nitrogen_alternative=self.nitrogen_alternative and standard.allows_nitrogen,
            higher_pressure=self.higher_pressure and standard.allows_higher_pressure,
        )

    def elect(
        self,
        on: dt.date,
        *,
        nitrogen_alternative: bool = False,
        higher_pressure: bool = False,
    ) -> Site:
        """Record what the site has chosen where the standard leaves a choice."""
        if on < self.opened_on:
            raise OrderError("election", str(self.opened_on), str(on))
        return replace(
            self,
            nitrogen_alternative=nitrogen_alternative,
            higher_pressure=higher_pressure,
            elected_on=on,
        )


@dataclass(frozen=True)
class Area:
    """One filling area, with the dates the collection deadline counts from."""

    label: str
    site: str
    name: str
    acres: float
    first_waste: dt.date
    last_waste: dt.date | None = None
    closed_on: dt.date | None = None
    cover: Cover = Cover.DAILY

    def __post_init__(self) -> None:
        if self.acres <= 0:
            raise RuleError("area", "an area covers some ground")
        if self.last_waste is not None and self.last_waste < self.first_waste:
            raise OrderError("area", str(self.first_waste), str(self.last_waste))
        if self.closed_on is not None:
            if self.last_waste is None:
                raise RuleError("area", "an area cannot be closed while it is still taking waste")
            if self.closed_on < self.last_waste:
                raise OrderError("area", str(self.last_waste), str(self.closed_on))

    @property
    def is_closed(self) -> bool:
        """True once final cover has gone on and the area is shut."""
        return self.closed_on is not None

    @property
    def is_filling(self) -> bool:
        """True while waste is still going into the area."""
        return self.last_waste is None

    def install_due(self, standard: Standard) -> dt.date:
        """The last day collection has to be in the ground in this area.

        A filling area gets the long window counted from first waste. Once the
        area is closed the short window applies instead, counted from the day
        the last load went in, and it can land earlier than the long one.
        """
        if self.is_closed:
            last = self.last_waste or self.first_waste
            return _add_years(last, standard.closed_install_years)
        return _add_years(self.first_waste, standard.active_install_years)

    def stop_filling(self, on: dt.date) -> Area:
        """The same area, recorded as having taken its last load."""
        if not self.is_filling:
            raise RuleError("area", f"{self.label} stopped taking waste on {self.last_waste}")
        return replace(self, last_waste=on)

    def close(self, on: dt.date, cover: Cover = Cover.FINAL) -> Area:
        """The same area, recorded as closed under the cover that went on."""
        if self.is_filling:
            raise RuleError("area", f"{self.label} is still taking waste")
        if self.is_closed:
            raise RuleError("area", f"{self.label} closed on {self.closed_on}")
        return replace(self, closed_on=on, cover=cover)


def _add_years(day: dt.date, years: int) -> dt.date:
    """The same day and month *years* on, with the leap day pulled back a day."""
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, day=day.day - 1)


__all__ = ["Area", "Cover", "Site"]

"""Dewatering: what is under water, what needs pumping, and what was hauled.

The desk is where the liquid record meets the gas record. A well that read no
flow and a lot of air is either leaking at the fitting or standing full of
water, and those are two completely different jobs. The tape drop is what tells
them apart, so the desk will say which of the two a wellhead's concerns are
consistent with rather than leaving it to whoever reads the report.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from gemwalk.assess import Concern
from gemwalk.errors import RuleError, StateError
from gemwalk.ids import Labels
from gemwalk.model.device import Device, State
from gemwalk.model.liquids import Level, Pumpout, Sump, SumpKind
from gemwalk.service.sites import SiteDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.store.book import Book
from gemwalk.store.liquids import LevelRepository, PumpoutRepository, SumpRepository

DEWATER_SHARE = 0.5


@dataclass(frozen=True)
class Water:
    """What is standing in one well, worked out against its construction."""

    device: Device
    level: Level
    column: float
    submerged: float
    share: float
    flooded: bool

    @property
    def needs_pumping(self) -> bool:
        """True when enough of the screen is under water to be worth a pump."""
        return self.share >= DEWATER_SHARE


class LiquidsDesk:
    """The tape drops, the sumps and the loads hauled off them."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.sumps = SumpRepository(book)
        self.levels = LevelRepository(book)
        self.pumpouts = PumpoutRepository(book)
        self.wellfield = WellfieldDesk(book)
        self.sites = SiteDesk(book)
        self.labels = Labels(book)

    def add_sump(
        self,
        site: str,
        station: str,
        *,
        kind: SumpKind = SumpKind.KNOCKOUT,
        capacity: float,
        on: dt.date,
    ) -> Sump:
        """Put a condensate catcher on the pipe tree."""
        self.sites.sites.get(site)
        with self.book.writing():
            sump = Sump(
                label=self.labels.next("sump", on),
                site=site,
                station=station,
                kind=kind,
                capacity=capacity,
                installed_on=on,
            )
            return self.sumps.add(sump)

    def retire_sump(self, label: str, on: dt.date) -> Sump:
        """Take a condensate catcher off the pipe tree."""
        sump = self.sumps.get(label)
        with self.book.writing():
            return self.sumps.put(sump.retire(on))

    def tape(
        self,
        device: str,
        on: dt.date,
        depth: float,
        *,
        pumped: bool = False,
        note: str = "",
    ) -> Level:
        """Write down a tape drop at one well."""
        found = self.wellfield.devices.get(device)
        if found.state is State.ABANDONED:
            raise StateError(device, "abandoned", "in service")
        if depth > found.total_depth:
            raise RuleError(
                "level",
                f"a tape at {depth:g} ft is below the bottom of a {found.total_depth:g} ft hole",
            )
        if on < found.drilled_on:
            raise RuleError("level", f"{device} was not drilled until {found.drilled_on}")
        with self.book.writing():
            return self.levels.add(
                Level(device=device, taken_on=on, depth=depth, pumped=pumped, note=note)
            )

    def water_in(self, device: str, on: dt.date) -> Water | None:
        """What was standing in one well as of a day, if it was ever tapped."""
        found = self.wellfield.devices.get(device)
        level = self.levels.latest_for(device, on)
        if level is None:
            return None
        return Water(
            device=found,
            level=level,
            column=level.liquid_column(found),
            submerged=level.submerged(found),
            share=level.submerged_share(found),
            flooded=level.is_flooded(found),
        )

    def standing(self, site: str, on: dt.date) -> list[Water]:
        """What is standing in every well at a site, wettest first."""
        found: list[Water] = []
        for device in self.wellfield.devices.of_site(site):
            if device.state is State.ABANDONED:
                continue
            water = self.water_in(device.label, on)
            if water is not None:
                found.append(water)
        return sorted(found, key=lambda w: (-w.share, w.device.label))

    def flooded(self, site: str, on: dt.date) -> list[Water]:
        """Every well at a site standing full to the top of its screen."""
        return [water for water in self.standing(site, on) if water.flooded]

    def dewater_list(self, site: str, on: dt.date) -> list[Water]:
        """Every well wet enough to be worth putting a pump in."""
        return [water for water in self.standing(site, on) if water.needs_pumping]

    def explains(self, device: str, on: dt.date, concerns: tuple[Concern, ...]) -> str | None:
        """Say whether water accounts for what the gas reading looked like.

        A dead wellhead with no flow reads the same whether it is under water or
        leaking at the fitting. This is the one number that tells them apart, so
        it says which, rather than leaving the report to imply either.
        """
        wanted = (Concern.NO_FLOW, Concern.DEAD, Concern.RICH_AIR)
        if not any(concern in concerns for concern in wanted):
            return None
        water = self.water_in(device, on)
        if water is None:
            return "no tape drop on file, so the reading is unexplained"
        if water.flooded:
            return f"under water: {water.column:.1f} ft standing, the whole screen covered"
        if water.needs_pumping:
            return f"part flooded: {water.share * 100:.0f}% of the screen under water"
        return "the well is not under water, so look at the seal and the fittings"

    def pump(
        self,
        sump: str,
        at: dt.datetime,
        gallons: float,
        *,
        hauler: str,
        bound_for: str,
        note: str = "",
    ) -> Pumpout:
        """Write down a load taken off a sump."""
        found = self.sumps.get(sump)
        if not found.is_live:
            raise StateError(sump, "retired", "live")
        with self.book.writing():
            return self.pumpouts.add(
                Pumpout(
                    sump=sump,
                    at=at,
                    gallons=gallons,
                    hauler=hauler,
                    bound_for=bound_for,
                    note=note,
                )
            )

    def hauled(self, site: str, first: dt.datetime, last: dt.datetime) -> float:
        """How many gallons came off every sump at a site in a range."""
        return sum(
            self.pumpouts.gallons_between(sump.label, first, last)
            for sump in self.sumps.of_site(site)
        )

    def by_hauler(self, first: dt.datetime, last: dt.datetime) -> dict[str, float]:
        """How many gallons each hauler took in a range, biggest first."""
        tally: dict[str, float] = {}
        for load in self.pumpouts.between(first, last):
            tally[load.hauler] = tally.get(load.hauler, 0.0) + load.gallons
        return dict(sorted(tally.items(), key=lambda pair: (-pair[1], pair[0])))


__all__ = ["DEWATER_SHARE", "LiquidsDesk", "Water"]

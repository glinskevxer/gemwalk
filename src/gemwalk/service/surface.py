"""Running a walkover, marking what it finds, and working the marks off.

The desk knows two things the model does not. It knows which walk is open, so a
mark goes onto the right one, and it knows the site's standard, so it can say
whether a reading is a hit at all.

Whether a reading is a hit is not a property of the reading. The limit is five
hundred parts per million above the background the crew measured that morning,
so the same number is a hit on one walk and not on the next.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from gemwalk.clock import Quarter
from gemwalk.errors import RuleError, StateError
from gemwalk.ids import Labels
from gemwalk.model.landfill import Cover
from gemwalk.model.surface import Hit, Step, Walk
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book
from gemwalk.store.surface import HitRepository, WalkRepository


@dataclass(frozen=True)
class Mark:
    """One open spot and where its clock has got to."""

    hit: Hit
    due: dt.date
    days_left: int
    late: bool


class SurfaceDesk:
    """The quarterly walkovers and the spots they leave behind."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.walks = WalkRepository(book)
        self.hits = HitRepository(book)
        self.sites = SiteDesk(book)
        self.labels = Labels(book)

    def open_walk(
        self,
        site: str,
        on: dt.date,
        *,
        monitor: str,
        instrument: str,
        background: float,
        wind_mean: float,
        wind_gust: float,
        spacing: float = 30.0,
    ) -> Walk:
        """Start a walkover of the cover."""
        self.sites.sites.get(site)
        already = self.walks.open_walks(site)
        if already:
            names = ", ".join(w.label for w in already)
            raise RuleError("walk", f"{names} is still open at {site}")
        with self.book.writing():
            walk = Walk(
                label=self.labels.next("walk", on),
                site=site,
                quarter=Quarter.of(on),
                started_on=on,
                monitor=monitor,
                instrument=instrument,
                background=background,
                wind_mean=wind_mean,
                wind_gust=wind_gust,
                spacing=spacing,
            )
            return self.walks.add(walk)

    def mark(
        self,
        walk: str,
        area: str,
        station: str,
        reading: float,
        *,
        on: dt.date,
        cover: Cover = Cover.INTERMEDIATE,
        note: str = "",
    ) -> Hit:
        """Write down a spot the detector read over the limit."""
        pass_ = self.walks.get(walk)
        if not pass_.is_open:
            raise StateError(walk, "finished", "open")
        found = self.sites.areas.get(area)
        if found.site != pass_.site:
            raise RuleError("hit", f"{area} is not an area of {pass_.site}")
        subpart = self.sites.standard_of(pass_.site)
        if not pass_.is_over(reading, subpart):
            raise RuleError(
                "hit",
                f"{reading:g} ppmv is under the {pass_.limit(subpart)} this walk is measured to",
            )
        if on < pass_.started_on:
            raise RuleError("hit", f"{walk} did not start until {pass_.started_on}")
        with self.book.writing():
            hit = Hit(
                label=self.labels.next("hit", on),
                walk=walk,
                site=pass_.site,
                area=area,
                station=station,
                reading=reading,
                cover=cover,
                found_on=on,
                note=note,
            )
            return self.hits.add(hit)

    def finish_walk(self, walk: str, on: dt.date) -> Walk:
        """Close a walkover off once the whole cover has been crossed."""
        pass_ = self.walks.get(walk)
        with self.book.writing():
            return self.walks.put(pass_.finish(on))

    def repair(self, hit: str, on: dt.date, note: str = "") -> Hit:
        """Record the cover work on a spot and start its remonitor window."""
        found = self.hits.get(hit)
        with self.book.writing():
            return self.hits.put(found.repair(on, note))

    def remonitor(self, hit: str, on: dt.date, reading: float, note: str = "") -> Hit:
        """Read a repaired spot again and take it wherever the number says."""
        found = self.hits.get(hit)
        walk = self.walks.get(found.walk)
        subpart = self.sites.standard_of(found.site)
        with self.book.writing():
            if walk.is_over(reading, subpart):
                return self.hits.put(found.still_over(subpart, on, note))
            return self.hits.put(found.clear(on, note))

    def board(self, site: str, on: dt.date) -> list[Mark]:
        """Every open spot at a site, the least time left first."""
        subpart = self.sites.standard_of(site)
        marks: list[Mark] = []
        for hit in self.hits.open_at(site):
            due = hit.due(subpart)
            if due is None:
                continue
            marks.append(
                Mark(hit=hit, due=due, days_left=(due - on).days, late=hit.is_late(subpart, on))
            )
        return sorted(marks, key=lambda m: (m.days_left, m.hit.label))

    def overdue(self, site: str, on: dt.date) -> list[Mark]:
        """Every open spot whose current window has already run out."""
        return [mark for mark in self.board(site, on) if mark.late]

    def invalid_walks(self, site: str) -> list[Walk]:
        """Every walk whose own conditions throw its readings out."""
        subpart = self.sites.standard_of(site)
        return [w for w in self.walks.of_site(site) if not w.is_valid(subpart)]

    def quarters_missed(self, site: str, first: Quarter, last: Quarter) -> list[Quarter]:
        """Every quarter in a range with no valid finished walk in it."""
        subpart = self.sites.standard_of(site)
        missed: list[Quarter] = []
        quarter = first
        while quarter <= last:
            walks = [
                w
                for w in self.walks.in_quarter(site, quarter)
                if not w.is_open and w.is_valid(subpart)
            ]
            if not walks:
                missed.append(quarter)
            quarter = quarter.next
        return missed

    def repeat_stations(self, site: str, since: dt.date) -> dict[str, int]:
        """Places on the cover that have been marked more than once."""
        tally: dict[str, int] = {}
        for hit in self.hits.between_days(site, since.isoformat(), "9999-12-31"):
            tally[hit.station] = tally.get(hit.station, 0) + 1
        return {station: count for station, count in sorted(tally.items()) if count > 1}

    def waiting_on(self, site: str, step: Step) -> list[Hit]:
        """Every spot at one site waiting on one kind of work."""
        return self.hits.at_step(site, step)


__all__ = ["Mark", "SurfaceDesk"]

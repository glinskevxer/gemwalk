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
from gemwalk.model.route import Covered, Leg, Route, pattern_for
from gemwalk.model.surface import Hit, Step, Walk
from gemwalk.service.instruments import InstrumentDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book
from gemwalk.store.route import CoveredRepository, LegRepository
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
        self.legs = LegRepository(book)
        self.covered = CoveredRepository(book)
        self.sites = SiteDesk(book)
        self.instruments = InstrumentDesk(book)
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
        """Start a walkover of the cover.

        A detector the book knows about has to have been calibrated that day.
        The regulation is explicit about this one: the readings off an
        uncalibrated detector are not evidence of anything, and a walk made
        with one has to be done again.
        """
        self.sites.sites.get(site)
        if self.instruments.instruments.find(instrument) is not None:
            self.instruments.must_be_good(instrument, on)
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

    def lay_pattern(self, area: str, *, legs: int, metres: float) -> list[Leg]:
        """Lay a numbered pattern of legs across one area."""
        found = self.sites.areas.get(area)
        made: list[Leg] = []
        with self.book.writing():
            already = len(self.legs.of_area(area))
            for number in range(already + 1, already + legs + 1):
                made.append(
                    self.legs.add(
                        Leg(
                            label=f"{area}-L{number:02d}",
                            site=found.site,
                            area=area,
                            name=f"line {number} across {found.name}",
                            metres=metres,
                        )
                    )
                )
        return made

    def wanted_legs(self, area: str, metres: float) -> int:
        """How many legs of a given length the pattern over an area needs."""
        found = self.sites.areas.get(area)
        return pattern_for(found.acres, self.sites.standard_of(found.site), metres)

    def cross(self, walk: str, leg: str, note: str = "") -> Covered:
        """Record that a walk crossed one leg of the pattern."""
        pass_ = self.walks.get(walk)
        found = self.legs.get(leg)
        if found.site != pass_.site:
            raise RuleError("leg", f"{leg} is not a leg at {pass_.site}")
        if not pass_.is_open:
            raise StateError(walk, "finished", "open")
        with self.book.writing():
            return self.covered.add(Covered(walk=walk, leg=leg, note=note))

    def route_of(self, walk: str, area: str) -> Route:
        """The pattern over one area, and how much of it a walk covered."""
        pass_ = self.walks.get(walk)
        found = self.sites.areas.get(area)
        crossed = self.covered.labels_of(walk)
        legs = tuple(self.legs.live_in(area))
        del pass_
        return Route(
            area=area,
            acres=found.acres,
            legs=legs,
            walked=tuple(label for label in crossed if label in {leg.label for leg in legs}),
        )

    def routes_of(self, walk: str) -> list[Route]:
        """The pattern over every area of the site, as one walk covered it."""
        pass_ = self.walks.get(walk)
        return [self.route_of(walk, area.label) for area in self.sites.areas_of(pass_.site)]

    def incomplete(self, walk: str) -> list[Route]:
        """Every area whose pattern this walk did not cross whole.

        An area with no pattern laid out is not listed. Nobody said what a
        whole walk of it was, so nothing can say the walk fell short of it, and
        pretending otherwise would make every site with no pattern look like a
        site that missed everything.
        """
        return [route for route in self.routes_of(walk) if route.legs and not route.is_whole]

    def covered_whole(self, walk: str) -> bool:
        """True when the walk crossed every leg of every pattern there is."""
        return not self.incomplete(walk)

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
                if not w.is_open and w.is_valid(subpart) and self.covered_whole(w.label)
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

"""Rows of the walk and hit tables."""

from __future__ import annotations

from typing import Any, ClassVar

from gemwalk.clock import Quarter, read_day
from gemwalk.model.landfill import Cover
from gemwalk.model.surface import Hit, Step, Walk
from gemwalk.store.book import Row
from gemwalk.store.columns import day_text, read_day_or_none
from gemwalk.store.repo import Repository


class WalkRepository(Repository[Walk]):
    """Every quarterly pass over the cover."""

    table: ClassVar[str] = "walk"
    kind: ClassVar[str] = "walk"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "quarter",
        "started_on",
        "finished_on",
        "monitor",
        "instrument",
        "background",
        "wind_mean",
        "wind_gust",
        "spacing",
        "note",
    )

    def read(self, row: Row) -> Walk:
        """Turn one walk row into a walk."""
        return Walk(
            label=str(row["label"]),
            site=str(row["site"]),
            quarter=Quarter.parse(str(row["quarter"])),
            started_on=read_day(str(row["started_on"])),
            finished_on=read_day_or_none(row["finished_on"]),
            monitor=str(row["monitor"]),
            instrument=str(row["instrument"]),
            background=float(row["background"]),
            wind_mean=float(row["wind_mean"]),
            wind_gust=float(row["wind_gust"]),
            spacing=float(row["spacing"]),
            note=str(row["note"]),
        )

    def write(self, item: Walk) -> dict[str, Any]:
        """Turn one walk into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "quarter": str(item.quarter),
            "started_on": day_text(item.started_on),
            "finished_on": day_text(item.finished_on),
            "monitor": item.monitor,
            "instrument": item.instrument,
            "background": item.background,
            "wind_mean": item.wind_mean,
            "wind_gust": item.wind_gust,
            "spacing": item.spacing,
            "note": item.note,
        }

    def of_site(self, site: str) -> list[Walk]:
        """Every walk at one site."""
        return self.where("site = ?", (site,))

    def in_quarter(self, site: str, quarter: Quarter) -> list[Walk]:
        """Every walk at one site inside one quarter."""
        return self.where("site = ? AND quarter = ?", (site, str(quarter)))

    def open_walks(self, site: str) -> list[Walk]:
        """Every walk at one site the crew has not finished."""
        return self.where("site = ? AND finished_on IS NULL", (site,))


class HitRepository(Repository[Hit]):
    """Every spot on the cover that read over the limit."""

    table: ClassVar[str] = "hit"
    kind: ClassVar[str] = "hit"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "walk",
        "site",
        "area",
        "station",
        "reading",
        "cover",
        "found_on",
        "stage",
        "attempt",
        "repaired_on",
        "remonitor_on",
        "closed_on",
        "note",
    )

    def read(self, row: Row) -> Hit:
        """Turn one hit row into a hit."""
        return Hit(
            label=str(row["label"]),
            walk=str(row["walk"]),
            site=str(row["site"]),
            area=str(row["area"]),
            station=str(row["station"]),
            reading=float(row["reading"]),
            cover=Cover(str(row["cover"])),
            found_on=read_day(str(row["found_on"])),
            step=Step(str(row["stage"])),
            attempt=int(row["attempt"]),
            repaired_on=read_day_or_none(row["repaired_on"]),
            remonitor_on=read_day_or_none(row["remonitor_on"]),
            closed_on=read_day_or_none(row["closed_on"]),
            note=str(row["note"]),
        )

    def write(self, item: Hit) -> dict[str, Any]:
        """Turn one hit into the column values it is stored as."""
        return {
            "label": item.label,
            "walk": item.walk,
            "site": item.site,
            "area": item.area,
            "station": item.station,
            "reading": item.reading,
            "cover": item.cover.value,
            "found_on": day_text(item.found_on),
            "stage": item.step.value,
            "attempt": item.attempt,
            "repaired_on": day_text(item.repaired_on),
            "remonitor_on": day_text(item.remonitor_on),
            "closed_on": day_text(item.closed_on),
            "note": item.note,
        }

    def of_walk(self, walk: str) -> list[Hit]:
        """Every spot one walk found."""
        return self.where("walk = ?", (walk,))

    def open_at(self, site: str) -> list[Hit]:
        """Every spot at one site that still needs work."""
        return self.where("site = ? AND stage != ?", (site, Step.CLOSED.value))

    def of_area(self, area: str) -> list[Hit]:
        """Every spot ever found in one filling area."""
        return self.where("area = ?", (area,))

    def at_step(self, site: str, step: Step) -> list[Hit]:
        """Every spot at one site waiting on one kind of work."""
        return self.where("site = ? AND stage = ?", (site, step.value))

    def found_between(self, site: str, first: str, last: str) -> list[Hit]:
        """Every spot at one site found inside a range of days."""
        rows = self.book.all(
            "SELECT * FROM hit WHERE site = ? AND found_on >= ? AND found_on <= ? "
            "ORDER BY found_on, label",
            (site, first, last),
        )
        return [self.read(row) for row in rows]

    def at_station(self, site: str, station: str) -> list[Hit]:
        """Every spot ever found at one place on the cover, oldest first."""
        rows = self.book.all(
            "SELECT * FROM hit WHERE site = ? AND station = ? ORDER BY found_on, label",
            (site, station),
        )
        return [self.read(row) for row in rows]


__all__ = ["HitRepository", "WalkRepository"]

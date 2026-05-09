"""Rows of the fault table."""

from __future__ import annotations

from typing import Any, ClassVar

from gemwalk.clock import read_day
from gemwalk.model.fault import Damage, Fault
from gemwalk.store.book import Row
from gemwalk.store.columns import day_text, read_day_or_none
from gemwalk.store.repo import Repository


class FaultRepository(Repository[Fault]):
    """Everything anybody has found wrong with the cover."""

    table: ClassVar[str] = "fault"
    kind: ClassVar[str] = "fault"
    day_column: ClassVar[str] = "found_on"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "area",
        "kind",
        "station",
        "extent",
        "found_on",
        "found_by",
        "fixed_on",
        "note",
    )

    def read(self, row: Row) -> Fault:
        """Turn one fault row into a fault."""
        return Fault(
            label=str(row["label"]),
            site=str(row["site"]),
            area=str(row["area"]),
            kind=Damage(str(row["kind"])),
            station=str(row["station"]),
            extent=float(row["extent"]),
            found_on=read_day(str(row["found_on"])),
            found_by=str(row["found_by"]),
            fixed_on=read_day_or_none(row["fixed_on"]),
            note=str(row["note"]),
        )

    def write(self, item: Fault) -> dict[str, Any]:
        """Turn one fault into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "area": item.area,
            "kind": item.kind.value,
            "station": item.station,
            "extent": item.extent,
            "found_on": day_text(item.found_on),
            "found_by": item.found_by,
            "fixed_on": day_text(item.fixed_on),
            "note": item.note,
        }

    def open_at(self, site: str) -> list[Fault]:
        """Every fault at a site the cover still has."""
        return self.where("site = ? AND fixed_on IS NULL", (site,))

    def of_area(self, area: str) -> list[Fault]:
        """Every fault ever found in one area."""
        return self.where("area = ?", (area,))

    def of_kind(self, site: str, kind: Damage) -> list[Fault]:
        """Every fault at one site of one kind."""
        return self.where("site = ? AND kind = ?", (site, kind.value))


__all__ = ["FaultRepository"]

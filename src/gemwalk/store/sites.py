"""Rows of the site and area tables."""

from __future__ import annotations

from typing import Any, ClassVar

from gemwalk.clock import read_day
from gemwalk.model.landfill import Area, Cover, Site, read_optional_day
from gemwalk.store.book import Row
from gemwalk.store.repo import Repository


class SiteRepository(Repository[Site]):
    """The landfills the book carries, usually one."""

    table: ClassVar[str] = "site"
    kind: ClassVar[str] = "site"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "name",
        "standard",
        "permit",
        "zone",
        "design_capacity",
        "opened_on",
        "closed_on",
    )

    def read(self, row: Row) -> Site:
        """Turn one site row into a site."""
        return Site(
            label=str(row["label"]),
            name=str(row["name"]),
            standard=str(row["standard"]),
            permit=str(row["permit"]),
            zone=str(row["zone"]),
            design_capacity=float(row["design_capacity"]),
            opened_on=read_day(str(row["opened_on"])),
            closed_on=read_optional_day(row["closed_on"]),
        )

    def write(self, item: Site) -> dict[str, Any]:
        """Turn one site into the column values it is stored as."""
        return {
            "label": item.label,
            "name": item.name,
            "standard": item.standard,
            "permit": item.permit,
            "zone": item.zone,
            "design_capacity": item.design_capacity,
            "opened_on": item.opened_on.isoformat(),
            "closed_on": None if item.closed_on is None else item.closed_on.isoformat(),
        }


class AreaRepository(Repository[Area]):
    """The filling areas of every site in the book."""

    table: ClassVar[str] = "area"
    kind: ClassVar[str] = "area"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "name",
        "acres",
        "first_waste",
        "last_waste",
        "closed_on",
        "cover",
    )

    def read(self, row: Row) -> Area:
        """Turn one area row into an area."""
        return Area(
            label=str(row["label"]),
            site=str(row["site"]),
            name=str(row["name"]),
            acres=float(row["acres"]),
            first_waste=read_day(str(row["first_waste"])),
            last_waste=read_optional_day(row["last_waste"]),
            closed_on=read_optional_day(row["closed_on"]),
            cover=Cover(str(row["cover"])),
        )

    def write(self, item: Area) -> dict[str, Any]:
        """Turn one area into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "name": item.name,
            "acres": item.acres,
            "first_waste": item.first_waste.isoformat(),
            "last_waste": None if item.last_waste is None else item.last_waste.isoformat(),
            "closed_on": None if item.closed_on is None else item.closed_on.isoformat(),
            "cover": item.cover.value,
        }

    def of_site(self, site: str) -> list[Area]:
        """Every area of one site."""
        return self.where("site = ?", (site,))

    def filling(self, site: str) -> list[Area]:
        """Every area of one site that is still taking waste."""
        return self.where("site = ? AND last_waste IS NULL", (site,))


__all__ = ["AreaRepository", "SiteRepository"]

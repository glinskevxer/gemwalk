"""Rows of the leg and covered tables."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, ClassVar

from gemwalk.model.route import Covered, Leg
from gemwalk.store.book import Row
from gemwalk.store.columns import day_text, read_day_or_none
from gemwalk.store.repo import Repository


class LegRepository(Repository[Leg]):
    """The pattern, one leg at a time."""

    table: ClassVar[str] = "leg"
    kind: ClassVar[str] = "leg"
    retired_column: ClassVar[str] = "retired_on"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "area",
        "name",
        "metres",
        "retired_on",
    )

    def read(self, row: Row) -> Leg:
        """Turn one leg row into a leg."""
        return Leg(
            label=str(row["label"]),
            site=str(row["site"]),
            area=str(row["area"]),
            name=str(row["name"]),
            metres=float(row["metres"]),
            retired_on=read_day_or_none(row["retired_on"]),
        )

    def write(self, item: Leg) -> dict[str, Any]:
        """Turn one leg into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "area": item.area,
            "name": item.name,
            "metres": item.metres,
            "retired_on": day_text(item.retired_on),
        }

    def of_area(self, area: str) -> list[Leg]:
        """Every leg of the pattern over one area, retired ones included."""
        return self.where("area = ?", (area,))

    def live_in(self, area: str) -> list[Leg]:
        """Every leg of the pattern over one area that is still walked."""
        return self.where("area = ? AND retired_on IS NULL", (area,))


class CoveredRepository(Repository[Covered]):
    """Which legs each walk actually crossed."""

    table: ClassVar[str] = "covered"
    kind: ClassVar[str] = "covered leg"
    key: ClassVar[str] = "id"
    order: ClassVar[str] = "leg"
    auto: ClassVar[bool] = True
    columns: ClassVar[tuple[str, ...]] = ("id", "walk", "leg", "note")

    def read(self, row: Row) -> Covered:
        """Turn one covered row into a covered leg."""
        return Covered(
            id=int(row["id"]),
            walk=str(row["walk"]),
            leg=str(row["leg"]),
            note=str(row["note"]),
        )

    def write(self, item: Covered) -> dict[str, Any]:
        """Turn one covered leg into the column values it is stored as."""
        return {"id": item.id, "walk": item.walk, "leg": item.leg, "note": item.note}

    def with_key(self, item: Covered, key: int) -> Covered:
        """The same covered leg carrying the number sqlite chose for it."""
        return replace(item, id=key)

    def of_walk(self, walk: str) -> list[Covered]:
        """Every leg one walk crossed."""
        return self.where("walk = ?", (walk,))

    def labels_of(self, walk: str) -> set[str]:
        """The labels of the legs one walk crossed."""
        return {covered.leg for covered in self.of_walk(walk)}


__all__ = ["CoveredRepository", "LegRepository"]

"""Rows of the exceedance and recheck tables."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, ClassVar

from gemwalk.clock import read_day
from gemwalk.model.exceedance import Exceedance, Recheck, Stage
from gemwalk.model.landfill import read_optional_day
from gemwalk.rules import Finding
from gemwalk.store.book import Row
from gemwalk.store.repo import Repository


class ExceedanceRepository(Repository[Exceedance]):
    """Every clock a bad wellhead reading has started."""

    table: ClassVar[str] = "exceedance"
    kind: ClassVar[str] = "exceedance"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "device",
        "kind",
        "opened_on",
        "reading",
        "value",
        "limit_value",
        "stage",
        "closed_on",
        "note",
    )

    def read(self, row: Row) -> Exceedance:
        """Turn one exceedance row into an exceedance."""
        return Exceedance(
            label=str(row["label"]),
            site=str(row["site"]),
            device=str(row["device"]),
            kind=Finding(str(row["kind"])),
            opened_on=read_day(str(row["opened_on"])),
            reading=int(row["reading"]),
            value=float(row["value"]),
            limit_value=float(row["limit_value"]),
            stage=Stage(str(row["stage"])),
            closed_on=read_optional_day(row["closed_on"]),
            note=str(row["note"]),
        )

    def write(self, item: Exceedance) -> dict[str, Any]:
        """Turn one exceedance into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "device": item.device,
            "kind": item.kind.value,
            "opened_on": item.opened_on.isoformat(),
            "reading": item.reading,
            "value": item.value,
            "limit_value": item.limit_value,
            "stage": item.stage.value,
            "closed_on": None if item.closed_on is None else item.closed_on.isoformat(),
            "note": item.note,
        }

    def open_at(self, site: str) -> list[Exceedance]:
        """Every exceedance at a site that has not been closed."""
        return self.where("site = ? AND stage != ?", (site, Stage.CLOSED.value))

    def open_on_device(self, device: str) -> list[Exceedance]:
        """Every open exceedance on one wellhead."""
        return self.where("device = ? AND stage != ?", (device, Stage.CLOSED.value))

    def open_of_kind(self, device: str, kind: Finding) -> Exceedance | None:
        """The open exceedance of one kind on one wellhead, if there is one."""
        row = self.book.one(
            "SELECT * FROM exceedance WHERE device = ? AND kind = ? AND stage != ?",
            (device, kind.value, Stage.CLOSED.value),
        )
        return None if row is None else self.read(row)

    def of_device(self, device: str) -> list[Exceedance]:
        """Every exceedance ever opened on one wellhead, oldest first."""
        rows = self.book.all(
            "SELECT * FROM exceedance WHERE device = ? ORDER BY opened_on, label", (device,)
        )
        return [self.read(row) for row in rows]

    def opened_between(self, site: str, first: str, last: str) -> list[Exceedance]:
        """Every exceedance at a site opened inside a range of days."""
        rows = self.book.all(
            "SELECT * FROM exceedance WHERE site = ? AND opened_on >= ? AND opened_on <= ? "
            "ORDER BY opened_on, label",
            (site, first, last),
        )
        return [self.read(row) for row in rows]

    def for_reading(self, reading: int) -> list[Exceedance]:
        """Every exceedance opened off one reading."""
        return self.where("reading = ?", (reading,))


class RecheckRepository(Repository[Recheck]):
    """The later readings taken against an open exceedance."""

    table: ClassVar[str] = "recheck"
    kind: ClassVar[str] = "recheck"
    key: ClassVar[str] = "id"
    order: ClassVar[str] = "taken_on, id"
    auto: ClassVar[bool] = True
    columns: ClassVar[tuple[str, ...]] = (
        "id",
        "exceedance",
        "taken_on",
        "reading",
        "value",
        "clear",
        "stage",
        "note",
    )

    def read(self, row: Row) -> Recheck:
        """Turn one recheck row into a recheck."""
        return Recheck(
            id=int(row["id"]),
            exceedance=str(row["exceedance"]),
            taken_on=read_day(str(row["taken_on"])),
            reading=None if row["reading"] is None else int(row["reading"]),
            value=float(row["value"]),
            clear=bool(row["clear"]),
            stage=Stage(str(row["stage"])),
            note=str(row["note"]),
        )

    def write(self, item: Recheck) -> dict[str, Any]:
        """Turn one recheck into the column values it is stored as."""
        return {
            "id": item.id,
            "exceedance": item.exceedance,
            "taken_on": item.taken_on.isoformat(),
            "reading": item.reading,
            "value": item.value,
            "clear": int(item.clear),
            "stage": item.stage.value,
            "note": item.note,
        }

    def with_key(self, item: Recheck, key: int) -> Recheck:
        """The same recheck carrying the number sqlite chose for it."""
        return replace(item, id=key)

    def of_exceedance(self, label: str) -> list[Recheck]:
        """Every recheck against one exceedance, oldest first."""
        return self.where("exceedance = ?", (label,))

    def last_for(self, label: str) -> Recheck | None:
        """The most recent recheck against one exceedance."""
        row = self.book.one(
            "SELECT * FROM recheck WHERE exceedance = ? ORDER BY taken_on DESC, id DESC LIMIT 1",
            (label,),
        )
        return None if row is None else self.read(row)


__all__ = ["ExceedanceRepository", "RecheckRepository"]

"""Rows of the sump, level and pumpout tables."""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import Any, ClassVar

from gemwalk.clock import read_day
from gemwalk.model.liquids import Level, Pumpout, Sump, SumpKind
from gemwalk.store.book import Row
from gemwalk.store.columns import day_text, flag, moment_text, read_day_or_none, read_flag
from gemwalk.store.plant import stamp, unstamp
from gemwalk.store.repo import Repository


class SumpRepository(Repository[Sump]):
    """The places on the pipe tree that condensate collects in."""

    table: ClassVar[str] = "sump"
    kind: ClassVar[str] = "sump"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "station",
        "kind",
        "capacity",
        "installed_on",
        "retired_on",
    )

    def read(self, row: Row) -> Sump:
        """Turn one sump row into a sump."""
        return Sump(
            label=str(row["label"]),
            site=str(row["site"]),
            station=str(row["station"]),
            kind=SumpKind(str(row["kind"])),
            capacity=float(row["capacity"]),
            installed_on=read_day(str(row["installed_on"])),
            retired_on=read_day_or_none(row["retired_on"]),
        )

    def write(self, item: Sump) -> dict[str, Any]:
        """Turn one sump into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "station": item.station,
            "kind": item.kind.value,
            "capacity": item.capacity,
            "installed_on": day_text(item.installed_on),
            "retired_on": day_text(item.retired_on),
        }

    def of_site(self, site: str) -> list[Sump]:
        """Every sump at one site."""
        return self.where("site = ?", (site,))

    def live(self, site: str) -> list[Sump]:
        """Every sump still on the system at one site."""
        return self.where("site = ? AND retired_on IS NULL", (site,))


class LevelRepository(Repository[Level]):
    """Every tape drop down every well casing."""

    table: ClassVar[str] = "level"
    kind: ClassVar[str] = "level"
    key: ClassVar[str] = "id"
    order: ClassVar[str] = "taken_on, id"
    auto: ClassVar[bool] = True
    columns: ClassVar[tuple[str, ...]] = ("id", "device", "taken_on", "depth", "pumped", "note")

    def read(self, row: Row) -> Level:
        """Turn one level row into a level."""
        return Level(
            id=int(row["id"]),
            device=str(row["device"]),
            taken_on=read_day(str(row["taken_on"])),
            depth=float(row["depth"]),
            pumped=read_flag(row["pumped"]),
            note=str(row["note"]),
        )

    def write(self, item: Level) -> dict[str, Any]:
        """Turn one level into the column values it is stored as."""
        return {
            "id": item.id,
            "device": item.device,
            "taken_on": day_text(item.taken_on),
            "depth": item.depth,
            "pumped": flag(item.pumped),
            "note": item.note,
        }

    def with_key(self, item: Level, key: int) -> Level:
        """The same level carrying the number sqlite chose for it."""
        return replace(item, id=key)

    def of_device(self, device: str) -> list[Level]:
        """Every level ever taken at one well, oldest first."""
        return self.where("device = ?", (device,))

    def latest_for(self, device: str, on: dt.date) -> Level | None:
        """The most recent level at one well on or before a day."""
        row = self.book.one(
            "SELECT * FROM level WHERE device = ? AND taken_on <= ? "
            "ORDER BY taken_on DESC, id DESC LIMIT 1",
            (device, on.isoformat()),
        )
        return None if row is None else self.read(row)

    def on_day(self, day: dt.date) -> list[Level]:
        """Every level taken on one day, in well order."""
        rows = self.book.all(
            "SELECT * FROM level WHERE taken_on = ? ORDER BY device", (day.isoformat(),)
        )
        return [self.read(row) for row in rows]


class PumpoutRepository(Repository[Pumpout]):
    """Every load of condensate taken off a sump."""

    table: ClassVar[str] = "pumpout"
    kind: ClassVar[str] = "pumpout"
    key: ClassVar[str] = "id"
    order: ClassVar[str] = "at, id"
    auto: ClassVar[bool] = True
    columns: ClassVar[tuple[str, ...]] = (
        "id",
        "sump",
        "at",
        "gallons",
        "hauler",
        "bound_for",
        "note",
    )

    def read(self, row: Row) -> Pumpout:
        """Turn one pumpout row into a pumpout."""
        return Pumpout(
            id=int(row["id"]),
            sump=str(row["sump"]),
            at=unstamp(str(row["at"])),
            gallons=float(row["gallons"]),
            hauler=str(row["hauler"]),
            bound_for=str(row["bound_for"]),
            note=str(row["note"]),
        )

    def write(self, item: Pumpout) -> dict[str, Any]:
        """Turn one pumpout into the column values it is stored as."""
        return {
            "id": item.id,
            "sump": item.sump,
            "at": moment_text(item.at),
            "gallons": item.gallons,
            "hauler": item.hauler,
            "bound_for": item.bound_for,
            "note": item.note,
        }

    def with_key(self, item: Pumpout, key: int) -> Pumpout:
        """The same pumpout carrying the number sqlite chose for it."""
        return replace(item, id=key)

    def of_sump(self, sump: str) -> list[Pumpout]:
        """Every load off one sump, oldest first."""
        return self.where("sump = ?", (sump,))

    def between(self, first: dt.datetime, last: dt.datetime) -> list[Pumpout]:
        """Every load in a half open range of moments."""
        rows = self.book.all(
            "SELECT * FROM pumpout WHERE at >= ? AND at < ? ORDER BY at, id",
            (stamp(first), stamp(last)),
        )
        return [self.read(row) for row in rows]

    def gallons_between(self, sump: str, first: dt.datetime, last: dt.datetime) -> float:
        """How many gallons came off one sump in a range."""
        value = self.book.value(
            "SELECT sum(gallons) FROM pumpout WHERE sump = ? AND at >= ? AND at < ?",
            (sump, stamp(first), stamp(last)),
        )
        return 0.0 if value is None else float(value)


__all__ = ["LevelRepository", "PumpoutRepository", "SumpRepository"]

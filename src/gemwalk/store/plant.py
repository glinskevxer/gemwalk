"""Rows of the control, operation and outage tables.

Moments are stored as utc isoformat text, which sorts the same way it compares,
so a range query on the column is a range query on the clock.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import Any, ClassVar

from gemwalk.clock import UTC, read_day
from gemwalk.model.landfill import read_optional_day
from gemwalk.model.plant import Control, ControlKind, Operation, Outage
from gemwalk.store.book import Row
from gemwalk.store.repo import Repository


def stamp(moment: dt.datetime) -> str:
    """Write a moment the way the book stores it."""
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def unstamp(text: str) -> dt.datetime:
    """Read a moment back out of the book."""
    return dt.datetime.fromisoformat(text).astimezone(UTC)


def unstamp_or_none(value: object) -> dt.datetime | None:
    """Read a moment the book may have left blank."""
    return None if value is None else unstamp(str(value))


class ControlRepository(Repository[Control]):
    """The devices that burn the gas."""

    table: ClassVar[str] = "control"
    kind: ClassVar[str] = "control device"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "name",
        "kind",
        "capacity",
        "minimum_temp",
        "installed_on",
        "retired_on",
    )

    def read(self, row: Row) -> Control:
        """Turn one control row into a control device."""
        return Control(
            label=str(row["label"]),
            site=str(row["site"]),
            name=str(row["name"]),
            kind=ControlKind(str(row["kind"])),
            capacity=float(row["capacity"]),
            minimum_temp=None if row["minimum_temp"] is None else float(row["minimum_temp"]),
            installed_on=read_day(str(row["installed_on"])),
            retired_on=read_optional_day(row["retired_on"]),
        )

    def write(self, item: Control) -> dict[str, Any]:
        """Turn one control device into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "name": item.name,
            "kind": item.kind.value,
            "capacity": item.capacity,
            "minimum_temp": item.minimum_temp,
            "installed_on": item.installed_on.isoformat(),
            "retired_on": None if item.retired_on is None else item.retired_on.isoformat(),
        }

    def of_site(self, site: str) -> list[Control]:
        """Every control device at one site."""
        return self.where("site = ?", (site,))

    def live(self, site: str) -> list[Control]:
        """Every control device still on the system at one site."""
        return self.where("site = ? AND retired_on IS NULL", (site,))


class OperationRepository(Repository[Operation]):
    """The operating record of every control device."""

    table: ClassVar[str] = "operation"
    kind: ClassVar[str] = "operating record"
    key: ClassVar[str] = "id"
    order: ClassVar[str] = "at, id"
    auto: ClassVar[bool] = True
    columns: ClassVar[tuple[str, ...]] = (
        "id",
        "control",
        "at",
        "running",
        "flow",
        "methane",
        "temperature",
        "note",
    )

    def read(self, row: Row) -> Operation:
        """Turn one operating row into an operating record."""
        return Operation(
            id=int(row["id"]),
            control=str(row["control"]),
            at=unstamp(str(row["at"])),
            running=bool(row["running"]),
            flow=float(row["flow"]),
            methane=float(row["methane"]),
            temperature=None if row["temperature"] is None else float(row["temperature"]),
            note=str(row["note"]),
        )

    def write(self, item: Operation) -> dict[str, Any]:
        """Turn one operating record into the column values it is stored as."""
        return {
            "id": item.id,
            "control": item.control,
            "at": stamp(item.at),
            "running": int(item.running),
            "flow": item.flow,
            "methane": item.methane,
            "temperature": item.temperature,
            "note": item.note,
        }

    def with_key(self, item: Operation, key: int) -> Operation:
        """The same record carrying the number sqlite chose for it."""
        return replace(item, id=key)

    def of_control(self, control: str) -> list[Operation]:
        """Every operating record of one device, oldest first."""
        return self.where("control = ?", (control,))

    def between(self, control: str, first: dt.datetime, last: dt.datetime) -> list[Operation]:
        """Every record of one device in a half open range of moments."""
        rows = self.book.all(
            "SELECT * FROM operation WHERE control = ? AND at >= ? AND at < ? ORDER BY at, id",
            (control, stamp(first), stamp(last)),
        )
        return [self.read(row) for row in rows]

    def latest(self, control: str) -> Operation | None:
        """The most recent operating record of one device."""
        row = self.book.one(
            "SELECT * FROM operation WHERE control = ? ORDER BY at DESC, id DESC LIMIT 1",
            (control,),
        )
        return None if row is None else self.read(row)


class OutageRepository(Repository[Outage]):
    """Every stretch of time a control device was not available."""

    table: ClassVar[str] = "outage"
    kind: ClassVar[str] = "outage"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "control",
        "site",
        "started_at",
        "ended_at",
        "reason",
        "planned",
        "note",
    )

    def read(self, row: Row) -> Outage:
        """Turn one outage row into an outage."""
        return Outage(
            label=str(row["label"]),
            control=str(row["control"]),
            site=str(row["site"]),
            started_at=unstamp(str(row["started_at"])),
            ended_at=unstamp_or_none(row["ended_at"]),
            reason=str(row["reason"]),
            planned=bool(row["planned"]),
            note=str(row["note"]),
        )

    def write(self, item: Outage) -> dict[str, Any]:
        """Turn one outage into the column values it is stored as."""
        return {
            "label": item.label,
            "control": item.control,
            "site": item.site,
            "started_at": stamp(item.started_at),
            "ended_at": None if item.ended_at is None else stamp(item.ended_at),
            "reason": item.reason,
            "planned": int(item.planned),
            "note": item.note,
        }

    def of_control(self, control: str) -> list[Outage]:
        """Every outage of one device."""
        return self.where("control = ?", (control,))

    def open_at(self, site: str) -> list[Outage]:
        """Every outage at one site that has not been closed."""
        return self.where("site = ? AND ended_at IS NULL", (site,))

    def overlapping(self, site: str, first: dt.datetime, last: dt.datetime) -> list[Outage]:
        """Every outage at a site that touches a range of moments."""
        rows = self.book.all(
            "SELECT * FROM outage WHERE site = ? AND started_at < ? "
            "AND (ended_at IS NULL OR ended_at > ?) ORDER BY started_at, label",
            (site, stamp(last), stamp(first)),
        )
        return [self.read(row) for row in rows]


__all__ = [
    "ControlRepository",
    "OperationRepository",
    "OutageRepository",
    "stamp",
    "unstamp",
    "unstamp_or_none",
]

"""Rows of the run and reading tables.

A reading has no label of its own. There is one reading per device per run and
sqlite hands out the number, so this is the first repository that lets the book
choose its own key.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, ClassVar

from gemwalk.clock import read_day
from gemwalk.model.reading import Reading, Run
from gemwalk.store.book import Row
from gemwalk.store.columns import day_text, read_day_or_none
from gemwalk.store.repo import Repository


class RunRepository(Repository[Run]):
    """The monthly passes over the wellfield."""

    table: ClassVar[str] = "run"
    kind: ClassVar[str] = "run"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "started_on",
        "closed_on",
        "monitor",
        "meter",
        "note",
    )

    def read(self, row: Row) -> Run:
        """Turn one run row into a run."""
        return Run(
            label=str(row["label"]),
            site=str(row["site"]),
            started_on=read_day(str(row["started_on"])),
            closed_on=read_day_or_none(row["closed_on"]),
            monitor=str(row["monitor"]),
            meter=str(row["meter"]),
            note=str(row["note"]),
        )

    def write(self, item: Run) -> dict[str, Any]:
        """Turn one run into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "started_on": day_text(item.started_on),
            "closed_on": day_text(item.closed_on),
            "monitor": item.monitor,
            "meter": item.meter,
            "note": item.note,
        }

    def open_runs(self, site: str) -> list[Run]:
        """Every run at one site that is still taking readings."""
        return self.where("site = ? AND closed_on IS NULL", (site,))

    def between(self, site: str, first: str, last: str) -> list[Run]:
        """Every run at one site started inside a range of days."""
        return self.where("site = ? AND started_on >= ? AND started_on <= ?", (site, first, last))


class ReadingRepository(Repository[Reading]):
    """The wellhead readings on every run in the book."""

    table: ClassVar[str] = "reading"
    kind: ClassVar[str] = "reading"
    key: ClassVar[str] = "id"
    order: ClassVar[str] = "device"
    auto: ClassVar[bool] = True
    columns: ClassVar[tuple[str, ...]] = (
        "id",
        "run",
        "device",
        "taken_on",
        "methane",
        "carbon",
        "oxygen",
        "balance",
        "temperature",
        "static",
        "applied",
        "flow",
        "valve_before",
        "valve_after",
        "note",
    )

    def read(self, row: Row) -> Reading:
        """Turn one reading row into a reading."""
        return Reading(
            id=int(row["id"]),
            run=str(row["run"]),
            device=str(row["device"]),
            taken_on=read_day(str(row["taken_on"])),
            methane=float(row["methane"]),
            carbon=float(row["carbon"]),
            oxygen=float(row["oxygen"]),
            balance=float(row["balance"]),
            temperature=float(row["temperature"]),
            static=float(row["static"]),
            applied=float(row["applied"]),
            flow=float(row["flow"]),
            valve_before=float(row["valve_before"]),
            valve_after=float(row["valve_after"]),
            note=str(row["note"]),
        )

    def write(self, item: Reading) -> dict[str, Any]:
        """Turn one reading into the column values it is stored as."""
        return {
            "id": item.id,
            "run": item.run,
            "device": item.device,
            "taken_on": day_text(item.taken_on),
            "methane": item.methane,
            "carbon": item.carbon,
            "oxygen": item.oxygen,
            "balance": item.balance,
            "temperature": item.temperature,
            "static": item.static,
            "applied": item.applied,
            "flow": item.flow,
            "valve_before": item.valve_before,
            "valve_after": item.valve_after,
            "note": item.note,
        }

    def with_key(self, item: Reading, key: int) -> Reading:
        """The same reading carrying the number sqlite chose for it."""
        return replace(item, id=key)

    def of_run(self, run: str) -> list[Reading]:
        """Every reading on one run, in device order."""
        return self.where("run = ?", (run,))

    def of_device(self, device: str) -> list[Reading]:
        """Every reading ever taken at one wellhead, oldest first."""
        rows = self.book.all(
            "SELECT * FROM reading WHERE device = ? ORDER BY taken_on, id", (device,)
        )
        return [self.read(row) for row in rows]

    def on_run_for(self, run: str, device: str) -> Reading | None:
        """The one reading of one device on one run, if it was read."""
        row = self.book.one("SELECT * FROM reading WHERE run = ? AND device = ?", (run, device))
        return None if row is None else self.read(row)

    def id_on_run(self, run: str, device: str) -> int:
        """The number of the reading of one device on one run."""
        found = self.on_run_for(run, device)
        return 0 if found is None else found.id

    def latest_for(self, device: str, on: str) -> Reading | None:
        """The most recent reading at a wellhead on or before a day."""
        row = self.book.one(
            "SELECT * FROM reading WHERE device = ? AND taken_on <= ? "
            "ORDER BY taken_on DESC, id DESC LIMIT 1",
            (device, on),
        )
        return None if row is None else self.read(row)

    def between(self, device: str, first: str, last: str) -> list[Reading]:
        """Every reading at one wellhead inside a range of days."""
        rows = self.book.all(
            "SELECT * FROM reading WHERE device = ? AND taken_on >= ? AND taken_on <= ? "
            "ORDER BY taken_on, id",
            (device, first, last),
        )
        return [self.read(row) for row in rows]


__all__ = ["ReadingRepository", "RunRepository"]

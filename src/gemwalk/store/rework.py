"""Rows of the rework table."""

from __future__ import annotations

from typing import Any, ClassVar

from gemwalk.clock import read_day
from gemwalk.model.rework import Job, Rework
from gemwalk.store.book import Row
from gemwalk.store.columns import day_text, read_day_or_none
from gemwalk.store.repo import Repository


def _number(value: object) -> float | None:
    """Read a measurement a column may have left blank."""
    return None if value is None else float(str(value))


class ReworkRepository(Repository[Job]):
    """Every raise, deepening, redrill and repair on every device."""

    table: ClassVar[str] = "rework"
    kind: ClassVar[str] = "rework"
    day_column: ClassVar[str] = "started_on"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "device",
        "site",
        "kind",
        "started_on",
        "finished_on",
        "before_depth",
        "before_top",
        "before_bottom",
        "after_depth",
        "after_top",
        "after_bottom",
        "note",
    )

    def read(self, row: Row) -> Job:
        """Turn one rework row into a job."""
        return Job(
            label=str(row["label"]),
            device=str(row["device"]),
            site=str(row["site"]),
            kind=Rework(str(row["kind"])),
            started_on=read_day(str(row["started_on"])),
            finished_on=read_day_or_none(row["finished_on"]),
            before_depth=float(row["before_depth"]),
            before_top=float(row["before_top"]),
            before_bottom=float(row["before_bottom"]),
            after_depth=_number(row["after_depth"]),
            after_top=_number(row["after_top"]),
            after_bottom=_number(row["after_bottom"]),
            note=str(row["note"]),
        )

    def write(self, item: Job) -> dict[str, Any]:
        """Turn one job into the column values it is stored as."""
        return {
            "label": item.label,
            "device": item.device,
            "site": item.site,
            "kind": item.kind.value,
            "started_on": day_text(item.started_on),
            "finished_on": day_text(item.finished_on),
            "before_depth": item.before_depth,
            "before_top": item.before_top,
            "before_bottom": item.before_bottom,
            "after_depth": item.after_depth,
            "after_top": item.after_top,
            "after_bottom": item.after_bottom,
            "note": item.note,
        }

    def of_device(self, device: str) -> list[Job]:
        """Every piece of work on one device, oldest first."""
        rows = self.book.all(
            "SELECT * FROM rework WHERE device = ? ORDER BY started_on, label", (device,)
        )
        return [self.read(row) for row in rows]

    def open_at(self, site: str) -> list[Job]:
        """Every piece of work at a site that is still going on."""
        return self.where("site = ? AND finished_on IS NULL", (site,))

    def open_on(self, device: str) -> Job | None:
        """The open piece of work on one device, if there is one."""
        row = self.book.one(
            "SELECT * FROM rework WHERE device = ? AND finished_on IS NULL", (device,)
        )
        return None if row is None else self.read(row)


__all__ = ["ReworkRepository"]

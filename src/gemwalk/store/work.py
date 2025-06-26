"""Rows of the work order table."""

from __future__ import annotations

from typing import Any, ClassVar

from gemwalk.clock import read_day
from gemwalk.model.work import CLOSED, Job, Standing, WorkOrder
from gemwalk.store.book import Row
from gemwalk.store.columns import day_text, read_day_or_none
from gemwalk.store.repo import Repository


class WorkOrderRepository(Repository[WorkOrder]):
    """Every job the field crew has been handed."""

    table: ClassVar[str] = "work_order"
    kind: ClassVar[str] = "work order"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "kind",
        "target",
        "because",
        "raised_on",
        "due_on",
        "state",
        "crew",
        "done_on",
        "note",
    )

    def read(self, row: Row) -> WorkOrder:
        """Turn one work order row into a work order."""
        return WorkOrder(
            label=str(row["label"]),
            site=str(row["site"]),
            job=Job(str(row["kind"])),
            target=str(row["target"]),
            because=None if row["because"] is None else str(row["because"]),
            raised_on=read_day(str(row["raised_on"])),
            due_on=read_day(str(row["due_on"])),
            state=Standing(str(row["state"])),
            crew=str(row["crew"]),
            done_on=read_day_or_none(row["done_on"]),
            note=str(row["note"]),
        )

    def write(self, item: WorkOrder) -> dict[str, Any]:
        """Turn one work order into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "kind": item.job.value,
            "target": item.target,
            "because": item.because,
            "raised_on": day_text(item.raised_on),
            "due_on": day_text(item.due_on),
            "state": item.state.value,
            "crew": item.crew,
            "done_on": day_text(item.done_on),
            "note": item.note,
        }

    def open_at(self, site: str) -> list[WorkOrder]:
        """Every order at one site that still has to be done."""
        closed = ", ".join(f"'{state.value}'" for state in CLOSED)
        return self.where(f"site = ? AND state NOT IN ({closed})", (site,))

    def of_target(self, target: str) -> list[WorkOrder]:
        """Every order ever raised against one place."""
        return self.where("target = ?", (target,))

    def of_record(self, because: str) -> list[WorkOrder]:
        """Every order raised out of one compliance record."""
        return self.where("because = ?", (because,))

    def in_state(self, site: str, state: Standing) -> list[WorkOrder]:
        """Every order at one site in one state."""
        return self.where("site = ? AND state = ?", (site, state.value))

    def raised_between(self, site: str, first: str, last: str) -> list[WorkOrder]:
        """Every order at one site raised inside a range of days."""
        rows = self.book.all(
            "SELECT * FROM work_order WHERE site = ? AND raised_on >= ? AND raised_on <= ? "
            "ORDER BY raised_on, label",
            (site, first, last),
        )
        return [self.read(row) for row in rows]


__all__ = ["WorkOrderRepository"]

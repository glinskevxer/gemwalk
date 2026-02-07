"""Rows of the observation table."""

from __future__ import annotations

from typing import Any, ClassVar

from gemwalk.model.observation import Observation
from gemwalk.store.book import Row
from gemwalk.store.columns import moment_text
from gemwalk.store.plant import unstamp
from gemwalk.store.repo import Repository


class ObservationRepository(Repository[Observation]):
    """Every period anybody spent watching a flare."""

    table: ClassVar[str] = "observation"
    kind: ClassVar[str] = "observation"
    order: ClassVar[str] = "started_at, label"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "control",
        "site",
        "started_at",
        "watched",
        "visible",
        "observer",
        "note",
    )

    def read(self, row: Row) -> Observation:
        """Turn one observation row into an observation."""
        return Observation(
            label=str(row["label"]),
            control=str(row["control"]),
            site=str(row["site"]),
            started_at=unstamp(str(row["started_at"])),
            watched=float(row["watched"]),
            visible=float(row["visible"]),
            observer=str(row["observer"]),
            note=str(row["note"]),
        )

    def write(self, item: Observation) -> dict[str, Any]:
        """Turn one observation into the column values it is stored as."""
        return {
            "label": item.label,
            "control": item.control,
            "site": item.site,
            "started_at": moment_text(item.started_at),
            "watched": item.watched,
            "visible": item.visible,
            "observer": item.observer,
            "note": item.note,
        }

    def of_control(self, control: str) -> list[Observation]:
        """Every watch of one flare, oldest first."""
        return self.where("control = ?", (control,))


__all__ = ["ObservationRepository"]

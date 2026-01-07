"""Rows of the instrument and calibration tables."""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import Any, ClassVar

from gemwalk.clock import read_day
from gemwalk.model.instrument import Calibration, Instrument, Meter
from gemwalk.store.book import Row
from gemwalk.store.columns import day_text, moment_text, read_day_or_none
from gemwalk.store.plant import stamp, unstamp
from gemwalk.store.repo import Repository


class InstrumentRepository(Repository[Instrument]):
    """Every meter the site has ever had."""

    table: ClassVar[str] = "instrument"
    kind: ClassVar[str] = "instrument"
    retired_column: ClassVar[str] = "retired_on"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "kind",
        "maker",
        "model",
        "serial",
        "in_service",
        "retired_on",
    )

    def read(self, row: Row) -> Instrument:
        """Turn one instrument row into an instrument."""
        return Instrument(
            label=str(row["label"]),
            site=str(row["site"]),
            kind=Meter(str(row["kind"])),
            maker=str(row["maker"]),
            model=str(row["model"]),
            serial=str(row["serial"]),
            in_service=read_day(str(row["in_service"])),
            retired_on=read_day_or_none(row["retired_on"]),
        )

    def write(self, item: Instrument) -> dict[str, Any]:
        """Turn one instrument into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "kind": item.kind.value,
            "maker": item.maker,
            "model": item.model,
            "serial": item.serial,
            "in_service": day_text(item.in_service),
            "retired_on": day_text(item.retired_on),
        }

    def of_kind(self, site: str, kind: Meter) -> list[Instrument]:
        """Every instrument of one kind at one site."""
        return self.where("site = ? AND kind = ?", (site, kind.value))


class CalibrationRepository(Repository[Calibration]):
    """Every calibration of every instrument."""

    table: ClassVar[str] = "calibration"
    kind: ClassVar[str] = "calibration"
    key: ClassVar[str] = "id"
    order: ClassVar[str] = "at, id"
    auto: ClassVar[bool] = True
    columns: ClassVar[tuple[str, ...]] = (
        "id",
        "instrument",
        "at",
        "standard",
        "expected",
        "before",
        "after",
        "by_whom",
        "note",
    )

    def read(self, row: Row) -> Calibration:
        """Turn one calibration row into a calibration."""
        return Calibration(
            id=int(row["id"]),
            instrument=str(row["instrument"]),
            at=unstamp(str(row["at"])),
            standard=str(row["standard"]),
            expected=float(row["expected"]),
            before=float(row["before"]),
            after=float(row["after"]),
            by_whom=str(row["by_whom"]),
            note=str(row["note"]),
        )

    def write(self, item: Calibration) -> dict[str, Any]:
        """Turn one calibration into the column values it is stored as."""
        return {
            "id": item.id,
            "instrument": item.instrument,
            "at": moment_text(item.at),
            "standard": item.standard,
            "expected": item.expected,
            "before": item.before,
            "after": item.after,
            "by_whom": item.by_whom,
            "note": item.note,
        }

    def with_key(self, item: Calibration, key: int) -> Calibration:
        """The same calibration carrying the number sqlite chose for it."""
        return replace(item, id=key)

    def of_instrument(self, instrument: str) -> list[Calibration]:
        """Every calibration of one instrument, oldest first."""
        return self.where("instrument = ?", (instrument,))

    def on_day(self, instrument: str, day: dt.date) -> list[Calibration]:
        """Every calibration of one instrument on one day."""
        rows = self.book.all(
            "SELECT * FROM calibration WHERE instrument = ? AND at >= ? AND at < ? ORDER BY at, id",
            (
                instrument,
                stamp(dt.datetime.combine(day, dt.time.min, tzinfo=dt.UTC)),
                stamp(dt.datetime.combine(day + dt.timedelta(days=1), dt.time.min, tzinfo=dt.UTC)),
            ),
        )
        return [self.read(row) for row in rows]

    def latest_before(self, instrument: str, day: dt.date) -> Calibration | None:
        """The most recent calibration of one instrument on or before a day."""
        end = dt.datetime.combine(day + dt.timedelta(days=1), dt.time.min, tzinfo=dt.UTC)
        row = self.book.one(
            "SELECT * FROM calibration WHERE instrument = ? AND at < ? ORDER BY at DESC, id DESC "
            "LIMIT 1",
            (instrument, stamp(end)),
        )
        return None if row is None else self.read(row)


__all__ = ["CalibrationRepository", "InstrumentRepository"]

"""Taking a field sheet in off a spreadsheet instead of typing it again.

The crew's tablet writes a csv and somebody has to get it into the book. The
whole difficulty is that a sheet of forty rows will have two bad ones in it, and
the useful behaviour is to take the thirty eight and say exactly what was wrong
with the other two, by line number, in the words of the sheet.

So nothing here raises on a bad row. The reader collects what it could not read
and hands it back beside what it could, and the desk writes the good ones inside
one transaction. A sheet is either taken in full or, if the caller insists on
that, not at all.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from dataclasses import dataclass, field

from gemwalk.clock import read_day
from gemwalk.errors import RuleError, UnitError
from gemwalk.model.reading import Reading
from gemwalk.service.monitoring import MonitoringDesk
from gemwalk.store.book import Book

NUMBERS = (
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
)
REQUIRED = ("device", *NUMBERS)


@dataclass(frozen=True)
class FieldRow:
    """One row of a field sheet that read cleanly."""

    line: int
    device: str
    taken_on: dt.date | None
    values: dict[str, float]
    note: str = ""


@dataclass
class Read:
    """What a sheet gave up: the rows that read, and the ones that did not."""

    rows: list[FieldRow] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """True when every row on the sheet read."""
        return not self.refused


@dataclass
class Taken:
    """What writing a sheet into the book did."""

    recorded: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """True when every row went in."""
        return not self.refused


def read_sheet(text: str) -> Read:
    """Read a field sheet, keeping what read and naming what did not."""
    reader = csv.DictReader(io.StringIO(text))
    out = Read()
    if reader.fieldnames is None:
        out.refused.append("the sheet has no heading row")
        return out
    missing = [name for name in REQUIRED if name not in reader.fieldnames]
    if missing:
        out.refused.append("the sheet has no " + ", ".join(missing) + " column")
        return out
    for number, row in enumerate(reader, start=2):
        parsed = _read_row(number, row)
        if isinstance(parsed, str):
            out.refused.append(parsed)
        else:
            out.rows.append(parsed)
    return out


def _read_row(number: int, row: dict[str, str | None]) -> FieldRow | str:
    device = (row.get("device") or "").strip()
    if not device:
        return f"line {number}: no device"
    values: dict[str, float] = {}
    for name in NUMBERS:
        raw = (row.get(name) or "").strip()
        if not raw:
            return f"line {number}: {device} has no {name}"
        try:
            values[name] = float(raw)
        except ValueError:
            return f"line {number}: {device} {name} of {raw!r} is not a number"
    taken_on: dt.date | None = None
    written = (row.get("taken_on") or "").strip()
    if written:
        try:
            taken_on = read_day(written)
        except UnitError:
            return f"line {number}: {device} taken_on of {written!r} is not a date"
    return FieldRow(
        line=number,
        device=device,
        taken_on=taken_on,
        values=values,
        note=(row.get("note") or "").strip(),
    )


class IntakeDesk:
    """Taking field sheets in off a spreadsheet."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.monitoring = MonitoringDesk(book)

    def take(self, run: str, text: str, *, on: dt.date, all_or_nothing: bool = False) -> Taken:
        """Write a field sheet onto an open run.

        A row that names a device the book has never issued, or one that is not
        on the run, is refused the way a bad number is: by line, with the
        wording the sheet used, and without stopping the rest of the sheet.
        """
        pass_ = self.monitoring.runs.get(run)
        read = read_sheet(text)
        taken = Taken(refused=list(read.refused))
        if all_or_nothing and read.refused:
            return taken
        with self.book.writing():
            for row in read.rows:
                try:
                    self.monitoring.record(
                        run,
                        row.device,
                        on=row.taken_on or on,
                        note=row.note,
                        methane=row.values["methane"],
                        carbon=row.values["carbon"],
                        oxygen=row.values["oxygen"],
                        balance=row.values["balance"],
                        temperature=row.values["temperature"],
                        static=row.values["static"],
                        applied=row.values["applied"],
                        flow=row.values["flow"],
                        valve_before=row.values["valve_before"],
                        valve_after=row.values["valve_after"],
                    )
                except RuleError as failure:
                    taken.refused.append(f"line {row.line}: {failure}")
                    continue
                except Exception as failure:  # noqa: BLE001
                    taken.refused.append(f"line {row.line}: {row.device}: {failure}")
                    continue
                taken.recorded.append(row.device)
            if all_or_nothing and taken.refused:
                raise RuleError(
                    f"sheet for {pass_.label}",
                    f"{len(taken.refused)} rows would not go in and nothing was written",
                )
        return taken

    def preview(self, text: str) -> Read:
        """Read a sheet without writing any of it."""
        return read_sheet(text)

    def sample(self) -> str:
        """A heading row a crew can start a sheet from."""
        return ",".join(("taken_on", *REQUIRED, "note")) + "\n"

    def as_rows(self, readings: list[Reading]) -> str:
        """Turn readings back into a sheet, which is how a run gets corrected."""
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(("taken_on", *REQUIRED, "note"))
        for reading in readings:
            writer.writerow(
                (
                    reading.taken_on.isoformat(),
                    reading.device,
                    reading.methane,
                    reading.carbon,
                    reading.oxygen,
                    reading.balance,
                    reading.temperature,
                    reading.static,
                    reading.applied,
                    reading.flow,
                    reading.valve_before,
                    reading.valve_after,
                    reading.note,
                )
            )
        return out.getvalue()


__all__ = ["NUMBERS", "REQUIRED", "FieldRow", "IntakeDesk", "Read", "Taken", "read_sheet"]

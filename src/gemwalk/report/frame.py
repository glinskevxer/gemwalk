"""How a report is put together, and how it is printed.

A report is built as a structure and printed at the very end. Nothing in this
package builds a report by writing strings into a list, because a report that
only exists as text cannot be totalled, filtered or checked, and every question
anybody asks about one is a question about its numbers.

Columns say how they are lined up and what they do with a blank. The width of a
column is worked out from what is actually in it, so a report of three rows is
narrow and the same report of three hundred is not.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum

from gemwalk.errors import DesignError

RULE = "-"
GAP = "  "


class Align(Enum):
    """Which edge a column's cells are pushed against."""

    LEFT = "left"
    RIGHT = "right"

    def pad(self, text: str, width: int) -> str:
        """Pad one cell out to the column width."""
        return text.ljust(width) if self is Align.LEFT else text.rjust(width)


@dataclass(frozen=True)
class Column:
    """One column of a table, with how its cells are lined up."""

    heading: str
    align: Align = Align.LEFT
    blank: str = ""
    adds_up: bool = False

    def cell(self, value: object) -> str:
        """The text of one cell, with the column's own word for nothing."""
        if value is None:
            return self.blank
        return str(value)


@dataclass
class Table:
    """A heading, a set of columns and the rows under them."""

    columns: tuple[Column, ...]
    rows: list[tuple[object, ...]] = field(default_factory=list)
    title: str = ""
    empty: str = "nothing to report"

    def add(self, *cells: object) -> Table:
        """Put one row on the table."""
        if len(cells) != len(self.columns):
            raise DesignError(
                self.title or "a table",
                f"{len(cells)} cells for {len(self.columns)} columns",
            )
        self.rows.append(cells)
        return self

    def extend(self, rows: Iterable[Sequence[object]]) -> Table:
        """Put several rows on the table."""
        for row in rows:
            self.add(*row)
        return self

    @property
    def is_empty(self) -> bool:
        """True when nothing was put on the table."""
        return not self.rows

    def total(self, heading: str) -> float:
        """Add one column up, skipping anything that is not a number.

        A cell that is not a number is skipped rather than refused, because a
        column of measurements with one blank in it is an ordinary column and
        refusing to total it would leave the report with no total at all.
        """
        index = self._index(heading)
        if not self.columns[index].adds_up:
            raise DesignError(heading, "this column does not add up")
        running = 0.0
        for row in self.rows:
            value = row[index]
            if isinstance(value, int | float) and not isinstance(value, bool):
                running += float(value)
        return running

    def totals(self) -> dict[str, float]:
        """Every column that adds up, added up."""
        return {
            column.heading: self.total(column.heading) for column in self.columns if column.adds_up
        }

    def _index(self, heading: str) -> int:
        for index, column in enumerate(self.columns):
            if column.heading == heading:
                return index
        raise DesignError(self.title or "a table", f"has no column called {heading}")

    def widths(self) -> list[int]:
        """How wide each column has to be for what is actually in it."""
        widths = [len(column.heading) for column in self.columns]
        for row in self.rows:
            for index, (column, value) in enumerate(zip(self.columns, row, strict=True)):
                widths[index] = max(widths[index], len(column.cell(value)))
        if self.totals():
            for index, column in enumerate(self.columns):
                if column.adds_up:
                    widths[index] = max(widths[index], len(f"{self.total(column.heading):g}"))
        return widths

    def lines(self) -> list[str]:
        """The table as text, headings and rule included."""
        out: list[str] = []
        if self.title:
            out.append(self.title)
        if self.is_empty:
            out.append(f"  {self.empty}")
            return out
        widths = self.widths()
        heads = [
            column.align.pad(column.heading, width)
            for column, width in zip(self.columns, widths, strict=True)
        ]
        out.append(GAP.join(heads).rstrip())
        out.append(GAP.join(RULE * width for width in widths))
        for row in self.rows:
            cells = [
                column.align.pad(column.cell(value), width)
                for column, value, width in zip(self.columns, row, widths, strict=True)
            ]
            out.append(GAP.join(cells).rstrip())
        if self.totals():
            out.append(GAP.join(RULE * width for width in widths))
            footer = [
                column.align.pad(
                    f"{self.total(column.heading):g}" if column.adds_up else "",
                    width,
                )
                for column, width in zip(self.columns, widths, strict=True)
            ]
            out.append(GAP.join(footer).rstrip())
        return out


@dataclass
class Section:
    """One headed part of a report, holding text and tables."""

    heading: str
    body: list[str] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)

    def say(self, line: str) -> Section:
        """Put one line of text under the heading."""
        self.body.append(line)
        return self

    def table(self, table: Table) -> Section:
        """Put a table under the heading."""
        self.tables.append(table)
        return self

    @property
    def is_empty(self) -> bool:
        """True when the section has nothing under it at all."""
        return not self.body and all(table.is_empty for table in self.tables)

    def lines(self) -> list[str]:
        """The section as text."""
        out = [self.heading, RULE * len(self.heading)]
        out.extend(self.body)
        for table in self.tables:
            if self.body or out[-1] != "":
                out.append("")
            out.extend(table.lines())
        return out


@dataclass
class Report:
    """A title, the lines under it, and the sections."""

    title: str
    subtitle: str = ""
    sections: list[Section] = field(default_factory=list)

    def section(self, heading: str) -> Section:
        """Start a new section and hand it back to be filled in."""
        made = Section(heading)
        self.sections.append(made)
        return made

    def find(self, heading: str) -> Section | None:
        """The section with this heading, if the report has one."""
        for section in self.sections:
            if section.heading == heading:
                return section
        return None

    def tables(self) -> list[Table]:
        """Every table in the report, in the order they are printed."""
        return [table for section in self.sections for table in section.tables]

    def lines(self) -> list[str]:
        """The whole report as text."""
        out = [self.title, "=" * len(self.title)]
        if self.subtitle:
            out.append(self.subtitle)
        for section in self.sections:
            out.append("")
            out.extend(section.lines())
        return out

    def render(self) -> str:
        """The whole report as one string, ending in a newline."""
        return "\n".join(self.lines()) + "\n"

    def __str__(self) -> str:
        return self.render()


def money(value: float) -> str:
    """A figure with two places, for anything that is counted in dollars."""
    return f"{value:,.2f}"


def number(value: float, places: int = 1) -> str:
    """A figure with a fixed number of places and thousands separators."""
    return f"{value:,.{places}f}"


def share(value: float) -> str:
    """A fraction printed as a whole percentage."""
    return f"{value * 100:.0f}%"


__all__ = [
    "GAP",
    "RULE",
    "Align",
    "Column",
    "Report",
    "Section",
    "Table",
    "money",
    "number",
    "share",
]

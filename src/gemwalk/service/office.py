"""One place every desk is made, so nothing makes its own.

Each desk quietly builds the desks under it, so a report that wants four of
them ends up with four site desks, four label counters and four of everything
else, all pointing at the same book. Nothing is wrong with that until something
caches, and then two of them disagree.

The office builds each desk once and hands the same one out every time. It also
opens and migrates the book, which is the only thing in the package that knows
both how to find a book and what has to be true about it before it is used.
"""

from __future__ import annotations

from pathlib import Path
from types import TracebackType

from gemwalk.service.compliance import ComplianceDesk
from gemwalk.service.instruments import InstrumentDesk
from gemwalk.service.liquids import LiquidsDesk
from gemwalk.service.monitoring import MonitoringDesk
from gemwalk.service.piping import PipingDesk
from gemwalk.service.plant import PlantDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.service.surface import SurfaceDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.service.work import WorkDesk
from gemwalk.store.book import Book
from gemwalk.store.migrations import migrate, version


class Office:
    """Every desk in the building, all on one book."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.sites = SiteDesk(book)
        self.wellfield = WellfieldDesk(book)
        self.instruments = InstrumentDesk(book)
        self.piping = PipingDesk(book)
        self.monitoring = MonitoringDesk(book)
        self.compliance = ComplianceDesk(book)
        self.surface = SurfaceDesk(book)
        self.plant = PlantDesk(book)
        self.liquids = LiquidsDesk(book)
        self.work = WorkDesk(book)

    @classmethod
    def open(cls, path: str | Path) -> Office:
        """Open the book at *path*, bring it up to the schema, and staff it."""
        book = Book.open(path)
        migrate(book)
        return cls(book)

    @classmethod
    def memory(cls) -> Office:
        """An office on a book that lives only as long as the process."""
        book = Book.memory()
        migrate(book)
        return cls(book)

    @property
    def schema_version(self) -> int:
        """Which migration the book has been brought up to."""
        return version(self.book)

    def counts(self) -> dict[str, int]:
        """How many rows are in each table, in table order."""
        return {table: self.book.count(table) for table in self.book.tables()}

    def close(self) -> None:
        """Shut the book."""
        self.book.close()

    def __enter__(self) -> Office:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.close()


__all__ = ["Office"]

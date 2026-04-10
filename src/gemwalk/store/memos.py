"""Rows of the memo table."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, ClassVar

from gemwalk.model.memo import About, Memo
from gemwalk.store.book import Row
from gemwalk.store.columns import moment_text
from gemwalk.store.plant import unstamp
from gemwalk.store.repo import Repository


class MemoRepository(Repository[Memo]):
    """Every note anybody has put against anything."""

    table: ClassVar[str] = "memo"
    kind: ClassVar[str] = "note"
    key: ClassVar[str] = "id"
    order: ClassVar[str] = "at, id"
    auto: ClassVar[bool] = True
    columns: ClassVar[tuple[str, ...]] = (
        "id",
        "site",
        "about",
        "subject",
        "at",
        "by_whom",
        "body",
    )

    def read(self, row: Row) -> Memo:
        """Turn one memo row into a note."""
        return Memo(
            id=int(row["id"]),
            site=str(row["site"]),
            about=About(str(row["about"])),
            subject=str(row["subject"]),
            at=unstamp(str(row["at"])),
            by_whom=str(row["by_whom"]),
            body=str(row["body"]),
        )

    def write(self, item: Memo) -> dict[str, Any]:
        """Turn one note into the column values it is stored as."""
        return {
            "id": item.id,
            "site": item.site,
            "about": item.about.value,
            "subject": item.subject,
            "at": moment_text(item.at),
            "by_whom": item.by_whom,
            "body": item.body,
        }

    def with_key(self, item: Memo, key: int) -> Memo:
        """The same note carrying the number sqlite chose for it."""
        return replace(item, id=key)

    def about_subject(self, subject: str) -> list[Memo]:
        """Every note about one thing, oldest first."""
        return self.where("subject = ?", (subject,))

    def of_kind(self, site: str, about: About) -> list[Memo]:
        """Every note at one site about one kind of thing."""
        return self.where("site = ? AND about = ?", (site, about.value))

    def saying(self, site: str, word: str) -> list[Memo]:
        """Every note at one site whose words or subject contain a word."""
        pattern = f"%{word.lower()}%"
        rows = self.book.all(
            "SELECT * FROM memo WHERE site = ? AND (lower(body) LIKE ? OR lower(subject) LIKE ?) "
            "ORDER BY at, id",
            (site, pattern, pattern),
        )
        return [self.read(row) for row in rows]


__all__ = ["MemoRepository"]

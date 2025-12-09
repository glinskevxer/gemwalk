"""Rows of the header and lateral tables."""

from __future__ import annotations

from typing import Any, ClassVar

from gemwalk.clock import read_day
from gemwalk.model.piping import Header, Lateral
from gemwalk.store.book import Row
from gemwalk.store.columns import day_text, read_day_or_none
from gemwalk.store.repo import Repository


class HeaderRepository(Repository[Header]):
    """The trunk lines running out of the blower station."""

    table: ClassVar[str] = "header"
    kind: ClassVar[str] = "header"
    retired_column: ClassVar[str] = "retired_on"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "name",
        "diameter",
        "material",
        "length_feet",
        "installed_on",
        "retired_on",
    )

    def read(self, row: Row) -> Header:
        """Turn one header row into a header."""
        return Header(
            label=str(row["label"]),
            site=str(row["site"]),
            name=str(row["name"]),
            diameter=float(row["diameter"]),
            material=str(row["material"]),
            length_feet=float(row["length_feet"]),
            installed_on=read_day(str(row["installed_on"])),
            retired_on=read_day_or_none(row["retired_on"]),
        )

    def write(self, item: Header) -> dict[str, Any]:
        """Turn one header into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "name": item.name,
            "diameter": item.diameter,
            "material": item.material,
            "length_feet": item.length_feet,
            "installed_on": day_text(item.installed_on),
            "retired_on": day_text(item.retired_on),
        }


class LateralRepository(Repository[Lateral]):
    """The branch lines tying devices into headers."""

    table: ClassVar[str] = "lateral"
    kind: ClassVar[str] = "lateral"
    retired_column: ClassVar[str] = "retired_on"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "header",
        "diameter",
        "material",
        "length_feet",
        "installed_on",
        "retired_on",
    )

    def read(self, row: Row) -> Lateral:
        """Turn one lateral row into a lateral."""
        return Lateral(
            label=str(row["label"]),
            site=str(row["site"]),
            header=str(row["header"]),
            diameter=float(row["diameter"]),
            material=str(row["material"]),
            length_feet=float(row["length_feet"]),
            installed_on=read_day(str(row["installed_on"])),
            retired_on=read_day_or_none(row["retired_on"]),
        )

    def write(self, item: Lateral) -> dict[str, Any]:
        """Turn one lateral into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "header": item.header,
            "diameter": item.diameter,
            "material": item.material,
            "length_feet": item.length_feet,
            "installed_on": day_text(item.installed_on),
            "retired_on": day_text(item.retired_on),
        }

    def of_header(self, header: str) -> list[Lateral]:
        """Every lateral tied into one header."""
        return self.where("header = ?", (header,))


__all__ = ["HeaderRepository", "LateralRepository"]

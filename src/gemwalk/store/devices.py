"""Rows of the device table."""

from __future__ import annotations

from typing import Any, ClassVar

from gemwalk.clock import read_day
from gemwalk.model.device import Device, Kind, State
from gemwalk.store.book import Row
from gemwalk.store.columns import day_text, read_day_or_none
from gemwalk.store.repo import Repository


class DeviceRepository(Repository[Device]):
    """Every device ever put in the ground at every site in the book."""

    table: ClassVar[str] = "device"
    kind: ClassVar[str] = "device"
    columns: ClassVar[tuple[str, ...]] = (
        "label",
        "site",
        "area",
        "kind",
        "station",
        "total_depth",
        "screen_top",
        "screen_bottom",
        "state",
        "drilled_on",
        "connected_on",
        "offline_since",
        "abandoned_on",
        "hov_degrees",
        "hov_approved",
        "lateral",
    )

    def read(self, row: Row) -> Device:
        """Turn one device row into a device."""
        return Device(
            label=str(row["label"]),
            site=str(row["site"]),
            area=str(row["area"]),
            kind=Kind(str(row["kind"])),
            station=str(row["station"]),
            total_depth=float(row["total_depth"]),
            screen_top=float(row["screen_top"]),
            screen_bottom=float(row["screen_bottom"]),
            state=State(str(row["state"])),
            drilled_on=read_day(str(row["drilled_on"])),
            connected_on=read_day_or_none(row["connected_on"]),
            offline_since=read_day_or_none(row["offline_since"]),
            abandoned_on=read_day_or_none(row["abandoned_on"]),
            hov_degrees=None if row["hov_degrees"] is None else float(row["hov_degrees"]),
            hov_approved=read_day_or_none(row["hov_approved"]),
            lateral=None if row["lateral"] is None else str(row["lateral"]),
        )

    def write(self, item: Device) -> dict[str, Any]:
        """Turn one device into the column values it is stored as."""
        return {
            "label": item.label,
            "site": item.site,
            "area": item.area,
            "kind": item.kind.value,
            "station": item.station,
            "total_depth": item.total_depth,
            "screen_top": item.screen_top,
            "screen_bottom": item.screen_bottom,
            "state": item.state.value,
            "drilled_on": day_text(item.drilled_on),
            "connected_on": day_text(item.connected_on),
            "offline_since": day_text(item.offline_since),
            "abandoned_on": day_text(item.abandoned_on),
            "hov_degrees": item.hov_degrees,
            "hov_approved": day_text(item.hov_approved),
            "lateral": item.lateral,
        }

    def of_site(self, site: str) -> list[Device]:
        """Every device at one site, abandoned ones included."""
        return self.where("site = ?", (site,))

    def of_area(self, area: str) -> list[Device]:
        """Every device in one filling area."""
        return self.where("area = ?", (area,))

    def monitored(self, site: str) -> list[Device]:
        """Every device at one site that has to appear on the monthly run."""
        return self.where("site = ? AND state = ?", (site, State.CONNECTED.value))

    def in_state(self, site: str, state: State) -> list[Device]:
        """Every device at one site in one state."""
        return self.where("site = ? AND state = ?", (site, state.value))

    def on_lateral(self, lateral: str) -> list[Device]:
        """Every device piped to one lateral."""
        return self.where("lateral = ?", (lateral,))

    def unpiped(self, site: str) -> list[Device]:
        """Every device at one site with no lateral to send its gas down."""
        return self.where("site = ? AND lateral IS NULL", (site,))


__all__ = ["DeviceRepository"]

"""Sheets: the same records again, in the shape a spreadsheet wants.

A report is written to be read. A sheet is written to be opened in something
else and totalled by somebody who does not have this package. So the two are
built separately rather than one being derived from the other: a report can
merge a heading and leave a repeated value blank, and a sheet must never do
either, because the row is the unit and every row has to stand alone.

Every sheet is a heading row and a list of rows of plain strings. Nothing here
writes a file. The command line does that, so the same sheets can be printed,
piped or written, and so a test does not need a directory to check one.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from collections.abc import Sequence
from dataclasses import dataclass

from gemwalk.clock import Quarter, show_moment
from gemwalk.errors import UnknownError
from gemwalk.service.office import Office


@dataclass(frozen=True)
class Sheet:
    """One heading row and the rows under it."""

    name: str
    headings: tuple[str, ...]
    rows: list[tuple[str, ...]]

    def __post_init__(self) -> None:
        for row in self.rows:
            if len(row) != len(self.headings):
                raise UnknownError("sheet row", f"{self.name} row of {len(row)}")

    @property
    def is_empty(self) -> bool:
        """True when the sheet has a heading and nothing under it."""
        return not self.rows

    def text(self) -> str:
        """The sheet as comma separated text, with the heading row first."""
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(self.headings)
        writer.writerows(self.rows)
        return out.getvalue()


def _rows(headings: Sequence[str], name: str, rows: list[tuple[str, ...]]) -> Sheet:
    return Sheet(name=name, headings=tuple(headings), rows=rows)


def readings_sheet(office: Office, run: str) -> Sheet:
    """Every wellhead reading on one run."""
    pass_ = office.monitoring.runs.get(run)
    rows: list[tuple[str, ...]] = []
    for reading in office.monitoring.readings.of_run(run):
        result = office.monitoring.assessment(run, reading.device)
        analysis = reading.analysis
        rows.append(
            (
                pass_.label,
                str(reading.taken_on),
                reading.device,
                f"{reading.methane:g}",
                f"{reading.carbon:g}",
                f"{reading.oxygen:g}",
                f"{reading.balance:g}",
                f"{reading.temperature:g}",
                f"{reading.static:g}",
                f"{reading.applied:g}",
                f"{reading.flow:g}",
                f"{reading.valve_before:g}",
                f"{reading.valve_after:g}",
                f"{analysis.corrected_methane.value:.1f}",
                str(analysis.character()),
                "; ".join(str(kind) for kind in result.kinds),
                reading.note,
            )
        )
    return _rows(
        (
            "run",
            "taken_on",
            "device",
            "methane",
            "carbon_dioxide",
            "oxygen",
            "balance",
            "temperature_f",
            "static_wc",
            "applied_wc",
            "flow_scfm",
            "valve_before",
            "valve_after",
            "corrected_methane",
            "character",
            "over",
            "note",
        ),
        f"readings-{run}",
        rows,
    )


def records_sheet(office: Office, site: str, on: dt.date) -> Sheet:
    """Every open exceedance at a site, with where its clock has got to."""
    rows: list[tuple[str, ...]] = []
    for standing in office.compliance.board(site, on):
        found = standing.exceedance
        rows.append(
            (
                found.label,
                found.site,
                found.device,
                str(found.kind),
                str(found.opened_on),
                f"{found.value:g}",
                f"{found.limit_value:g}",
                str(found.stage),
                str(standing.expected),
                str(standing.due),
                str(standing.days_left),
                "yes" if standing.late else "no",
            )
        )
    return _rows(
        (
            "record",
            "site",
            "device",
            "kind",
            "opened_on",
            "reading",
            "limit",
            "stage",
            "expected_stage",
            "due",
            "days_left",
            "late",
        ),
        f"records-{site}",
        rows,
    )


def orders_sheet(office: Office, site: str, first: dt.date, last: dt.date) -> Sheet:
    """Every work order raised at a site inside a range of days."""
    rows: list[tuple[str, ...]] = []
    for order in office.work.orders.between_days(site, first.isoformat(), last.isoformat()):
        rows.append(
            (
                order.label,
                str(order.job),
                order.target,
                order.because or "",
                str(order.raised_on),
                str(order.due_on),
                str(order.state),
                order.crew,
                str(order.done_on or ""),
                "yes" if order.was_late() else "no",
                order.note,
            )
        )
    return _rows(
        (
            "order",
            "job",
            "where",
            "because",
            "raised_on",
            "due_on",
            "state",
            "crew",
            "done_on",
            "late",
            "note",
        ),
        f"orders-{site}",
        rows,
    )


def surface_sheet(office: Office, site: str, quarter: Quarter) -> Sheet:
    """Every spot found in one quarter, with the clock it is on."""
    subpart = office.sites.standard_of(site)
    rows: list[tuple[str, ...]] = []
    hits = office.surface.hits.between_days(
        site, quarter.first_day.isoformat(), quarter.last_day.isoformat()
    )
    for hit in hits:
        rows.append(
            (
                hit.label,
                hit.walk,
                hit.area,
                hit.station,
                f"{hit.reading:g}",
                str(hit.cover),
                str(hit.found_on),
                str(hit.step),
                str(hit.attempt),
                str(hit.repaired_on or ""),
                str(hit.remonitor_on or ""),
                str(hit.due(subpart) or ""),
                str(hit.closed_on or ""),
            )
        )
    return _rows(
        (
            "spot",
            "walk",
            "area",
            "station",
            "reading_ppmv",
            "cover",
            "found_on",
            "step",
            "attempt",
            "repaired_on",
            "remonitored_on",
            "due",
            "closed_on",
        ),
        f"surface-{quarter}",
        rows,
    )


def calibrations_sheet(office: Office, label: str, zone: str) -> Sheet:
    """Every calibration of one meter."""
    rows: list[tuple[str, ...]] = []
    for check in office.instruments.history(label):
        rows.append(
            (
                check.instrument,
                show_moment(check.at, zone),
                check.standard,
                f"{check.expected:g}",
                f"{check.before:g}",
                f"{check.after:g}",
                f"{check.drift:.2f}",
                f"{check.error:.2f}",
                "yes" if check.passed else "no",
                check.by_whom,
                check.note,
            )
        )
    return _rows(
        (
            "instrument",
            "at",
            "standard",
            "expected",
            "before",
            "after",
            "drift_pct",
            "error_pct",
            "passed",
            "by",
            "note",
        ),
        f"calibrations-{label}",
        rows,
    )


def devices_sheet(office: Office, site: str) -> Sheet:
    """Every device at one site, with its construction and its state."""
    rows: list[tuple[str, ...]] = []
    for device in office.wellfield.devices.of_site(site):
        rows.append(
            (
                device.label,
                device.area,
                str(device.kind),
                device.station,
                f"{device.total_depth:g}",
                f"{device.screen_top:g}",
                f"{device.screen_bottom:g}",
                f"{device.influence:g}",
                str(device.state),
                str(device.drilled_on),
                str(device.connected_on or ""),
                device.lateral or "",
                str(device.abandoned_on or ""),
            )
        )
    return _rows(
        (
            "device",
            "area",
            "kind",
            "station",
            "total_depth",
            "screen_top",
            "screen_bottom",
            "influence_ft",
            "state",
            "drilled_on",
            "connected_on",
            "lateral",
            "abandoned_on",
        ),
        f"devices-{site}",
        rows,
    )


def faults_sheet(office: Office, site: str) -> Sheet:
    """Every fault ever found on one site's cover."""
    rows: list[tuple[str, ...]] = []
    for fault in office.surface.faults.of_site(site):
        rows.append(
            (
                fault.label,
                fault.area,
                str(fault.kind),
                fault.station,
                f"{fault.extent:g}",
                str(fault.found_on),
                fault.found_by,
                str(fault.due or ""),
                str(fault.fixed_on or ""),
                fault.note,
            )
        )
    return _rows(
        (
            "fault",
            "area",
            "kind",
            "station",
            "square_feet",
            "found_on",
            "found_by",
            "due",
            "fixed_on",
            "note",
        ),
        f"faults-{site}",
        rows,
    )


def notes_sheet(office: Office, site: str, zone: str) -> Sheet:
    """Every note anybody has written at one site."""
    rows: list[tuple[str, ...]] = []
    for memo in office.memos.memos.of_site(site):
        rows.append(
            (
                str(memo.id),
                str(memo.about),
                memo.subject,
                show_moment(memo.at, zone),
                memo.by_whom,
                memo.body,
            )
        )
    return _rows(("id", "about", "subject", "at", "by", "body"), f"notes-{site}", rows)


def everything(office: Office, site: str, on: dt.date) -> list[Sheet]:
    """Every sheet a site has, for somebody who wants the lot.

    The readings are one sheet per run rather than one sheet for all of them,
    because a run is the unit somebody works with and a single sheet of every
    reading a site ever took is a file nobody opens twice.
    """
    zone = office.sites.zone_of(site)
    made = [
        devices_sheet(office, site),
        records_sheet(office, site, on),
        orders_sheet(office, site, dt.date(on.year, 1, 1), on),
        faults_sheet(office, site),
        notes_sheet(office, site, zone),
    ]
    made.extend(readings_sheet(office, run.label) for run in office.monitoring.runs.of_site(site))
    made.extend(
        surface_sheet(office, site, quarter)
        for quarter in sorted(
            {Quarter.of(walk.started_on) for walk in office.surface.walks.of_site(site)}
        )
    )
    made.extend(
        calibrations_sheet(office, meter.label, zone)
        for meter in office.instruments.instruments.of_site(site)
    )
    return [sheet for sheet in made if not sheet.is_empty]


__all__ = [
    "Sheet",
    "calibrations_sheet",
    "devices_sheet",
    "everything",
    "faults_sheet",
    "notes_sheet",
    "orders_sheet",
    "readings_sheet",
    "records_sheet",
    "surface_sheet",
]

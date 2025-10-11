"""Run one site through a season and check the numbers come out right.

This is not a test. It is the thing that runs against an installed wheel, in a
container with no source tree and no pytest, to answer one question: does the
package work when it is not being run out of its own repository.

It walks a real sequence. A site is opened, areas are cut, wells are drilled
and piped, the wellfield is read three months running with one wellhead going
hot, the cover is walked and a spot found, the flare is logged through a block
that dips, condensate is hauled, and then every report is printed. Each step
asserts what it expects, so a failure names the step rather than a traceback.
"""

from __future__ import annotations

import datetime as dt
import sys
import tempfile
from pathlib import Path

from gemwalk.clock import Month, Quarter, read_moment
from gemwalk.model.liquids import SumpKind
from gemwalk.model.plant import ControlKind
from gemwalk.model.work import Job
from gemwalk.report.compliance import compliance_report
from gemwalk.report.monthly import monthly_report
from gemwalk.service.office import Office

SITE = "NORTHRIDGE"
ZONE = "America/Chicago"
CLEAN: dict[str, float] = {
    "methane": 52.4,
    "carbon": 38.1,
    "oxygen": 0.6,
    "balance": 8.9,
    "temperature": 118.2,
    "static": -1.4,
    "applied": -12.0,
    "flow": 42.0,
    "valve_before": 3.0,
    "valve_after": 3.0,
}


class SmokeError(RuntimeError):
    """A step of the walk did not do what it was supposed to."""


def expect(step: str, got: object, wanted: object) -> None:
    """Insist a step produced what it was supposed to."""
    if got != wanted:
        raise SmokeError(f"{step}: got {got!r}, wanted {wanted!r}")


def insist(step: str, truth: bool) -> None:
    """Insist a step is true."""
    if not truth:
        raise SmokeError(step)


def build(office: Office) -> None:
    """Open the site, cut the areas, sink the wells and lay the pipe."""
    office.sites.open_site(
        SITE,
        "Northridge Sanitary Landfill",
        subpart="XXX",
        permit="MSW-1188-04",
        zone=ZONE,
        design_capacity=8_400_000.0,
        opened_on=dt.date(1998, 6, 1),
    )
    office.sites.add_area(
        "A-03", SITE, "phase 3 north slope", acres=12.4, first_waste=dt.date(2019, 4, 15)
    )
    office.sites.add_area("A-04", SITE, "phase 4 east", acres=8.0, first_waste=dt.date(2020, 6, 1))
    header = office.piping.lay_header(
        SITE,
        "north trunk",
        diameter=18.0,
        material="HDPE SDR17",
        length_feet=2_140.0,
        on=dt.date(2019, 9, 3),
    ).label
    lateral = office.piping.lay_lateral(
        SITE,
        header,
        diameter=8.0,
        material="HDPE SDR17",
        length_feet=460.0,
        on=dt.date(2019, 9, 3),
    ).label
    for index in range(6):
        device = office.wellfield.drill(
            SITE,
            "A-03" if index % 2 == 0 else "A-04",
            station=f"N {12 + index}+40 E 3+15",
            total_depth=92.0,
            screen_top=22.0,
            screen_bottom=86.0,
            on=dt.date(2021, 5, 12),
        ).label
        office.piping.tie_in(device, lateral)
        office.wellfield.connect(device, dt.date(2021, 6, 2))
    expect("roster", len(office.wellfield.roster(SITE)), 6)
    office.plant.install(
        "CD-01",
        SITE,
        "west flare",
        kind=ControlKind.ENCLOSED_FLARE,
        capacity=2_400.0,
        on=dt.date(2016, 4, 1),
        minimum_temp=1_400.0,
    )
    office.liquids.add_sump(
        SITE,
        "HD-01 low point",
        kind=SumpKind.KNOCKOUT,
        capacity=550.0,
        on=dt.date(2019, 9, 3),
    )


def walk(office: Office, on: dt.date, hot: dict[str, dict[str, float]]) -> str:
    """Read every wellhead on the roster on one day."""
    run = office.monitoring.open_run(SITE, on, monitor="D. Kasprzak", meter="GEM5000-40912").label
    for device in office.wellfield.roster(SITE):
        fields = dict(CLEAN)
        fields.update(hot.get(device.label, {}))
        office.monitoring.record(run, device.label, on=on, **fields)  # type: ignore[arg-type]
    office.monitoring.close_run(run, on)
    return run


def season(office: Office) -> None:
    """Three months of monitoring, with one wellhead going hot and coming back."""
    april = walk(office, dt.date(2025, 4, 8), {"VW-002": {"temperature": 138.0}})
    opened = office.compliance.post_run(april)
    expect("first posting", opened.opened, ["EX-2025-001"])

    may = walk(office, dt.date(2025, 5, 6), {"VW-002": {"temperature": 136.0}})
    again = office.compliance.post_run(may)
    expect("second posting opened nothing", again.opened, [])
    expect("second posting continued", again.continued, ["EX-2025-001"])
    expect("second posting escalated", again.escalated, ["EX-2025-001"])

    # The record was opened on the eighth of April and the May reading is
    # twenty eight days later, so it has already been through both of the
    # earlier windows. The order takes the window the record is actually at,
    # which is the hundred and twenty day one, and not a fresh five days.
    order = office.work.raise_for_exceedance("EX-2025-001", Job.WELLHEAD, dt.date(2025, 5, 7))
    expect("the order takes the record's date", order.due_on, dt.date(2025, 8, 6))
    office.work.assign(order.label, "north crew", dt.date(2025, 5, 7))
    office.work.finish(order.label, dt.date(2025, 5, 9), "seal replaced")
    insist("the record is still open", office.compliance.exceedances.get("EX-2025-001").is_open)

    june = walk(office, dt.date(2025, 6, 10), {})
    closed = office.compliance.post_run(june)
    expect("third posting closed it", closed.closed, ["EX-2025-001"])
    insist(
        "nothing is open",
        not office.compliance.exceedances.open_at(SITE),
    )


def cover(office: Office) -> None:
    """One walkover of the cover, with a spot that takes two goes."""
    walk_label = office.surface.open_walk(
        SITE,
        dt.date(2025, 5, 13),
        monitor="T. Wierzbicki",
        instrument="TVA1000B-8841",
        background=2.0,
        wind_mean=3.4,
        wind_gust=7.1,
    ).label
    hit = office.surface.mark(walk_label, "A-03", "grid 14-J", 720.0, on=dt.date(2025, 5, 13)).label
    office.surface.finish_walk(walk_label, dt.date(2025, 5, 15))
    subpart = office.sites.standard_of(SITE)
    expect("the repair window", office.surface.hits.get(hit).due(subpart), dt.date(2025, 5, 23))
    office.surface.repair(hit, dt.date(2025, 5, 22))
    expect(
        "the remonitor window runs from the repair",
        office.surface.hits.get(hit).due(subpart),
        dt.date(2025, 6, 1),
    )
    after = office.surface.remonitor(hit, dt.date(2025, 5, 28), 640.0)
    expect("a failed remonitor starts a second attempt", after.attempt, 2)
    office.surface.repair(hit, dt.date(2025, 5, 30))
    office.surface.remonitor(hit, dt.date(2025, 6, 3), 180.0)
    insist("the spot closed", not office.surface.hits.get(hit).is_open)
    expect(
        "no quarters missed",
        office.surface.quarters_missed(SITE, Quarter(2025, 2), Quarter(2025, 2)),
        [],
    )


def plant(office: Office) -> None:
    """A morning at the flare with a block that averages under the floor."""
    for hour, temperature in ((9, 1_398.0), (10, 1_396.0), (11, 1_399.0)):
        office.plant.log(
            "CD-01",
            read_moment(f"2025-06-11 {hour:02d}:00", ZONE),
            running=True,
            flow=1_180.0,
            methane=49.2,
            temperature=temperature,
        )
    blocks = office.plant.deviations(
        "CD-01",
        read_moment("2025-06-11 09:00", ZONE),
        read_moment("2025-06-11 12:00", ZONE),
    )
    expect("one block under the floor", len(blocks), 1)
    outage = office.plant.start_outage(
        "CD-01", read_moment("2025-06-12 06:00", ZONE), "blower bearing"
    )
    office.plant.end_outage(outage.label, read_moment("2025-06-12 15:00", ZONE))
    expect(
        "no long outages",
        office.plant.long_outages(SITE, read_moment("2025-06-20 09:00", ZONE)),
        [],
    )


def liquids(office: Office) -> None:
    """A tape drop that explains a dead wellhead, and a load off the sump."""
    office.liquids.tape("VW-003", dt.date(2025, 6, 9), 20.0)
    wet = office.liquids.flooded(SITE, dt.date(2025, 6, 10))
    expect("one well under water", [w.device.label for w in wet], ["VW-003"])
    office.liquids.pump(
        "CS-001",
        read_moment("2025-06-12 10:20", ZONE),
        410.0,
        hauler="Vestermark Vacuum",
        bound_for="leachate pretreatment",
    )
    hauled = office.liquids.hauled(
        SITE, read_moment("2025-06-01 00:00", ZONE), read_moment("2025-07-01 00:00", ZONE)
    )
    expect("gallons hauled", round(hauled), 410)


def paperwork(office: Office, quiet: bool) -> None:
    """Print every report and check each one says what it should."""
    month = monthly_report(office, SITE, Month(2025, 4), on=dt.date(2025, 4, 30))
    insist("the monthly report names the hot wellhead", "VW-002" in month.render())
    quarter = compliance_report(office, SITE, Quarter(2025, 2))
    text = quarter.render()
    insist("the quarterly report names the walkover", "SW-2025Q2-01" in text)
    insist("the quarterly report names the flare", "CD-01" in text)
    if not quiet:
        print(month.render())
        print(text)


def main(argv: list[str] | None = None) -> int:
    """Run the whole walk against a book in a temporary directory."""
    args = list(sys.argv[1:] if argv is None else argv)
    quiet = "--quiet" in args
    with (
        tempfile.TemporaryDirectory() as room,
        Office.open(Path(room) / "smoke.sqlite3") as office,
    ):
        build(office)
        season(office)
        cover(office)
        plant(office)
        liquids(office)
        paperwork(office, quiet)
        counts = office.counts()
    insist("the book has readings in it", counts["reading"] == 18)
    if not quiet:
        print("smoke: every step did what it was supposed to")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

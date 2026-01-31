"""Fill a book with a year of a plausible site, so it can be looked at.

Nothing in here is random. A seeded book with a different shape every time is a
book nobody can write a test against and nobody can compare two versions of, so
the numbers come out of a small deterministic generator that produces the same
site every time it is run.

The site is built to have the interesting cases in it rather than the average
ones: a wellhead that runs hot for three months and comes back, one that leaks
air, one that floods, a surface spot that takes two goes at the cover, a flare
block that averages under its floor, and an area that is short of collection and
past the day it was due it. A book with none of those in it looks tidy and
teaches nothing.
"""

from __future__ import annotations

import datetime as dt

from gemwalk.clock import read_moment
from gemwalk.model.instrument import Meter
from gemwalk.model.liquids import SumpKind
from gemwalk.model.plant import ControlKind
from gemwalk.model.work import Job
from gemwalk.service.office import Office

SITE = "NORTHRIDGE"
ZONE = "America/Chicago"
MONITOR = "D. Kasprzak"
METER = "GEM5000-40912"
DETECTOR = "TVA1000B-8841"
WELLS = 12

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

HOT = {"temperature": 138.4, "methane": 49.0, "carbon": 36.0, "balance": 14.4}
LEAKING = {"methane": 41.0, "carbon": 30.0, "oxygen": 6.1, "balance": 22.8, "flow": 22.0}
DROWNED = {"methane": 4.0, "carbon": 3.0, "oxygen": 2.0, "balance": 91.0, "flow": 0.0}

RUN_DAYS = (
    dt.date(2025, 1, 14),
    dt.date(2025, 2, 11),
    dt.date(2025, 3, 11),
    dt.date(2025, 4, 8),
    dt.date(2025, 5, 13),
    dt.date(2025, 6, 10),
)


def _shape(device: str, day: dt.date) -> dict[str, float]:
    """What one wellhead read on one day, which is fixed and not random."""
    if device == "VW-004" and day >= dt.date(2025, 3, 11) and day <= dt.date(2025, 5, 13):
        return HOT
    if device == "VW-007":
        return LEAKING
    if device == "VW-011" and day >= dt.date(2025, 4, 8):
        return DROWNED
    return {}


def build(office: Office) -> None:
    """Open the site, cut the areas, lay the pipe and sink the wells."""
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
    office.wellfield.set_radius("A-03", 150.0)
    office.wellfield.set_radius("A-04", 150.0)
    header = office.piping.lay_header(
        SITE,
        "north trunk",
        diameter=18.0,
        material="HDPE SDR17",
        length_feet=2_140.0,
        on=dt.date(2019, 9, 3),
    ).label
    laterals = [
        office.piping.lay_lateral(
            SITE,
            header,
            diameter=8.0,
            material="HDPE SDR17",
            length_feet=460.0,
            on=dt.date(2019, 9, 3),
        ).label
        for _ in range(2)
    ]
    for index in range(WELLS):
        device = office.wellfield.drill(
            SITE,
            "A-03" if index % 2 == 0 else "A-04",
            station=f"N {10 + index}+40 E {3 + index % 4}+15",
            total_depth=88.0 + index,
            screen_top=20.0,
            screen_bottom=82.0 + index,
            on=dt.date(2021, 5, 12),
        ).label
        office.piping.tie_in(device, laterals[index % 2])
        office.wellfield.connect(device, dt.date(2021, 6, 2))
    office.plant.install(
        "CD-01",
        SITE,
        "west flare",
        kind=ControlKind.ENCLOSED_FLARE,
        capacity=2_400.0,
        on=dt.date(2016, 4, 1),
        floor_degrees=1_400.0,
    )
    office.liquids.add_sump(
        SITE,
        "HD-01 low point",
        kind=SumpKind.KNOCKOUT,
        capacity=550.0,
        on=dt.date(2019, 9, 3),
    )
    for label, kind, model in (
        (METER, Meter.ANALYSER, "GEM5000"),
        (DETECTOR, Meter.DETECTOR, "TVA1000B"),
    ):
        office.instruments.add(
            label,
            SITE,
            kind=kind,
            maker="Verrick Instruments",
            model=model,
            serial=label.rsplit("-", 1)[-1],
            on=dt.date(2022, 3, 1),
        )


def calibrate(office: Office, label: str, day: dt.date, expected: float) -> None:
    """Calibrate one meter on the morning of a day it is used."""
    office.instruments.calibrate(
        label,
        read_moment(f"{day.isoformat()} 05:40", ZONE),
        standard=f"{expected:g} span",
        expected=expected,
        before=expected * 0.99,
        after=expected,
        by_whom=MONITOR,
    )


def monitor(office: Office) -> None:
    """Walk the wellfield once a month and post every run."""
    for day in RUN_DAYS:
        calibrate(office, METER, day, 50.0)
        run = office.monitoring.open_run(SITE, day, monitor=MONITOR, meter=METER).label
        for device in office.wellfield.roster(SITE):
            fields = dict(CLEAN)
            fields.update(_shape(device.label, day))
            office.monitoring.record(run, device.label, on=day, **fields)  # type: ignore[arg-type]
        office.monitoring.close_run(run, day)
        office.compliance.post_run(run)


def cover(office: Office) -> None:
    """Walk the cover once a quarter, with one spot that takes two goes."""
    for day, marks in (
        (dt.date(2025, 2, 18), ()),
        (dt.date(2025, 5, 20), (("A-03", "grid 14-J", 720.0),)),
    ):
        calibrate(office, DETECTOR, day, 500.0)
        walk = office.surface.open_walk(
            SITE,
            day,
            monitor="T. Wierzbicki",
            instrument=DETECTOR,
            background=2.0,
            wind_mean=3.4,
            wind_gust=7.1,
        ).label
        for area, station, reading in marks:
            office.surface.mark(walk, area, station, reading, on=day)
        office.surface.finish_walk(walk, day)
    office.surface.repair("SH-2025Q2-001", dt.date(2025, 5, 27))
    office.surface.remonitor("SH-2025Q2-001", dt.date(2025, 6, 3), 640.0)


def plant(office: Office) -> None:
    """Run the flare through a morning that averages under its floor."""
    for hour, temperature in ((9, 1_398.0), (10, 1_396.0), (11, 1_399.0), (12, 1_520.0)):
        office.plant.log(
            "CD-01",
            read_moment(f"2025-06-11 {hour:02d}:00", ZONE),
            running=True,
            flow=1_180.0,
            methane=49.2,
            temperature=temperature,
        )
    outage = office.plant.start_outage(
        "CD-01", read_moment("2025-06-12 06:00", ZONE), "blower bearing"
    )
    office.plant.end_outage(outage.label, read_moment("2025-06-12 15:00", ZONE))


def liquids(office: Office) -> None:
    """Tape the wells and haul a load off the sump."""
    for device, depth in (("VW-011", 18.0), ("VW-007", 78.0), ("VW-001", 84.0)):
        office.liquids.tape(device, dt.date(2025, 6, 9), depth)
    office.liquids.pump(
        "CS-001",
        read_moment("2025-06-12 10:20", ZONE),
        410.0,
        hauler="Vestermark Vacuum",
        bound_for="leachate pretreatment",
    )


def work(office: Office) -> None:
    """Raise one order off a record, and one because somebody noticed something."""
    open_records = office.compliance.exceedances.open_at(SITE)
    for record in open_records[:1]:
        order = office.work.raise_for_exceedance(record.label, Job.WELLHEAD, dt.date(2025, 6, 11))
        office.work.assign(order.label, "north crew", dt.date(2025, 6, 11))
    office.work.raise_order(
        SITE,
        Job.DEWATER,
        "VW-011",
        on=dt.date(2025, 6, 10),
        due=dt.date(2025, 6, 24),
        note="standing full, put a pump in it",
    )


def seed(office: Office) -> dict[str, int]:
    """Fill a book with the whole year and say what went in."""
    build(office)
    monitor(office)
    cover(office)
    plant(office)
    liquids(office)
    work(office)
    return office.counts()


__all__ = ["RUN_DAYS", "SITE", "WELLS", "ZONE", "seed"]

"""A furnished site, so a suite about reports is not a suite about setup.

Everything here writes through the ordinary desks. Nothing reaches into the
book, because a fixture that inserts rows the services would have refused is a
fixture that tests something the site cannot actually be in.
"""

from __future__ import annotations

import datetime as dt

from gemwalk.clock import read_moment
from gemwalk.model.device import Kind
from gemwalk.model.liquids import SumpKind
from gemwalk.model.plant import ControlKind
from gemwalk.service.office import Office

SITE = "NORTHRIDGE"
ZONE = "America/Chicago"
OPENED = dt.date(1998, 6, 1)
DRILLED = dt.date(2021, 5, 12)
WIRED = dt.date(2021, 6, 2)

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


def furnish(office: Office, *, wells: int = 4, subpart: str = "XXX") -> Office:
    """Open a site, cut two areas, sink some wells and pipe them up."""
    office.sites.open_site(
        SITE,
        "Northridge Sanitary Landfill",
        subpart=subpart,
        permit="MSW-1188-04",
        zone=ZONE,
        design_capacity=8_400_000.0,
        opened_on=OPENED,
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
    for index in range(wells):
        device = office.wellfield.drill(
            SITE,
            "A-03" if index % 2 == 0 else "A-04",
            kind=Kind.VERTICAL,
            station=f"N {12 + index}+40 E 3+15",
            total_depth=92.0,
            screen_top=22.0,
            screen_bottom=86.0,
            on=DRILLED,
        ).label
        office.piping.tie_in(device, lateral)
        office.wellfield.connect(device, WIRED)
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
        SITE, "HD-01 low point", kind=SumpKind.KNOCKOUT, capacity=550.0, on=dt.date(2019, 9, 3)
    )
    return office


def walk_wellfield(
    office: Office,
    on: dt.date,
    changes: dict[str, dict[str, float]] | None = None,
    *,
    close: bool = True,
) -> str:
    """Run one monitoring pass, with any wellheads named in *changes* altered."""
    run = office.monitoring.open_run(SITE, on, monitor="D. Kasprzak", meter="GEM5000-40912").label
    for device in office.wellfield.roster(SITE):
        fields = dict(CLEAN)
        fields.update((changes or {}).get(device.label, {}))
        office.monitoring.record(run, device.label, on=on, **fields)  # type: ignore[arg-type]
    if close:
        office.monitoring.close_run(run, on)
    return run


def run_plant(office: Office, day: str, temperatures: tuple[float, ...]) -> None:
    """Write a block of operating records for the flare on one morning."""
    for index, temperature in enumerate(temperatures):
        office.plant.log(
            "CD-01",
            read_moment(f"{day} {9 + index:02d}:00", ZONE),
            running=True,
            flow=1_180.0,
            methane=49.2,
            temperature=temperature,
        )


def walk_cover(
    office: Office,
    on: dt.date,
    marks: tuple[tuple[str, str, float], ...] = (),
    *,
    background: float = 2.0,
    finish: bool = True,
) -> str:
    """Run one walkover of the cover, marking whatever is handed in."""
    walk = office.surface.open_walk(
        SITE,
        on,
        monitor="T. Wierzbicki",
        instrument="TVA1000B-8841",
        background=background,
        wind_mean=3.4,
        wind_gust=7.1,
    ).label
    for area, station, reading in marks:
        office.surface.mark(walk, area, station, reading, on=on)
    if finish:
        office.surface.finish_walk(walk, on)
    return walk

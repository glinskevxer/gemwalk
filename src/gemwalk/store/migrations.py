"""The schema, written as a list of migrations that only ever grows.

A migration is a number, a name and a script. The book records the ones it has
run in ``schema_log``, so opening an old book applies what it is missing and
opening a current one does nothing. Nothing here is ever edited after it has
shipped: a mistake in migration four is fixed by migration nineteen.

Each migration runs inside one transaction, so a script that fails half way
leaves the book on the version it started at.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from gemwalk.errors import DesignError, StateError
from gemwalk.store.book import Book

LOG_TABLE = """
CREATE TABLE IF NOT EXISTS schema_log (
  number   INTEGER PRIMARY KEY,
  name     TEXT NOT NULL,
  ran_at   TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Migration:
    """One numbered step of the schema."""

    number: int
    name: str
    script: str

    def __post_init__(self) -> None:
        if self.number < 1:
            raise DesignError("migration", "migrations are numbered from one")
        if not self.script.strip():
            raise DesignError("migration", f"migration {self.number} has no script")


M001 = Migration(
    number=1,
    name="sites and the areas waste goes into",
    script="""
    CREATE TABLE site (
      label            TEXT PRIMARY KEY,
      name             TEXT NOT NULL,
      standard         TEXT NOT NULL,
      permit           TEXT NOT NULL,
      zone             TEXT NOT NULL,
      design_capacity  REAL NOT NULL,
      opened_on        TEXT NOT NULL,
      closed_on        TEXT
    );

    CREATE TABLE area (
      label        TEXT PRIMARY KEY,
      site         TEXT NOT NULL REFERENCES site(label),
      name         TEXT NOT NULL,
      acres        REAL NOT NULL,
      first_waste  TEXT NOT NULL,
      last_waste   TEXT,
      closed_on    TEXT,
      cover        TEXT NOT NULL
    );

    CREATE INDEX area_by_site ON area(site);
    """,
)

M002 = Migration(
    number=2,
    name="the counters every label is handed out of",
    script="""
    CREATE TABLE label_run (
      kind   TEXT NOT NULL,
      scope  TEXT NOT NULL,
      last   INTEGER NOT NULL,
      PRIMARY KEY (kind, scope)
    );
    """,
)

M003 = Migration(
    number=3,
    name="the devices sunk into the refuse",
    script="""
    CREATE TABLE device (
      label          TEXT PRIMARY KEY,
      site           TEXT NOT NULL REFERENCES site(label),
      area           TEXT NOT NULL REFERENCES area(label),
      kind           TEXT NOT NULL,
      station        TEXT NOT NULL,
      total_depth    REAL NOT NULL,
      screen_top     REAL NOT NULL,
      screen_bottom  REAL NOT NULL,
      state          TEXT NOT NULL,
      drilled_on     TEXT NOT NULL,
      connected_on   TEXT,
      offline_since  TEXT,
      abandoned_on   TEXT,
      hov_degrees    REAL,
      hov_approved   TEXT
    );

    CREATE INDEX device_by_site ON device(site);
    CREATE INDEX device_by_area ON device(area);
    CREATE INDEX device_by_state ON device(state);
    """,
)

M004 = Migration(
    number=4,
    name="the pipe tree the devices hang off",
    script="""
    CREATE TABLE header (
      label         TEXT PRIMARY KEY,
      site          TEXT NOT NULL REFERENCES site(label),
      name          TEXT NOT NULL,
      diameter      REAL NOT NULL,
      material      TEXT NOT NULL,
      length_feet   REAL NOT NULL,
      installed_on  TEXT NOT NULL,
      retired_on    TEXT
    );

    CREATE TABLE lateral (
      label         TEXT PRIMARY KEY,
      site          TEXT NOT NULL REFERENCES site(label),
      header        TEXT NOT NULL REFERENCES header(label),
      diameter      REAL NOT NULL,
      material      TEXT NOT NULL,
      length_feet   REAL NOT NULL,
      installed_on  TEXT NOT NULL,
      retired_on    TEXT
    );

    ALTER TABLE device ADD COLUMN lateral TEXT REFERENCES lateral(label);

    CREATE INDEX header_by_site ON header(site);
    CREATE INDEX lateral_by_site ON lateral(site);
    CREATE INDEX lateral_by_header ON lateral(header);
    CREATE INDEX device_by_lateral ON device(lateral);
    """,
)

M005 = Migration(
    number=5,
    name="the monthly monitoring run and the wellhead readings on it",
    script="""
    CREATE TABLE run (
      label      TEXT PRIMARY KEY,
      site       TEXT NOT NULL REFERENCES site(label),
      started_on TEXT NOT NULL,
      closed_on  TEXT,
      monitor    TEXT NOT NULL,
      meter      TEXT NOT NULL,
      note       TEXT NOT NULL DEFAULT ''
    );

    CREATE TABLE reading (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      run           TEXT NOT NULL REFERENCES run(label),
      device        TEXT NOT NULL REFERENCES device(label),
      taken_on      TEXT NOT NULL,
      methane       REAL NOT NULL,
      carbon        REAL NOT NULL,
      oxygen        REAL NOT NULL,
      balance       REAL NOT NULL,
      temperature   REAL NOT NULL,
      static        REAL NOT NULL,
      applied       REAL NOT NULL,
      flow          REAL NOT NULL,
      valve_before  REAL NOT NULL,
      valve_after   REAL NOT NULL,
      note          TEXT NOT NULL DEFAULT '',
      UNIQUE (run, device)
    );

    CREATE INDEX run_by_site ON run(site);
    CREATE INDEX reading_by_run ON reading(run);
    CREATE INDEX reading_by_device ON reading(device);
    CREATE INDEX reading_by_day ON reading(taken_on);
    """,
)

M006 = Migration(
    number=6,
    name="what a site has elected where the standard leaves a choice",
    script="""
    ALTER TABLE site ADD COLUMN nitrogen_alternative INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE site ADD COLUMN higher_pressure INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE site ADD COLUMN elected_on TEXT;
    """,
)

M007 = Migration(
    number=7,
    name="the exceedance clocks a bad wellhead reading starts",
    script="""
    CREATE TABLE exceedance (
      label       TEXT PRIMARY KEY,
      site        TEXT NOT NULL REFERENCES site(label),
      device      TEXT NOT NULL REFERENCES device(label),
      kind        TEXT NOT NULL,
      opened_on   TEXT NOT NULL,
      reading     INTEGER NOT NULL REFERENCES reading(id),
      value       REAL NOT NULL,
      limit_value REAL NOT NULL,
      stage       TEXT NOT NULL,
      closed_on   TEXT,
      note        TEXT NOT NULL DEFAULT ''
    );

    CREATE TABLE recheck (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      exceedance  TEXT NOT NULL REFERENCES exceedance(label),
      taken_on    TEXT NOT NULL,
      reading     INTEGER REFERENCES reading(id),
      value       REAL NOT NULL,
      clear       INTEGER NOT NULL,
      stage       TEXT NOT NULL,
      note        TEXT NOT NULL DEFAULT ''
    );

    CREATE INDEX exceedance_by_site ON exceedance(site);
    CREATE INDEX exceedance_by_device ON exceedance(device);
    CREATE INDEX exceedance_by_stage ON exceedance(stage);
    CREATE INDEX exceedance_by_reading ON exceedance(reading);
    CREATE INDEX recheck_by_exceedance ON recheck(exceedance);
    CREATE INDEX recheck_by_reading ON recheck(reading);
    """,
)

M008 = Migration(
    number=8,
    name="the quarterly walkover of the cover and what it found",
    script="""
    CREATE TABLE walk (
      label       TEXT PRIMARY KEY,
      site        TEXT NOT NULL REFERENCES site(label),
      quarter     TEXT NOT NULL,
      started_on  TEXT NOT NULL,
      finished_on TEXT,
      monitor     TEXT NOT NULL,
      instrument  TEXT NOT NULL,
      background  REAL NOT NULL,
      wind_mean   REAL NOT NULL,
      wind_gust   REAL NOT NULL,
      spacing     REAL NOT NULL,
      note        TEXT NOT NULL DEFAULT ''
    );

    CREATE TABLE hit (
      label         TEXT PRIMARY KEY,
      walk          TEXT NOT NULL REFERENCES walk(label),
      site          TEXT NOT NULL REFERENCES site(label),
      area          TEXT NOT NULL REFERENCES area(label),
      station       TEXT NOT NULL,
      reading       REAL NOT NULL,
      cover         TEXT NOT NULL,
      found_on      TEXT NOT NULL,
      stage         TEXT NOT NULL,
      attempt       INTEGER NOT NULL DEFAULT 1,
      repaired_on   TEXT,
      remonitor_on  TEXT,
      closed_on     TEXT,
      note          TEXT NOT NULL DEFAULT ''
    );

    CREATE INDEX walk_by_site ON walk(site);
    CREATE INDEX walk_by_quarter ON walk(quarter);
    CREATE INDEX hit_by_walk ON hit(walk);
    CREATE INDEX hit_by_site ON hit(site);
    CREATE INDEX hit_by_area ON hit(area);
    CREATE INDEX hit_by_stage ON hit(stage);
    """,
)

M009 = Migration(
    number=9,
    name="the blower station and the devices that burn what it pulls",
    script="""
    CREATE TABLE control (
      label        TEXT PRIMARY KEY,
      site         TEXT NOT NULL REFERENCES site(label),
      name         TEXT NOT NULL,
      kind         TEXT NOT NULL,
      capacity     REAL NOT NULL,
      minimum_temp REAL,
      installed_on TEXT NOT NULL,
      retired_on   TEXT
    );

    CREATE TABLE operation (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      control     TEXT NOT NULL REFERENCES control(label),
      at          TEXT NOT NULL,
      running     INTEGER NOT NULL,
      flow        REAL NOT NULL,
      methane     REAL NOT NULL,
      temperature REAL,
      note        TEXT NOT NULL DEFAULT '',
      UNIQUE (control, at)
    );

    CREATE TABLE outage (
      label      TEXT PRIMARY KEY,
      control    TEXT NOT NULL REFERENCES control(label),
      site       TEXT NOT NULL REFERENCES site(label),
      started_at TEXT NOT NULL,
      ended_at   TEXT,
      reason     TEXT NOT NULL,
      planned    INTEGER NOT NULL DEFAULT 0,
      note       TEXT NOT NULL DEFAULT ''
    );

    CREATE INDEX control_by_site ON control(site);
    CREATE INDEX operation_by_control ON operation(control);
    CREATE INDEX operation_by_at ON operation(at);
    CREATE INDEX outage_by_control ON outage(control);
    CREATE INDEX outage_by_site ON outage(site);
    """,
)

M010 = Migration(
    number=10,
    name="liquid levels, sumps and what gets pumped out of them",
    script="""
    CREATE TABLE sump (
      label        TEXT PRIMARY KEY,
      site         TEXT NOT NULL REFERENCES site(label),
      station      TEXT NOT NULL,
      kind         TEXT NOT NULL,
      capacity     REAL NOT NULL,
      installed_on TEXT NOT NULL,
      retired_on   TEXT
    );

    CREATE TABLE level (
      id           INTEGER PRIMARY KEY AUTOINCREMENT,
      device       TEXT NOT NULL REFERENCES device(label),
      taken_on     TEXT NOT NULL,
      depth        REAL NOT NULL,
      pumped       INTEGER NOT NULL DEFAULT 0,
      note         TEXT NOT NULL DEFAULT '',
      UNIQUE (device, taken_on)
    );

    CREATE TABLE pumpout (
      id        INTEGER PRIMARY KEY AUTOINCREMENT,
      sump      TEXT NOT NULL REFERENCES sump(label),
      at        TEXT NOT NULL,
      gallons   REAL NOT NULL,
      hauler    TEXT NOT NULL,
      bound_for TEXT NOT NULL,
      note      TEXT NOT NULL DEFAULT ''
    );

    CREATE INDEX sump_by_site ON sump(site);
    CREATE INDEX level_by_device ON level(device);
    CREATE INDEX level_by_day ON level(taken_on);
    CREATE INDEX pumpout_by_sump ON pumpout(sump);
    CREATE INDEX pumpout_by_at ON pumpout(at);
    """,
)

M011 = Migration(
    number=11,
    name="the work orders the field crew is handed",
    script="""
    CREATE TABLE work_order (
      label     TEXT PRIMARY KEY,
      site      TEXT NOT NULL REFERENCES site(label),
      kind      TEXT NOT NULL,
      target    TEXT NOT NULL,
      because   TEXT,
      raised_on TEXT NOT NULL,
      due_on    TEXT NOT NULL,
      state     TEXT NOT NULL,
      crew      TEXT NOT NULL DEFAULT '',
      done_on   TEXT,
      note      TEXT NOT NULL DEFAULT ''
    );

    CREATE INDEX work_order_by_site ON work_order(site);
    CREATE INDEX work_order_by_state ON work_order(state);
    CREATE INDEX work_order_by_target ON work_order(target);
    CREATE INDEX work_order_by_because ON work_order(because);
    """,
)

M012 = Migration(
    number=12,
    name="the instruments and the calibrations behind every reading",
    script="""
    CREATE TABLE instrument (
      label        TEXT PRIMARY KEY,
      site         TEXT NOT NULL REFERENCES site(label),
      kind         TEXT NOT NULL,
      maker        TEXT NOT NULL,
      model        TEXT NOT NULL,
      serial       TEXT NOT NULL,
      in_service   TEXT NOT NULL,
      retired_on   TEXT
    );

    CREATE TABLE calibration (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      instrument  TEXT NOT NULL REFERENCES instrument(label),
      at          TEXT NOT NULL,
      standard    TEXT NOT NULL,
      expected    REAL NOT NULL,
      before      REAL NOT NULL,
      after       REAL NOT NULL,
      by_whom     TEXT NOT NULL,
      note        TEXT NOT NULL DEFAULT ''
    );

    CREATE INDEX instrument_by_site ON instrument(site);
    CREATE INDEX calibration_by_instrument ON calibration(instrument);
    CREATE INDEX calibration_by_at ON calibration(at);
    """,
)

MIGRATIONS: tuple[Migration, ...] = (
    M001,
    M002,
    M003,
    M004,
    M005,
    M006,
    M007,
    M008,
    M009,
    M010,
    M011,
    M012,
)


def _applied(book: Book) -> set[int]:
    book.script(LOG_TABLE)
    return {int(row["number"]) for row in book.all("SELECT number FROM schema_log")}


def pending(book: Book) -> list[Migration]:
    """The migrations this book has not run yet, in order."""
    done = _applied(book)
    return [m for m in MIGRATIONS if m.number not in done]


def version(book: Book) -> int:
    """The highest migration number this book has run, or zero."""
    done = _applied(book)
    return max(done) if done else 0


def migrate(book: Book, *, at: dt.datetime | None = None) -> list[Migration]:
    """Bring the book up to the current schema and say what was run."""
    if book.closed:
        raise StateError("the book", "closed", "open")
    stamp = (at or dt.datetime.now(tz=dt.UTC)).isoformat(timespec="seconds")
    ran: list[Migration] = []
    for migration in pending(book):
        with book.writing():
            book.script(migration.script)
            book.execute(
                "INSERT INTO schema_log (number, name, ran_at) VALUES (?, ?, ?)",
                (migration.number, migration.name, stamp),
            )
        ran.append(migration)
    return ran


def numbers_are_contiguous() -> bool:
    """True when the migration numbers run one, two, three with no gaps."""
    return [m.number for m in MIGRATIONS] == list(range(1, len(MIGRATIONS) + 1))


__all__ = [
    "LOG_TABLE",
    "MIGRATIONS",
    "Migration",
    "migrate",
    "numbers_are_contiguous",
    "pending",
    "version",
]

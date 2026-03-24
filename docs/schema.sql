-- The schema as sqlite holds it at migration 16.
-- Written by gemwalk.tools.schema_dump. Do not edit: add a migration.

CREATE TABLE area (
      label        TEXT PRIMARY KEY,
      site         TEXT NOT NULL REFERENCES site(label),
      name         TEXT NOT NULL,
      acres        REAL NOT NULL,
      first_waste  TEXT NOT NULL,
      last_waste   TEXT,
      closed_on    TEXT,
      cover        TEXT NOT NULL
    , target_radius REAL NOT NULL DEFAULT 100.0);

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

CREATE TABLE covered (
      id      INTEGER PRIMARY KEY AUTOINCREMENT,
      walk    TEXT NOT NULL REFERENCES walk(label),
      leg     TEXT NOT NULL REFERENCES leg(label),
      note    TEXT NOT NULL DEFAULT '',
      UNIQUE (walk, leg)
    );

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
    , lateral TEXT REFERENCES lateral(label), influence REAL NOT NULL DEFAULT 100.0);

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

CREATE TABLE label_run (
      kind   TEXT NOT NULL,
      scope  TEXT NOT NULL,
      last   INTEGER NOT NULL,
      PRIMARY KEY (kind, scope)
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

CREATE TABLE leg (
      label      TEXT PRIMARY KEY,
      site       TEXT NOT NULL REFERENCES site(label),
      area       TEXT NOT NULL REFERENCES area(label),
      name       TEXT NOT NULL,
      metres     REAL NOT NULL,
      retired_on TEXT
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

CREATE TABLE observation (
      label      TEXT PRIMARY KEY,
      control    TEXT NOT NULL REFERENCES control(label),
      site       TEXT NOT NULL REFERENCES site(label),
      started_at TEXT NOT NULL,
      watched    REAL NOT NULL,
      visible    REAL NOT NULL,
      observer   TEXT NOT NULL,
      note       TEXT NOT NULL DEFAULT ''
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

CREATE TABLE pumpout (
      id        INTEGER PRIMARY KEY AUTOINCREMENT,
      sump      TEXT NOT NULL REFERENCES sump(label),
      at        TEXT NOT NULL,
      gallons   REAL NOT NULL,
      hauler    TEXT NOT NULL,
      bound_for TEXT NOT NULL,
      note      TEXT NOT NULL DEFAULT ''
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

CREATE TABLE rework (
      label         TEXT PRIMARY KEY,
      device        TEXT NOT NULL REFERENCES device(label),
      site          TEXT NOT NULL REFERENCES site(label),
      kind          TEXT NOT NULL,
      started_on    TEXT NOT NULL,
      finished_on   TEXT,
      before_depth  REAL NOT NULL,
      before_top    REAL NOT NULL,
      before_bottom REAL NOT NULL,
      after_depth   REAL,
      after_top     REAL,
      after_bottom  REAL,
      note          TEXT NOT NULL DEFAULT ''
    );

CREATE TABLE run (
      label      TEXT PRIMARY KEY,
      site       TEXT NOT NULL REFERENCES site(label),
      started_on TEXT NOT NULL,
      closed_on  TEXT,
      monitor    TEXT NOT NULL,
      meter      TEXT NOT NULL,
      note       TEXT NOT NULL DEFAULT ''
    );

CREATE TABLE schema_log (
  number   INTEGER PRIMARY KEY,
  name     TEXT NOT NULL,
  ran_at   TEXT NOT NULL
);

CREATE TABLE site (
      label            TEXT PRIMARY KEY,
      name             TEXT NOT NULL,
      standard         TEXT NOT NULL,
      permit           TEXT NOT NULL,
      zone             TEXT NOT NULL,
      design_capacity  REAL NOT NULL,
      opened_on        TEXT NOT NULL,
      closed_on        TEXT
    , nitrogen_alternative INTEGER NOT NULL DEFAULT 0, higher_pressure INTEGER NOT NULL DEFAULT 0, elected_on TEXT);

CREATE TABLE sump (
      label        TEXT PRIMARY KEY,
      site         TEXT NOT NULL REFERENCES site(label),
      station      TEXT NOT NULL,
      kind         TEXT NOT NULL,
      capacity     REAL NOT NULL,
      installed_on TEXT NOT NULL,
      retired_on   TEXT
    );

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

CREATE INDEX area_by_site ON area(site);

CREATE INDEX calibration_by_at ON calibration(at);

CREATE INDEX calibration_by_instrument ON calibration(instrument);

CREATE INDEX control_by_site ON control(site);

CREATE INDEX covered_by_leg ON covered(leg);

CREATE INDEX covered_by_walk ON covered(walk);

CREATE INDEX device_by_area ON device(area);

CREATE INDEX device_by_lateral ON device(lateral);

CREATE INDEX device_by_site ON device(site);

CREATE INDEX device_by_state ON device(state);

CREATE INDEX exceedance_by_device ON exceedance(device);

CREATE INDEX exceedance_by_reading ON exceedance(reading);

CREATE INDEX exceedance_by_site ON exceedance(site);

CREATE INDEX exceedance_by_stage ON exceedance(stage);

CREATE INDEX header_by_site ON header(site);

CREATE INDEX hit_by_area ON hit(area);

CREATE INDEX hit_by_site ON hit(site);

CREATE INDEX hit_by_stage ON hit(stage);

CREATE INDEX hit_by_walk ON hit(walk);

CREATE INDEX instrument_by_site ON instrument(site);

CREATE INDEX lateral_by_header ON lateral(header);

CREATE INDEX lateral_by_site ON lateral(site);

CREATE INDEX leg_by_area ON leg(area);

CREATE INDEX leg_by_site ON leg(site);

CREATE INDEX level_by_day ON level(taken_on);

CREATE INDEX level_by_device ON level(device);

CREATE INDEX observation_by_at ON observation(started_at);

CREATE INDEX observation_by_control ON observation(control);

CREATE INDEX observation_by_site ON observation(site);

CREATE INDEX operation_by_at ON operation(at);

CREATE INDEX operation_by_control ON operation(control);

CREATE INDEX outage_by_control ON outage(control);

CREATE INDEX outage_by_site ON outage(site);

CREATE INDEX pumpout_by_at ON pumpout(at);

CREATE INDEX pumpout_by_sump ON pumpout(sump);

CREATE INDEX reading_by_day ON reading(taken_on);

CREATE INDEX reading_by_device ON reading(device);

CREATE INDEX reading_by_run ON reading(run);

CREATE INDEX recheck_by_exceedance ON recheck(exceedance);

CREATE INDEX recheck_by_reading ON recheck(reading);

CREATE INDEX rework_by_device ON rework(device);

CREATE INDEX rework_by_site ON rework(site);

CREATE INDEX run_by_site ON run(site);

CREATE INDEX sump_by_site ON sump(site);

CREATE INDEX walk_by_quarter ON walk(quarter);

CREATE INDEX walk_by_site ON walk(site);

CREATE INDEX work_order_by_because ON work_order(because);

CREATE INDEX work_order_by_site ON work_order(site);

CREATE INDEX work_order_by_state ON work_order(state);

CREATE INDEX work_order_by_target ON work_order(target);

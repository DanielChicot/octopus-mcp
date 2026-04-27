-- 001_init: full v1 schema.

CREATE TABLE consumption (
  fuel             TEXT NOT NULL,
  mpan_or_mprn     TEXT NOT NULL,
  serial_number    TEXT NOT NULL,
  interval_start   TEXT NOT NULL,
  interval_end     TEXT NOT NULL,
  consumption_kwh  REAL NOT NULL,
  PRIMARY KEY (fuel, mpan_or_mprn, serial_number, interval_start)
);
CREATE INDEX idx_consumption_range ON consumption (fuel, interval_start);

CREATE TABLE unit_rates (
  tariff_code   TEXT NOT NULL,
  fuel          TEXT NOT NULL,
  valid_from    TEXT NOT NULL,
  valid_to      TEXT,
  value_inc_vat REAL NOT NULL,
  value_exc_vat REAL NOT NULL,
  PRIMARY KEY (tariff_code, valid_from)
);

CREATE TABLE standing_charges (
  tariff_code   TEXT NOT NULL,
  fuel          TEXT NOT NULL,
  valid_from    TEXT NOT NULL,
  valid_to      TEXT,
  value_inc_vat REAL NOT NULL,
  value_exc_vat REAL NOT NULL,
  PRIMARY KEY (tariff_code, valid_from)
);

CREATE TABLE meters (
  account_number TEXT NOT NULL,
  fuel           TEXT NOT NULL,
  mpan_or_mprn   TEXT NOT NULL,
  serial_number  TEXT NOT NULL,
  is_export      INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (account_number, fuel, mpan_or_mprn, serial_number)
);

CREATE TABLE tariff_assignments (
  account_number TEXT NOT NULL,
  fuel           TEXT NOT NULL,
  product_code   TEXT NOT NULL,
  tariff_code    TEXT NOT NULL,
  valid_from     TEXT NOT NULL,
  valid_to       TEXT,
  PRIMARY KEY (account_number, fuel, valid_from)
);

CREATE TABLE products (
  code         TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  brand        TEXT,
  payload_json TEXT NOT NULL,
  fetched_at   TEXT NOT NULL
);

CREATE TABLE saving_sessions (
  id              TEXT PRIMARY KEY,
  code            TEXT,
  starts_at       TEXT NOT NULL,
  ends_at         TEXT NOT NULL,
  points_awarded  INTEGER,
  kwh_saved       REAL,
  joined          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE octoplus_events (
  id            TEXT PRIMARY KEY,
  event_type    TEXT NOT NULL,
  points        INTEGER,
  occurred_at   TEXT NOT NULL,
  payload_json  TEXT NOT NULL
);

CREATE TABLE sync_state (
  resource        TEXT PRIMARY KEY,
  last_synced_at  TEXT NOT NULL,
  ttl_seconds     INTEGER
);

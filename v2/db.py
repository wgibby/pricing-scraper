"""
SQLite database for v2 pricing data.

Schema:
  - runs: one row per orchestrator invocation
  - results: one row per (site, country, run)
  - plans: one row per plan per result
  - price_changes: append-only log of detected price changes
  - latest_results (view): latest successful result per (site, country)

Database location: data/pricing.db (relative to project root).

Usage:
    python -m v2.db --info    # Show table row counts and recent runs
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "pricing.db"

SCHEMA = """
-- Orchestrator invocations
CREATE TABLE IF NOT EXISTS runs (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,               -- ISO 8601
    countries   TEXT NOT NULL,               -- comma-separated
    site_count  INTEGER NOT NULL DEFAULT 0,
    success     INTEGER NOT NULL DEFAULT 0,
    errors      INTEGER NOT NULL DEFAULT 0,
    mode        TEXT NOT NULL DEFAULT 'sequential',  -- sequential | concurrent
    elapsed_sec REAL
);

-- One row per (site, country, run)
CREATE TABLE IF NOT EXISTS results (
    result_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL REFERENCES runs(run_id),
    site_id         TEXT NOT NULL,
    country         TEXT NOT NULL,
    status          TEXT NOT NULL,            -- success | error
    tier            TEXT,
    confidence      TEXT,
    plan_count      INTEGER NOT NULL DEFAULT 0,
    currency_code   TEXT,
    currency_symbol TEXT,
    url             TEXT,
    error           TEXT,
    elapsed_sec     REAL,
    json_path       TEXT,                    -- path to the JSON result file
    scraped_at      TEXT NOT NULL             -- ISO 8601
);

CREATE INDEX IF NOT EXISTS idx_results_site_country
    ON results(site_id, country);
CREATE INDEX IF NOT EXISTS idx_results_run
    ON results(run_id);

-- One row per pricing plan per result
CREATE TABLE IF NOT EXISTS plans (
    plan_id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id                INTEGER NOT NULL REFERENCES results(result_id),
    site_id                  TEXT NOT NULL,
    country                  TEXT NOT NULL,
    plan_name                TEXT NOT NULL,
    monthly_price            REAL,
    annual_price             REAL,
    annual_monthly_equivalent REAL,
    billing_periods          TEXT,            -- JSON array
    is_free_tier             INTEGER NOT NULL DEFAULT 0,
    is_contact_sales         INTEGER NOT NULL DEFAULT 0,
    target_audience          TEXT,
    key_features             TEXT,            -- JSON array
    notes                    TEXT
);

CREATE INDEX IF NOT EXISTS idx_plans_result
    ON plans(result_id);
CREATE INDEX IF NOT EXISTS idx_plans_site_country
    ON plans(site_id, country);

-- Append-only log of detected price changes
CREATE TABLE IF NOT EXISTS price_changes (
    change_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES runs(run_id),
    site_id     TEXT NOT NULL,
    country     TEXT NOT NULL,
    plan_name   TEXT NOT NULL,
    change_type TEXT NOT NULL,                -- price_changed | plan_added | plan_removed
    field       TEXT,                         -- monthly_price | annual_price | null for add/remove
    old_value   TEXT,
    new_value   TEXT,
    detected_at TEXT NOT NULL                 -- ISO 8601
);

CREATE INDEX IF NOT EXISTS idx_changes_run
    ON price_changes(run_id);

-- View: latest successful result per (site, country)
CREATE VIEW IF NOT EXISTS latest_results AS
SELECT r.*
FROM results r
INNER JOIN (
    SELECT site_id, country, MAX(result_id) AS max_id
    FROM results
    WHERE status = 'success'
    GROUP BY site_id, country
) latest ON r.result_id = latest.max_id;
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open (and initialize if needed) the pricing database."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


def db_info(db_path: Path | None = None) -> dict:
    """Return row counts and recent runs for --info display."""
    conn = get_connection(db_path)
    try:
        info = {}
        for table in ("runs", "results", "plans", "price_changes"):
            row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
            info[table] = row["cnt"]

        # Latest 5 runs
        runs = conn.execute(
            "SELECT run_id, started_at, countries, site_count, success, errors "
            "FROM runs ORDER BY run_id DESC LIMIT 5"
        ).fetchall()
        info["recent_runs"] = [dict(r) for r in runs]

        return info
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="V2 Pricing Database")
    parser.add_argument("--info", action="store_true", help="Show database info")
    args = parser.parse_args()

    if args.info:
        info = db_info()
        print(f"Database: {DB_PATH}")
        print(f"  runs:          {info['runs']:>6}")
        print(f"  results:       {info['results']:>6}")
        print(f"  plans:         {info['plans']:>6}")
        print(f"  price_changes: {info['price_changes']:>6}")

        if info["recent_runs"]:
            print(f"\nRecent runs:")
            for r in info["recent_runs"]:
                print(
                    f"  #{r['run_id']}  {r['started_at']}  "
                    f"countries={r['countries']}  "
                    f"{r['success']}/{r['site_count']} ok  "
                    f"{r['errors']} errors"
                )
        else:
            print("\nNo runs yet.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

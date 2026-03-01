"""
Store orchestrator results into SQLite.

Called after save_results() in the orchestrator pipeline.
"""

import json
from datetime import datetime
from pathlib import Path

from v2.db import get_connection


def store_run(
    results: list[dict],
    json_paths: list[str] | None = None,
    countries: list[str] | None = None,
    mode: str = "sequential",
    elapsed_sec: float | None = None,
    db_path: Path | None = None,
) -> int:
    """
    Insert a complete run (run + results + plans) into SQLite.

    Args:
        results: List of result dicts from the orchestrator.
        json_paths: Corresponding JSON file paths (same order as results).
        countries: List of country codes scraped.
        mode: "sequential" or "concurrent".
        elapsed_sec: Total run elapsed time.
        db_path: Override database path (for testing).

    Returns:
        The run_id of the inserted run.
    """
    conn = get_connection(db_path)
    now = datetime.now().isoformat()

    success = sum(1 for r in results if r.get("status") == "success")
    errors = len(results) - success
    countries_str = ",".join(sorted(set(
        r.get("country", "?") for r in results
    ))) if not countries else ",".join(sorted(countries))

    try:
        # Insert run
        cur = conn.execute(
            "INSERT INTO runs (started_at, countries, site_count, success, errors, mode, elapsed_sec) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (now, countries_str, len(results), success, errors, mode, elapsed_sec),
        )
        run_id = cur.lastrowid

        # Insert results + plans
        path_map = {}
        if json_paths:
            for i, path in enumerate(json_paths):
                if i < len(results):
                    r = results[i]
                    key = (r.get("site_id", ""), r.get("country", ""))
                    path_map[key] = path

        for r in results:
            site_id = r.get("site_id", "unknown")
            country = r.get("country", "unknown")
            jp = path_map.get((site_id, country))

            result_id = _insert_result(conn, run_id, r, jp, now)

            # Insert plans if extraction succeeded
            extraction = r.get("extraction")
            if extraction and r.get("status") == "success":
                _insert_plans(conn, result_id, site_id, country, extraction)

        conn.commit()
        return run_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _insert_result(
    conn, run_id: int, r: dict, json_path: str | None, scraped_at: str
) -> int:
    """Insert a single result row. Returns result_id."""
    extraction = r.get("extraction") or {}
    cur = conn.execute(
        "INSERT INTO results "
        "(run_id, site_id, country, status, tier, confidence, plan_count, "
        " currency_code, currency_symbol, url, error, elapsed_sec, json_path, scraped_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            r.get("site_id", "unknown"),
            r.get("country", "unknown"),
            r.get("status", "error"),
            r.get("tier"),
            r.get("confidence"),
            r.get("plan_count", 0),
            extraction.get("currency_code"),
            extraction.get("currency_symbol"),
            r.get("url"),
            r.get("error"),
            r.get("elapsed_seconds"),
            json_path,
            scraped_at,
        ),
    )
    return cur.lastrowid


def _insert_plans(
    conn, result_id: int, site_id: str, country: str, extraction: dict
) -> None:
    """Insert plan rows for a successful extraction."""
    plans = extraction.get("plans", [])
    for plan in plans:
        billing = plan.get("billing_periods_available", [])
        features = plan.get("key_features", [])

        conn.execute(
            "INSERT INTO plans "
            "(result_id, site_id, country, plan_name, monthly_price, annual_price, "
            " annual_monthly_equivalent, billing_periods, is_free_tier, is_contact_sales, "
            " target_audience, key_features, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                result_id,
                site_id,
                country,
                plan.get("plan_name", "Unknown"),
                plan.get("monthly_price"),
                plan.get("annual_price"),
                plan.get("annual_monthly_equivalent"),
                json.dumps(billing),
                1 if plan.get("is_free_tier") else 0,
                1 if plan.get("is_contact_sales") else 0,
                plan.get("target_audience"),
                json.dumps(features),
                plan.get("notes"),
            ),
        )

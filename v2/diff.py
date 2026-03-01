"""
Price change detection between scraper runs.

Compares plans from a given run against the previous run for each (site, country).
Detects: price changes, plans added, plans removed.

Changes are stored in the price_changes table and printed to console.

Usage:
    python -m v2.diff --last           # most recent run
    python -m v2.diff --run-id 5       # specific run
"""

import sys
from datetime import datetime
from pathlib import Path

from v2.db import get_connection


def detect_changes(run_id: int, db_path: Path | None = None) -> list[dict]:
    """
    Compare plans from run_id against the previous run for each (site, country).

    Returns list of change dicts and inserts them into price_changes.
    """
    conn = get_connection(db_path)
    try:
        # Get all successful results for this run
        current_results = conn.execute(
            "SELECT result_id, site_id, country FROM results "
            "WHERE run_id = ? AND status = 'success'",
            (run_id,),
        ).fetchall()

        if not current_results:
            return []

        changes = []
        now = datetime.now().isoformat()

        for cr in current_results:
            site_id = cr["site_id"]
            country = cr["country"]

            # Find the previous successful result for this (site, country)
            prev = conn.execute(
                "SELECT result_id FROM results "
                "WHERE site_id = ? AND country = ? AND status = 'success' "
                "  AND run_id < ? "
                "ORDER BY run_id DESC LIMIT 1",
                (site_id, country, run_id),
            ).fetchone()

            if not prev:
                continue  # No prior data to compare against

            # Get plans for current and previous
            current_plans = _get_plans_map(conn, cr["result_id"])
            prev_plans = _get_plans_map(conn, prev["result_id"])

            # Detect changes
            all_names = set(current_plans.keys()) | set(prev_plans.keys())

            for name in all_names:
                if name in current_plans and name not in prev_plans:
                    changes.append({
                        "run_id": run_id,
                        "site_id": site_id,
                        "country": country,
                        "plan_name": name,
                        "change_type": "plan_added",
                        "field": None,
                        "old_value": None,
                        "new_value": None,
                        "detected_at": now,
                    })
                elif name not in current_plans and name in prev_plans:
                    changes.append({
                        "run_id": run_id,
                        "site_id": site_id,
                        "country": country,
                        "plan_name": name,
                        "change_type": "plan_removed",
                        "field": None,
                        "old_value": None,
                        "new_value": None,
                        "detected_at": now,
                    })
                else:
                    # Both exist — compare prices
                    cur_p = current_plans[name]
                    prev_p = prev_plans[name]

                    for field in ("monthly_price", "annual_price"):
                        old_val = prev_p.get(field)
                        new_val = cur_p.get(field)
                        if old_val != new_val:
                            changes.append({
                                "run_id": run_id,
                                "site_id": site_id,
                                "country": country,
                                "plan_name": name,
                                "change_type": "price_changed",
                                "field": field,
                                "old_value": str(old_val) if old_val is not None else None,
                                "new_value": str(new_val) if new_val is not None else None,
                                "detected_at": now,
                            })

        # Store changes in database
        if changes:
            for c in changes:
                conn.execute(
                    "INSERT INTO price_changes "
                    "(run_id, site_id, country, plan_name, change_type, field, "
                    " old_value, new_value, detected_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        c["run_id"], c["site_id"], c["country"], c["plan_name"],
                        c["change_type"], c["field"], c["old_value"],
                        c["new_value"], c["detected_at"],
                    ),
                )
            conn.commit()

        return changes
    finally:
        conn.close()


def _get_plans_map(conn, result_id: int) -> dict:
    """Get plans for a result as {plan_name: {field: value}}."""
    rows = conn.execute(
        "SELECT plan_name, monthly_price, annual_price FROM plans WHERE result_id = ?",
        (result_id,),
    ).fetchall()
    return {r["plan_name"]: dict(r) for r in rows}


def print_change_report(changes: list[dict], run_id: int) -> None:
    """Print a human-readable change report."""
    if not changes:
        print(f"Run #{run_id}: No price changes detected.")
        return

    print(f"\nRun #{run_id}: {len(changes)} change(s) detected")
    print(f"{'─' * 80}")

    # Group by (site, country)
    grouped: dict[tuple, list] = {}
    for c in changes:
        key = (c["site_id"], c["country"])
        grouped.setdefault(key, []).append(c)

    for (site_id, country), site_changes in sorted(grouped.items()):
        print(f"\n  {site_id} ({country.upper()}):")
        for c in site_changes:
            if c["change_type"] == "plan_added":
                print(f"    + Plan added: {c['plan_name']}")
            elif c["change_type"] == "plan_removed":
                print(f"    - Plan removed: {c['plan_name']}")
            elif c["change_type"] == "price_changed":
                field_label = c["field"].replace("_", " ")
                print(f"    ~ {c['plan_name']}: {field_label} {c['old_value']} → {c['new_value']}")

    print()


def get_latest_run_id(db_path: Path | None = None) -> int | None:
    """Return the most recent run_id, or None if no runs exist."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT MAX(run_id) AS max_id FROM runs").fetchone()
        return row["max_id"] if row and row["max_id"] is not None else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Price change detection")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--last", action="store_true", help="Analyze most recent run")
    group.add_argument("--run-id", type=int, help="Analyze a specific run")
    args = parser.parse_args()

    if args.last:
        run_id = get_latest_run_id()
        if run_id is None:
            print("No runs in database.")
            sys.exit(1)
    else:
        run_id = args.run_id

    changes = detect_changes(run_id)
    print_change_report(changes, run_id)


if __name__ == "__main__":
    main()

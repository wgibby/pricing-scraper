"""
One-time import of existing results/v2/*.json files into SQLite.

Groups files by timestamp (same timestamp = same orchestrator run),
then inserts each group as a run.

Usage:
    python -m v2.import_history
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from v2.db import get_connection, DB_PATH
from v2.store import store_run

PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / "results" / "v2"

# Filename pattern: {site_id}_{country}_{YYYYMMDD}_{HHMMSS}.json
FILENAME_RE = re.compile(r"^(.+)_([a-z]{2})_(\d{8}_\d{6})\.json$")


def import_history(dry_run: bool = False) -> dict:
    """
    Import all existing JSON result files into SQLite.

    Groups files by timestamp, inserts each group as a separate run.

    Returns:
        Summary dict with counts.
    """
    if not RESULTS_DIR.exists():
        print(f"No results directory: {RESULTS_DIR}")
        return {"files": 0, "runs": 0, "skipped": 0}

    # Group files by timestamp
    groups: dict[str, list[Path]] = defaultdict(list)
    skipped = 0

    for path in sorted(RESULTS_DIR.glob("*.json")):
        m = FILENAME_RE.match(path.name)
        if not m:
            print(f"  Skipping (bad name): {path.name}")
            skipped += 1
            continue
        timestamp = m.group(3)
        groups[timestamp].append(path)

    total_files = sum(len(files) for files in groups.values())
    print(f"Found {total_files} files in {len(groups)} groups (runs)")

    if dry_run:
        for ts, files in sorted(groups.items()):
            print(f"\n  Run {ts}: {len(files)} files")
            for f in files:
                print(f"    {f.name}")
        return {"files": total_files, "runs": len(groups), "skipped": skipped}

    # Import each group as a run
    runs_created = 0
    results_imported = 0

    for ts, files in sorted(groups.items()):
        results = []
        json_paths = []

        for path in files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append(data)
                json_paths.append(str(path))
            except (json.JSONDecodeError, OSError) as e:
                print(f"  Error reading {path.name}: {e}")
                skipped += 1
                continue

        if not results:
            continue

        # Derive countries from the results
        countries = sorted(set(r.get("country", "?") for r in results))

        # Parse timestamp for scraped_at
        try:
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            scraped_at = dt.isoformat()
        except ValueError:
            scraped_at = ts

        # Use store_run but we want to set scraped_at from the file timestamp
        # So we insert directly with a custom connection
        conn = get_connection()
        try:
            success = sum(1 for r in results if r.get("status") == "success")
            errors = len(results) - success

            cur = conn.execute(
                "INSERT INTO runs (started_at, countries, site_count, success, errors, mode) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (scraped_at, ",".join(countries), len(results), success, errors, "import"),
            )
            run_id = cur.lastrowid

            for i, r in enumerate(results):
                site_id = r.get("site_id", "unknown")
                country = r.get("country", "unknown")
                extraction = r.get("extraction") or {}
                jp = json_paths[i] if i < len(json_paths) else None

                cur2 = conn.execute(
                    "INSERT INTO results "
                    "(run_id, site_id, country, status, tier, confidence, plan_count, "
                    " currency_code, currency_symbol, url, error, elapsed_sec, json_path, scraped_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        site_id,
                        country,
                        r.get("status", "error"),
                        r.get("tier"),
                        r.get("confidence"),
                        r.get("plan_count", 0),
                        extraction.get("currency_code"),
                        extraction.get("currency_symbol"),
                        r.get("url"),
                        r.get("error"),
                        r.get("elapsed_seconds"),
                        jp,
                        scraped_at,
                    ),
                )
                result_id = cur2.lastrowid

                # Insert plans
                if extraction and r.get("status") == "success":
                    for plan in extraction.get("plans", []):
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

            conn.commit()
            runs_created += 1
            results_imported += len(results)
            print(f"  Run #{run_id} ({scraped_at}): {len(results)} results, countries={','.join(countries)}")

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    summary = {
        "files": total_files,
        "runs": runs_created,
        "results": results_imported,
        "skipped": skipped,
    }
    print(f"\nImport complete: {runs_created} runs, {results_imported} results imported")
    return summary


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Import historical results into SQLite")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported")
    args = parser.parse_args()

    # Safety check
    if not args.dry_run and DB_PATH.exists():
        from v2.db import db_info
        info = db_info()
        if info["runs"] > 0:
            print(f"Database already has {info['runs']} runs. Re-importing may create duplicates.")
            resp = input("Continue? [y/N] ").strip().lower()
            if resp != "y":
                print("Aborted.")
                sys.exit(0)

    import_history(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

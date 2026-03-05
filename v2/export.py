"""
Export latest pricing data as website-compatible JSON.

Reads from the latest_results view in SQLite and transforms v2 plan data
into the grouped format expected by the StratDesk website.

Output format:
    {
      "success": true,
      "data": [
        {
          "website": "spotify",
          "country": "us",
          "timestamp": "2026-03-03",
          "plans": [
            {"name": "Premium", "duration": "monthly", "price": 10.99, "currency": "$", ...},
            {"name": "Premium", "duration": "yearly", "price": 109.99, "currency": "$", ...}
          ]
        },
        ...
      ]
    }

Usage:
    python -m v2.export --output /path/to/pricing_data_formatted.json
    python -m v2.export --dry-run   # preview to stdout
"""

import json
import re
import sys
from pathlib import Path

from v2.db import get_connection
from v2.registry import load_registry

# Patterns that indicate a free trial in plan notes
TRIAL_PATTERNS = [
    re.compile(r"(\d+[\s-]?(?:day|week|month)s?\s+(?:free\s+)?trial)", re.IGNORECASE),
    re.compile(r"(free\s+for\s+(?:first\s+)?\d+\s+\w+)", re.IGNORECASE),
    re.compile(r"(\$0\s+for\s+(?:first\s+)?\d+\s+\w+)", re.IGNORECASE),
    re.compile(r"(try\s+(?:it\s+)?free\s+for\s+\d+\s+\w+)", re.IGNORECASE),
]


def _extract_trial(notes: str | None) -> str | None:
    """Extract trial info from plan notes."""
    if not notes:
        return None
    for pattern in TRIAL_PATTERNS:
        m = pattern.search(notes)
        if m:
            return m.group(1)
    return None


def _make_plan_entry(
    plan_name: str,
    original_name: str,
    price: float | None,
    duration: str,
    currency_symbol: str,
    features: list[str],
    trial: str | None,
    is_free_tier: bool,
    is_contact_sales: bool,
) -> dict:
    """Build a single plan entry within a (site, country) group."""
    if is_free_tier:
        display_price = 0
    elif is_contact_sales:
        display_price = None
    else:
        display_price = price

    entry = {
        "name": plan_name,
        "duration": duration,
        "price": display_price,
        "currency": currency_symbol or "$",
        "features": features,
        "original_name": original_name,
    }
    if trial:
        entry["trial"] = trial
    return entry


def export_for_website(db_path: Path | None = None) -> dict:
    """
    Export latest successful results as website-compatible JSON.

    Returns dict in the format: {"success": true, "data": [grouped entries]}
    where each entry groups all plans for a (site, country) pair.
    """
    # Load registry to filter out removed sites and get plan name maps
    registry = load_registry()
    active_sites = {s["id"] for s in registry if s.get("status", "active") == "active"}
    name_maps = {s["id"]: s["plan_name_map"] for s in registry if s.get("plan_name_map")}
    blocklists = {
        s["id"]: [n.lower() for n in s["plan_name_blocklist"]]
        for s in registry if s.get("plan_name_blocklist")
    }

    conn = get_connection(db_path)
    try:
        # Get latest results via the view
        results = conn.execute(
            "SELECT result_id, site_id, country, currency_symbol, scraped_at "
            "FROM latest_results ORDER BY site_id, country"
        ).fetchall()

        grouped = []
        normalized_count = 0

        for r in results:
            # Skip sites removed from registry
            if r["site_id"] not in active_sites:
                continue
            timestamp = r["scraped_at"][:10] if r["scraped_at"] else ""
            currency_symbol = r["currency_symbol"] or "$"

            # Get plans for this result
            plans = conn.execute(
                "SELECT plan_name, monthly_price, annual_price, "
                "       is_free_tier, is_contact_sales, key_features, notes "
                "FROM plans WHERE result_id = ?",
                (r["result_id"],),
            ).fetchall()

            plan_entries = []

            site_name_map = name_maps.get(r["site_id"], {})
            site_blocklist = blocklists.get(r["site_id"], [])

            for plan in plans:
                # Skip blocklisted plans (same filter as scrape-time postprocessing)
                if plan["plan_name"].lower() in site_blocklist:
                    continue
                features = []
                if plan["key_features"]:
                    try:
                        features = json.loads(plan["key_features"])
                    except json.JSONDecodeError:
                        features = []

                trial = _extract_trial(plan["notes"])
                is_free = bool(plan["is_free_tier"])
                is_sales = bool(plan["is_contact_sales"])

                raw_name = plan["plan_name"]
                canonical_name = site_name_map.get(raw_name, raw_name)
                if canonical_name != raw_name:
                    normalized_count += 1

                # Monthly entry
                if plan["monthly_price"] is not None or is_free or is_sales:
                    plan_entries.append(_make_plan_entry(
                        plan_name=canonical_name,
                        original_name=raw_name,
                        price=plan["monthly_price"],
                        duration="monthly",
                        currency_symbol=currency_symbol,
                        features=features,
                        trial=trial,
                        is_free_tier=is_free,
                        is_contact_sales=is_sales,
                    ))

                # Yearly entry (only if annual price exists)
                if plan["annual_price"] is not None:
                    plan_entries.append(_make_plan_entry(
                        plan_name=canonical_name,
                        original_name=raw_name,
                        price=plan["annual_price"],
                        duration="yearly",
                        currency_symbol=currency_symbol,
                        features=features,
                        trial=trial,
                        is_free_tier=is_free,
                        is_contact_sales=is_sales,
                    ))

            if plan_entries:
                grouped.append({
                    "website": r["site_id"],
                    "country": r["country"],
                    "timestamp": timestamp,
                    "plans": plan_entries,
                })

        return {"success": True, "data": grouped, "_normalized": normalized_count}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export pricing data for website")
    parser.add_argument(
        "--output", "-o", type=str,
        help="Output file path (e.g., /path/to/pricing_data_formatted.json)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview output to stdout without writing",
    )
    args = parser.parse_args()

    if not args.output and not args.dry_run:
        parser.error("Specify --output or --dry-run")

    result = export_for_website()
    normalized_count = result.pop("_normalized", 0)
    entries_count = len(result["data"])
    plan_count = sum(len(g["plans"]) for g in result["data"])

    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.dry_run:
        print(output_json)
        print(
            f"\n--- {entries_count} (site, country) groups, "
            f"{plan_count} plan entries, "
            f"{normalized_count} names normalized ---",
            file=sys.stderr,
        )
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(
            f"Exported {entries_count} groups ({plan_count} plan entries, "
            f"{normalized_count} names normalized) to {output_path}"
        )


if __name__ == "__main__":
    main()

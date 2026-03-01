"""
Export latest pricing data as website-compatible JSON.

Reads from the latest_results view in SQLite and transforms v2 plan data
into the format expected by the StratDesk website.

Each v2 plan can produce 1-2 website entries (one per billing period).

Usage:
    python -m v2.export --output /path/to/pricing_data_formatted.json
    python -m v2.export --dry-run   # preview to stdout
"""

import json
import re
import sys
from pathlib import Path

from v2.db import get_connection

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


def _make_entry(
    site_id: str,
    country: str,
    timestamp: str,
    plan_name: str,
    price: float | None,
    duration: str,
    currency_symbol: str,
    features: list[str],
    trial: str | None,
    is_free_tier: bool,
    is_contact_sales: bool,
) -> dict:
    """Build a single website entry."""
    # Determine display price
    if is_free_tier:
        display_price = 0
    elif is_contact_sales:
        display_price = None
    else:
        display_price = price

    entry = {
        "website": site_id,
        "country": country,
        "timestamp": timestamp,
        "name": plan_name,
        "price": display_price,
        "duration": duration,
        "currency": currency_symbol or "$",
        "features": features,
        "original_name": plan_name,
    }
    if trial:
        entry["trial"] = trial
    return entry


def export_for_website(db_path: Path | None = None) -> list[dict]:
    """
    Export latest successful results as website-compatible JSON.

    Returns list of website entry dicts.
    """
    conn = get_connection(db_path)
    try:
        # Get latest results via the view
        results = conn.execute(
            "SELECT result_id, site_id, country, currency_symbol, scraped_at "
            "FROM latest_results ORDER BY site_id, country"
        ).fetchall()

        entries = []

        for r in results:
            # Date portion only
            timestamp = r["scraped_at"][:10] if r["scraped_at"] else ""
            currency_symbol = r["currency_symbol"] or "$"

            # Get plans for this result
            plans = conn.execute(
                "SELECT plan_name, monthly_price, annual_price, "
                "       is_free_tier, is_contact_sales, key_features, notes "
                "FROM plans WHERE result_id = ?",
                (r["result_id"],),
            ).fetchall()

            for plan in plans:
                features = []
                if plan["key_features"]:
                    try:
                        features = json.loads(plan["key_features"])
                    except json.JSONDecodeError:
                        features = []

                trial = _extract_trial(plan["notes"])
                is_free = bool(plan["is_free_tier"])
                is_sales = bool(plan["is_contact_sales"])

                # Monthly entry
                if plan["monthly_price"] is not None or is_free or is_sales:
                    entries.append(_make_entry(
                        site_id=r["site_id"],
                        country=r["country"],
                        timestamp=timestamp,
                        plan_name=plan["plan_name"],
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
                    entries.append(_make_entry(
                        site_id=r["site_id"],
                        country=r["country"],
                        timestamp=timestamp,
                        plan_name=plan["plan_name"],
                        price=plan["annual_price"],
                        duration="yearly",
                        currency_symbol=currency_symbol,
                        features=features,
                        trial=trial,
                        is_free_tier=is_free,
                        is_contact_sales=is_sales,
                    ))

        return entries
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

    entries = export_for_website()

    output_json = json.dumps(entries, indent=2, ensure_ascii=False)

    if args.dry_run:
        print(output_json)
        print(f"\n--- {len(entries)} entries ---", file=sys.stderr)
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"Exported {len(entries)} entries to {output_path}")


if __name__ == "__main__":
    main()

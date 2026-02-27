"""
Tiered extraction cascade for the v2 pricing pipeline.

Single entry point: hand it HTML + a screenshot path, and it tries
progressively more expensive extraction tiers until it gets a good result.

Tier cascade:
  1. JSON-LD        (stub — not implemented)
  2. Cleaned HTML   (live — html_cleaner + llm_client)
  3. OCR            (stub — not wired)
  4. Vision         (live — screenshot + llm_client)

Usage:
    from v2.extractor import extract_with_fallback
    result = extract_with_fallback(html=raw_html, screenshot_path="shot.png",
                                    company="Spotify", country="us")

CLI:
    python -m v2.extractor <html_file> <company> <country> [--screenshot <path>]
    python -m v2.extractor --vision <screenshot.png> <company> <country>
"""

import sys
from dataclasses import dataclass
from pathlib import Path

from v2.html_cleaner import clean_html
from v2.llm_client import extract_pricing, extract_pricing_from_screenshot
from v2.models import Confidence, PricingExtraction


@dataclass
class ExtractionResult:
    tier: str  # "tier_1", "tier_2", "tier_3", "tier_4", "none"
    extraction: PricingExtraction
    company: str
    country: str


def extract_with_fallback(
    *,
    html: str = "",
    screenshot_path: str = "",
    company: str,
    country: str,
) -> ExtractionResult:
    """
    Run the tiered extraction cascade.

    Tries each tier in order; stops at the first one that produces
    a good result (non-empty plans + confidence not low).

    Args:
        html: Raw page HTML (for Tier 2). Empty string to skip.
        screenshot_path: Path to a PNG screenshot (for Tier 4). Empty to skip.
        company: Company name (e.g., "Spotify").
        country: ISO country code (e.g., "us").

    Returns:
        ExtractionResult with the winning tier and extraction data.
    """
    # Tier 1 — JSON-LD (stub)
    _log("Tier 1 (JSON-LD): not implemented, skipping")

    # Tier 2 — Cleaned HTML
    t2 = _try_tier_2(html, company, country)
    if t2 is not None:
        return ExtractionResult(tier="tier_2", extraction=t2, company=company, country=country)

    # Tier 3 — OCR (stub)
    _log("Tier 3 (OCR): not wired, skipping to Tier 4")

    # Tier 4 — Vision
    t4 = _try_tier_4(screenshot_path, company, country)
    if t4 is not None:
        return ExtractionResult(tier="tier_4", extraction=t4, company=company, country=country)

    # Fallthrough — all tiers exhausted
    _log("All tiers exhausted — returning low-confidence error result")
    return ExtractionResult(
        tier="none",
        extraction=PricingExtraction(
            currency_code="UNKNOWN",
            currency_symbol="?",
            plans=[],
            extraction_confidence=Confidence.LOW,
            extraction_notes="All extraction tiers exhausted without result",
        ),
        company=company,
        country=country,
    )


def _try_tier_2(html: str, company: str, country: str) -> PricingExtraction | None:
    """Tier 2: Clean HTML and extract via LLM. Returns None to fall through."""
    if not html or not html.strip():
        _log("Tier 2 (HTML): no HTML provided, skipping")
        return None

    _log("Tier 2 (HTML): cleaning HTML...")
    cleaned = clean_html(html)
    _log(f"Tier 2 (HTML): cleaned to {len(cleaned):,} chars")

    if not cleaned.strip():
        _log("Tier 2 (HTML): cleaned HTML is empty, falling through")
        return None

    _log("Tier 2 (HTML): calling LLM...")
    result = extract_pricing(cleaned, company, country, input_type="html")

    if _is_good(result):
        _log(f"Tier 2 (HTML): RESOLVED — confidence={result.extraction_confidence.value}, plans={len(result.plans)}")
        return result

    _log(
        f"Tier 2 (HTML): quality gate failed — "
        f"confidence={result.extraction_confidence.value}, plans={len(result.plans)}, "
        f"falling through"
    )
    return None


def _try_tier_4(screenshot_path: str, company: str, country: str) -> PricingExtraction | None:
    """Tier 4: Vision extraction from screenshot. Returns result regardless of quality (last resort)."""
    if not screenshot_path:
        _log("Tier 4 (Vision): no screenshot path provided, skipping")
        return None

    path = Path(screenshot_path)
    if not path.exists():
        _log(f"Tier 4 (Vision): screenshot not found at {screenshot_path}, skipping")
        return None

    _log(f"Tier 4 (Vision): extracting from {path.name}...")
    result = extract_pricing_from_screenshot(str(path), company, country)
    _log(f"Tier 4 (Vision): RESOLVED — confidence={result.extraction_confidence.value}, plans={len(result.plans)}")
    return result


def _is_good(result: PricingExtraction) -> bool:
    """
    Quality gate: does this extraction resolve the tier?

    Resolves if:
    - extraction_confidence is NOT low
    - plans list is NOT empty
    - at least one plan has meaningful price data (a numeric price,
      is_free_tier=True, or is_contact_sales=True)
    """
    if result.extraction_confidence == Confidence.LOW:
        return False
    if not result.plans:
        return False

    # Check that at least one plan has meaningful price data.
    # A plan has price data if it has a numeric price, is a free tier,
    # or is a contact-sales tier.
    # Additionally, if there are "paid" plans (not free, not contact-sales),
    # at least one of them must have an actual numeric price. This catches
    # cases like Canva where the HTML has plan names but dollar amounts
    # are rendered by client-side JS — the Free and Enterprise plans pass
    # individually, but the paid plans (Pro, Business) have no prices.
    def _plan_has_price(plan) -> bool:
        return (
            plan.monthly_price is not None
            or plan.annual_price is not None
            or plan.annual_monthly_equivalent is not None
            or plan.is_free_tier is True
            or plan.is_contact_sales is True
        )

    if not any(_plan_has_price(p) for p in result.plans):
        _log("quality gate: no plans have price data, falling through")
        return False

    # Stricter check: if there are paid plans (not free, not contact-sales),
    # at least one must have a numeric price.
    paid_plans = [
        p for p in result.plans
        if not p.is_free_tier and not p.is_contact_sales
    ]
    if paid_plans:
        has_numeric_price = any(
            p.monthly_price is not None
            or p.annual_price is not None
            or p.annual_monthly_equivalent is not None
            for p in paid_plans
        )
        if not has_numeric_price:
            _log("quality gate: no plans have price data, falling through")
            return False

    return True


def _log(msg: str) -> None:
    """Log cascade progress to stderr."""
    print(f"[extractor] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _print_result(result: ExtractionResult) -> None:
    """Pretty-print an ExtractionResult."""
    ext = result.extraction
    print(f"{'='*60}")
    print(f"  EXTRACTION RESULT — {result.company} ({result.country.upper()})")
    print(f"{'='*60}")
    print(f"  Resolved at: {result.tier}")
    print(f"  Confidence:  {ext.extraction_confidence.value}")
    print(f"  Currency:    {ext.currency_symbol} ({ext.currency_code})")
    print(f"  Plans:       {len(ext.plans)}")
    if ext.extraction_notes:
        print(f"  Notes:       {ext.extraction_notes}")
    print()

    for i, plan in enumerate(ext.plans, 1):
        print(f"  Plan {i}: {plan.plan_name}")
        if plan.is_free_tier:
            print(f"    Price:    FREE")
        elif plan.is_contact_sales:
            print(f"    Price:    Contact Sales")
        else:
            if plan.monthly_price is not None:
                print(f"    Monthly:  {ext.currency_symbol}{plan.monthly_price}")
            if plan.annual_price is not None:
                print(f"    Annual:   {ext.currency_symbol}{plan.annual_price}")
            if plan.annual_monthly_equivalent is not None:
                print(f"    Annual/mo:{ext.currency_symbol}{plan.annual_monthly_equivalent}")
        print(f"    Billing:  {', '.join(b.value for b in plan.billing_periods_available)}")
        print(f"    Audience: {plan.target_audience.value}")
        if plan.key_features:
            print(f"    Features: {', '.join(plan.key_features[:5])}")
        if plan.notes:
            print(f"    Notes:    {plan.notes}")
        print()

    print(f"{'='*60}")
    print("  FULL JSON OUTPUT")
    print(f"{'='*60}")
    print(ext.model_dump_json(indent=2))


def main():
    """
    CLI for testing the extraction cascade.

    Usage:
        # Tier 2 from saved HTML dump
        python -m v2.extractor screenshots/html/grammarly_us_20250601_083349.html Grammarly us

        # Tier 4 vision (force with --vision)
        python -m v2.extractor --vision screenshots/spotify_us_20260226_163408.png Spotify us

        # Cascade: try HTML first, fall back to vision if quality gate fails
        python -m v2.extractor screenshots/html/spotify_us_20260226_163408.html Spotify us \\
            --screenshot screenshots/spotify_us_20260226_163408.png
    """
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print("Usage:")
        print("  python -m v2.extractor <html_file> <company> <country> [--screenshot <path>]")
        print("  python -m v2.extractor --vision <screenshot.png> <company> <country>")
        sys.exit(0)

    # Parse --vision mode (skip straight to Tier 4)
    if args[0] == "--vision":
        if len(args) < 4:
            print("Usage: python -m v2.extractor --vision <screenshot.png> <company> <country>")
            sys.exit(1)
        screenshot_path = args[1]
        company = args[2]
        country = args[3]
        result = extract_with_fallback(
            screenshot_path=screenshot_path, company=company, country=country
        )
        _print_result(result)
        return

    # Standard mode: HTML file + optional --screenshot
    if len(args) < 3:
        print("Usage: python -m v2.extractor <html_file> <company> <country> [--screenshot <path>]")
        sys.exit(1)

    html_file = args[0]
    company = args[1]
    country = args[2]

    # Parse optional --screenshot
    screenshot_path = ""
    remaining = args[3:]
    if "--screenshot" in remaining:
        idx = remaining.index("--screenshot")
        if idx + 1 < len(remaining):
            screenshot_path = remaining[idx + 1]

    # Read HTML
    html = ""
    html_path = Path(html_file)
    if html_path.exists() and html_path.stat().st_size > 0:
        with open(html_path, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()

    result = extract_with_fallback(
        html=html,
        screenshot_path=screenshot_path,
        company=company,
        country=country,
    )
    _print_result(result)


if __name__ == "__main__":
    main()

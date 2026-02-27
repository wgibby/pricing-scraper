"""
Test harness: compare old site handlers vs v2 extraction pipeline.

Runs both systems on the same live page and scores v2 against the old handler
output. Single browser per site — old handler extracts first (read-only JS eval),
then HTML + screenshot are captured from the same page state for v2.

Usage:
    python -m v2.test_extraction --sites grammarly spotify audible --country us
    python -m v2.test_extraction --all --country us
"""

import argparse
import json
import os
import re
import sys
import time
import random
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright

from v2.capture_html import CHROMIUM_ARGS, USER_AGENT, STEALTH_JS, SITES as CAPTURE_SITES
from v2.extractor import ExtractionResult, extract_with_fallback
from v2.models import Confidence

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Sites that must use Firefox (bot detection blocks Chromium)
FIREFOX_SITES = {"netflix", "adobe", "canva", "box"}

# Sites with old handlers available for comparison
# Maps test key → handler name used by site_handlers.get_handler()
HANDLER_SITES = {
    "grammarly": "grammarly",
    "spotify": "spotify",
    "audible": "audible",
    "netflix": "netflix",
    "canva": "canva",
    "disney_plus": "disney_plus",
    "youtube": "youtube",
    "peacock": "peacock",
    "evernote": "evernote",
    "dropbox": "dropbox",
    "notion": "notion",
    "figma": "figma",
    "adobe": "adobe",
    "box": "box",
    "chatgpt_plus": "chatgpt_plus",
    "zwift": "zwift",
}

# Company display names for v2 extractor
COMPANY_NAMES = {
    "grammarly": "Grammarly",
    "spotify": "Spotify",
    "audible": "Audible",
    "netflix": "Netflix",
    "canva": "Canva",
    "disney_plus": "Disney+",
    "youtube": "YouTube",
    "peacock": "Peacock",
    "evernote": "Evernote",
    "dropbox": "Dropbox",
    "notion": "Notion",
    "figma": "Figma",
    "adobe": "Adobe",
    "box": "Box",
    "chatgpt_plus": "ChatGPT Plus",
    "zwift": "Zwift",
}

# Screenshot output dir
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots" / "test"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class NormalizedPlan:
    name: str
    monthly_price: Optional[float]  # None for free/contact-sales
    currency_symbol: str
    is_free: bool
    is_contact_sales: bool
    features: list[str] = field(default_factory=list)


@dataclass
class NormalizedResult:
    site: str
    plan_count: int
    currency_symbol: str
    plans: list[NormalizedPlan]
    raw_data: dict | None = None
    error: str | None = None


@dataclass
class PlanPair:
    old_plan: NormalizedPlan
    new_plan: NormalizedPlan
    name_score: float  # 0.0 – 1.0


@dataclass
class SiteScore:
    site: str
    scores: dict[str, float]  # category → points earned
    total: float
    plan_pairs: list[PlanPair]


# ---------------------------------------------------------------------------
# Normalization: old handler output → NormalizedResult
# ---------------------------------------------------------------------------

def normalize_old_result(result: dict, site_name: str) -> NormalizedResult:
    """Convert old handler output dict to NormalizedResult."""
    if not result:
        return NormalizedResult(site=site_name, plan_count=0, currency_symbol="?",
                                plans=[], error="No result returned")

    if "error" in result and not result.get("plans") and not result.get("tiers"):
        return NormalizedResult(site=site_name, plan_count=0, currency_symbol="?",
                                plans=[], raw_data=result, error=result["error"])

    plans: list[NormalizedPlan] = []
    currency = "?"

    # Format A: {plans: [{name, price: {display, numeric, currency}, features}]}
    if "plans" in result and isinstance(result["plans"], list):
        for p in result["plans"]:
            if not isinstance(p, dict):
                continue
            name = p.get("name", "Unknown")
            price_obj = p.get("price", {})
            numeric = None
            sym = "?"
            is_free = False
            is_contact = False

            if isinstance(price_obj, dict):
                numeric = price_obj.get("numeric")
                sym = price_obj.get("currency") or "?"
                display = price_obj.get("display", "") or ""
                if numeric == 0 or "free" in display.lower():
                    is_free = True
                    numeric = None
                if "contact" in display.lower():
                    is_contact = True
                    numeric = None
            elif isinstance(price_obj, (int, float)):
                numeric = float(price_obj)
                if numeric == 0:
                    is_free = True
                    numeric = None

            if sym != "?":
                currency = sym

            features = p.get("features", [])
            if not isinstance(features, list):
                features = []
            plans.append(NormalizedPlan(
                name=name, monthly_price=numeric, currency_symbol=sym,
                is_free=is_free, is_contact_sales=is_contact, features=features,
            ))

    # Format B: {tiers: [{name, price, price_text, features}], currency}
    elif "tiers" in result and isinstance(result["tiers"], list):
        currency = result.get("currency", "?")
        # Map currency code to symbol
        currency_sym = _currency_code_to_symbol(currency)
        for t in result["tiers"]:
            if not isinstance(t, dict):
                continue
            name = t.get("name", "Unknown")
            price = t.get("price")
            price_text = t.get("price_text", "")
            is_free = False
            is_contact = False
            numeric = None

            if isinstance(price, (int, float)) and price > 0:
                numeric = float(price)
            elif price_text:
                # Try to extract numeric from price_text
                m = re.search(r'[\d]+\.?\d*', price_text)
                if m:
                    numeric = float(m.group())
            if price == 0 or "free" in str(price_text).lower():
                is_free = True
            if "contact" in str(price_text).lower():
                is_contact = True

            features = t.get("features", [])
            if not isinstance(features, list):
                features = []
            plans.append(NormalizedPlan(
                name=name, monthly_price=numeric, currency_symbol=currency_sym,
                is_free=is_free, is_contact_sales=is_contact, features=features,
            ))

    return NormalizedResult(
        site=site_name,
        plan_count=len(plans),
        currency_symbol=currency,
        plans=plans,
        raw_data=result,
    )


def _currency_code_to_symbol(code: str) -> str:
    """Map common currency codes to symbols."""
    mapping = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
        "INR": "₹", "BRL": "R$", "CAD": "C$", "AUD": "A$",
    }
    return mapping.get(code.upper(), code)


# ---------------------------------------------------------------------------
# Normalization: v2 ExtractionResult → NormalizedResult
# ---------------------------------------------------------------------------

def normalize_v2_result(result: ExtractionResult) -> NormalizedResult:
    """Convert v2 ExtractionResult to NormalizedResult."""
    ext = result.extraction
    plans: list[NormalizedPlan] = []

    for p in ext.plans:
        plans.append(NormalizedPlan(
            name=p.plan_name,
            monthly_price=p.monthly_price,
            currency_symbol=ext.currency_symbol,
            is_free=p.is_free_tier,
            is_contact_sales=p.is_contact_sales,
            features=p.key_features,
        ))

    return NormalizedResult(
        site=result.company,
        plan_count=len(plans),
        currency_symbol=ext.currency_symbol,
        plans=plans,
    )


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _fuzzy_match(a: str, b: str) -> float:
    """Word-overlap similarity between two strings. Returns 0.0–1.0."""
    if not a or not b:
        return 0.0
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _normalize_currency(sym: str | None) -> str:
    """Normalize currency symbol for comparison."""
    if not sym:
        return "?"
    sym = sym.strip()
    # Common equivalences
    mapping = {
        "US$": "$", "USD": "$", "A$": "$", "C$": "$",
        "EUR": "€", "GBP": "£", "JPY": "¥", "INR": "₹",
        "BRL": "R$",
    }
    return mapping.get(sym, sym)


def _pair_plans(old_plans: list[NormalizedPlan],
                new_plans: list[NormalizedPlan]) -> list[PlanPair]:
    """
    Pair old plans to new plans by best fuzzy name match.
    Each plan can only be paired once. Threshold: 0.3.
    """
    if not old_plans or not new_plans:
        return []

    # Build similarity matrix
    used_new = set()
    pairs: list[PlanPair] = []

    for old_p in old_plans:
        best_score = 0.0
        best_idx = -1
        for i, new_p in enumerate(new_plans):
            if i in used_new:
                continue
            score = _fuzzy_match(old_p.name, new_p.name)
            if score > best_score:
                best_score = score
                best_idx = i
        if best_idx >= 0 and best_score >= 0.3:
            used_new.add(best_idx)
            pairs.append(PlanPair(
                old_plan=old_p, new_plan=new_plans[best_idx],
                name_score=best_score,
            ))

    return pairs


def score_comparison(old: NormalizedResult, new: NormalizedResult) -> SiteScore:
    """
    Score v2 result against old handler result on a 100-point scale.

    Categories:
        Plan count: 20 pts — exact match = 20, off by 1 = 10, else 0
        Plan names: 20 pts — average fuzzy match of paired plans
        Prices:     40 pts — exact numeric match per paired plan (5% tolerance = half)
        Currency:   10 pts — normalized symbol comparison
        Features:   10 pts — credit if v2 found features where old did
    """
    scores: dict[str, float] = {}
    pairs = _pair_plans(old.plans, new.plans)

    # --- Plan count (20 pts) ---
    diff = abs(old.plan_count - new.plan_count)
    if diff == 0:
        scores["plan_count"] = 20.0
    elif diff == 1:
        scores["plan_count"] = 10.0
    else:
        scores["plan_count"] = 0.0

    # --- Plan names (20 pts) ---
    if pairs:
        avg_name = sum(p.name_score for p in pairs) / len(pairs)
        scores["plan_names"] = round(avg_name * 20, 1)
    else:
        scores["plan_names"] = 0.0

    # --- Prices (40 pts) ---
    if pairs:
        price_points_per_pair = 40.0 / len(pairs)
        total_price = 0.0
        for pair in pairs:
            op = pair.old_plan.monthly_price
            np_ = pair.new_plan.monthly_price
            # Both free or both contact-sales
            if pair.old_plan.is_free and pair.new_plan.is_free:
                total_price += price_points_per_pair
            elif pair.old_plan.is_contact_sales and pair.new_plan.is_contact_sales:
                total_price += price_points_per_pair
            elif op is not None and np_ is not None:
                if abs(op - np_) < 0.01:
                    total_price += price_points_per_pair
                elif op > 0 and abs(op - np_) / op <= 0.05:
                    total_price += price_points_per_pair * 0.5
                # else 0
            # If one is None and the other isn't, 0 points
        scores["prices"] = round(total_price, 1)
    else:
        scores["prices"] = 0.0

    # --- Currency (10 pts) ---
    old_cur = _normalize_currency(old.currency_symbol)
    new_cur = _normalize_currency(new.currency_symbol)
    scores["currency"] = 10.0 if old_cur == new_cur else 0.0

    # --- Features (10 pts) ---
    if pairs:
        feat_points_per_pair = 10.0 / len(pairs)
        total_feat = 0.0
        for pair in pairs:
            old_has = len(pair.old_plan.features) > 0
            new_has = len(pair.new_plan.features) > 0
            if not old_has:
                # Old had no features — give full credit (can't penalize v2 for finding more)
                total_feat += feat_points_per_pair
            elif new_has:
                # Both have features — credit
                total_feat += feat_points_per_pair
            # else old had features, v2 didn't — 0
        scores["features"] = round(total_feat, 1)
    else:
        scores["features"] = 0.0

    total = round(sum(scores.values()), 1)
    return SiteScore(site=old.site, scores=scores, total=total, plan_pairs=pairs)


# ---------------------------------------------------------------------------
# Browser + extraction runner
# ---------------------------------------------------------------------------

def run_site_test(
    site_key: str,
    country: str,
    pw,
    v2_only: bool = False,
) -> tuple[NormalizedResult | None, NormalizedResult | None, dict]:
    """
    Run old handler + v2 pipeline on a live page.

    When v2_only=True, skips all old handler code (no get_handler, no
    prepare_context, no cookie_consent, no site_interactions, no
    extract_pricing_data).  Gets URL and browser type from CAPTURE_SITES.

    Returns:
        (old_normalized, v2_normalized, metadata_dict)
    """
    # --- Determine browser type ---
    if v2_only and site_key in CAPTURE_SITES:
        browser_type = CAPTURE_SITES[site_key].get("browser", "chromium")
    else:
        browser_type = "firefox" if site_key in FIREFOX_SITES else "chromium"

    metadata: dict = {
        "site": site_key,
        "country": country,
        "timestamp": datetime.now().isoformat(),
        "old_handler_found": False,
        "old_error": "N/A (v2-only mode)" if v2_only else None,
        "v2_error": None,
        "v2_tier": None,
        "v2_confidence": None,
        "screenshot_path": None,
        "browser": browser_type,
        "v2_only": v2_only,
    }

    # --- Get old handler (skip in v2-only mode) ---
    handler = None
    if not v2_only:
        try:
            from site_handlers import get_handler
            handler = get_handler(HANDLER_SITES.get(site_key, site_key))
        except Exception as e:
            _log(f"Could not load handler for {site_key}: {e}")

        if handler:
            metadata["old_handler_found"] = True

    # --- Determine URL ---
    url = None
    if handler and not v2_only:
        try:
            url = handler.get_url(country)
        except Exception:
            pass

    # Fallback (or primary in v2-only mode) to capture_html config
    if not url and site_key in CAPTURE_SITES:
        url = CAPTURE_SITES[site_key]["url"]

    if not url:
        return (None, None, {**metadata, "old_error": metadata["old_error"] or "No URL", "v2_error": "No URL"})

    _log(f"URL: {url}")
    _log(f"Browser: {metadata['browser']}")
    if v2_only:
        _log("Mode: v2-only (old handler bypassed)")

    # --- Launch browser ---
    use_firefox = browser_type == "firefox"
    browser = None
    try:
        if use_firefox:
            browser = pw.firefox.launch(
                headless=True,
                args=["--width=1920", "--height=1080"],
                timeout=60000,
            )
        else:
            browser = pw.chromium.launch(
                headless=True,
                args=CHROMIUM_ARGS,
                timeout=60000,
            )
    except Exception as e:
        err = f"Browser launch failed: {e}"
        _log(err)
        return (None, None, {**metadata, "old_error": metadata["old_error"] or err, "v2_error": err})

    old_norm = None
    v2_norm = None

    try:
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=USER_AGENT,
            java_script_enabled=True,
            bypass_csp=True,
        )

        # Stealth JS for Chromium only
        if not use_firefox:
            context.add_init_script(STEALTH_JS)

        # Let old handler prepare context if available (skip in v2-only)
        if handler and not v2_only:
            try:
                handler.prepare_context(context, country)
            except Exception as e:
                _log(f"prepare_context failed: {e}")

        page = context.new_page()

        # Navigate — try networkidle, fall back to domcontentloaded
        _log("Navigating...")
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            _log("networkidle timed out, retrying with domcontentloaded...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)  # extra wait for JS rendering
        page.wait_for_timeout(int(random.uniform(1.5, 3.0) * 1000))

        # Cookie consent (skip old handler version in v2-only, use generic)
        if handler and not v2_only:
            try:
                handler.handle_cookie_consent(page)
            except Exception as e:
                _log(f"handle_cookie_consent failed: {e}")
        elif v2_only:
            # Use generic cookie dismissal from capture_html
            from v2.capture_html import try_dismiss_cookies
            try:
                try_dismiss_cookies(page)
            except Exception as e:
                _log(f"Generic cookie dismiss failed: {e}")
        page.wait_for_timeout(1000)

        # Site interactions (skip entirely in v2-only)
        if handler and not v2_only:
            try:
                handler.perform_site_interactions(page)
            except Exception as e:
                _log(f"perform_site_interactions failed: {e}")
            page.wait_for_timeout(1000)
        elif v2_only:
            # Gentle scroll to trigger lazy content (same as capture_html)
            try:
                page.evaluate("window.scrollBy(0, 300)")
                page.wait_for_timeout(1000)
                page.evaluate("window.scrollBy(0, 500)")
                page.wait_for_timeout(1500)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(500)
            except Exception as e:
                _log(f"Scroll failed: {e}")

        # === CAPTURE PHASE (same page state for both systems) ===

        # 1) Old handler extraction (skip in v2-only mode)
        if v2_only:
            _log("Skipping old handler (v2-only mode)")
        elif handler:
            try:
                _log("Running old handler extract_pricing_data()...")
                old_result = handler.extract_pricing_data(page)
                old_norm = normalize_old_result(old_result, site_key)
                _log(f"Old handler: {old_norm.plan_count} plans")
            except Exception as e:
                metadata["old_error"] = str(e)
                _log(f"Old handler extraction failed: {e}")
        else:
            metadata["old_error"] = "No handler"

        # 2) Capture HTML for v2
        try:
            raw_html = page.content()
        except Exception as e:
            raw_html = ""
            _log(f"page.content() failed: {e}")

        # 3) Capture screenshot for v2
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = str(SCREENSHOT_DIR / f"{site_key}_{country}_{ts}.png")
        try:
            page.screenshot(path=screenshot_path, full_page=True)
            metadata["screenshot_path"] = screenshot_path
        except Exception as e:
            screenshot_path = ""
            _log(f"Screenshot failed: {e}")

        # Close browser before v2 LLM call (free resources)
        try:
            browser.close()
        except Exception:
            pass
        browser = None

        # 4) v2 extraction
        company = COMPANY_NAMES.get(site_key, site_key.replace("_", " ").title())
        try:
            _log("Running v2 extraction cascade...")
            v2_result = extract_with_fallback(
                html=raw_html,
                screenshot_path=screenshot_path,
                company=company,
                country=country,
            )
            v2_norm = normalize_v2_result(v2_result)
            metadata["v2_tier"] = v2_result.tier
            metadata["v2_confidence"] = v2_result.extraction.extraction_confidence.value
            _log(f"v2: tier={v2_result.tier}, confidence={v2_result.extraction.extraction_confidence.value}, plans={v2_norm.plan_count}")
        except Exception as e:
            metadata["v2_error"] = str(e)
            _log(f"v2 extraction failed: {e}")
            traceback.print_exc(file=sys.stderr)

    except Exception as e:
        err = f"Test run error: {e}"
        _log(err)
        traceback.print_exc(file=sys.stderr)
        if not metadata.get("old_error"):
            metadata["old_error"] = err
        if not metadata.get("v2_error"):
            metadata["v2_error"] = err
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    return (old_norm, v2_norm, metadata)


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_site_result(
    site_key: str,
    old: NormalizedResult | None,
    v2: NormalizedResult | None,
    score: SiteScore | None,
    metadata: dict,
) -> None:
    """Print formatted comparison for a single site."""
    w = 70
    print(f"\n{'='*w}")
    print(f"  {site_key.upper()} ({metadata.get('country', '?').upper()})")
    print(f"{'='*w}")

    # Metadata line
    parts = []
    parts.append(f"browser={metadata.get('browser', '?')}")
    if metadata.get("v2_tier"):
        parts.append(f"v2_tier={metadata['v2_tier']}")
    if metadata.get("v2_confidence"):
        parts.append(f"v2_conf={metadata['v2_confidence']}")
    print(f"  {' | '.join(parts)}")

    # Errors
    if metadata.get("old_error"):
        print(f"  OLD ERROR: {metadata['old_error']}")
    if metadata.get("v2_error"):
        print(f"  V2 ERROR: {metadata['v2_error']}")

    is_v2_only = metadata.get("v2_only", False)

    if not old and not v2:
        print(f"  Both systems failed — nothing to compare.")
        return

    if is_v2_only:
        # V2-only mode: show only v2 results
        if not v2:
            print(f"  V2 extraction failed — no results.")
            return

        print(f"\n  {'OLD HANDLER':<34} {'V2 PIPELINE':<34}")
        print(f"  {'-'*34} {'-'*34}")

        for np_ in v2.plans:
            old_str = "N/A (v2-only mode)"
            if np_.is_free:
                new_str = f"{np_.name}: FREE"
            elif np_.is_contact_sales:
                new_str = f"{np_.name}: Contact"
            elif np_.monthly_price is not None:
                new_str = f"{np_.name}: {np_.currency_symbol}{np_.monthly_price}"
            else:
                new_str = f"{np_.name}: ?"
            print(f"  {old_str:<34} {new_str:<34}")

        v2_cur = v2.currency_symbol if v2 else "?"
        print(f"\n  Currency: {'N/A':<23} Currency: {v2_cur}")
        print(f"  Plans: {'N/A':<25} Plans: {v2.plan_count}")
        print(f"\n  SCORE: N/A (v2-only mode, no old handler baseline)")
        print(f"{'='*w}")
        return

    # --- Normal (comparison) mode below ---

    # Side-by-side plan table
    print(f"\n  {'OLD HANDLER':<34} {'V2 PIPELINE':<34}")
    print(f"  {'-'*34} {'-'*34}")

    old_plans = old.plans if old else []
    v2_plans = v2.plans if v2 else []
    max_rows = max(len(old_plans), len(v2_plans))

    for i in range(max_rows):
        # Old column
        if i < len(old_plans):
            op = old_plans[i]
            if op.is_free:
                old_str = f"{op.name}: FREE"
            elif op.is_contact_sales:
                old_str = f"{op.name}: Contact"
            elif op.monthly_price is not None:
                old_str = f"{op.name}: {op.currency_symbol}{op.monthly_price}"
            else:
                old_str = f"{op.name}: ?"
        else:
            old_str = ""

        # V2 column
        if i < len(v2_plans):
            np_ = v2_plans[i]
            if np_.is_free:
                new_str = f"{np_.name}: FREE"
            elif np_.is_contact_sales:
                new_str = f"{np_.name}: Contact"
            elif np_.monthly_price is not None:
                new_str = f"{np_.name}: {np_.currency_symbol}{np_.monthly_price}"
            else:
                new_str = f"{np_.name}: ?"
        else:
            new_str = ""

        print(f"  {old_str:<34} {new_str:<34}")

    # Currency row
    old_cur = old.currency_symbol if old else "?"
    v2_cur = v2.currency_symbol if v2 else "?"
    print(f"\n  Currency: {old_cur:<23} Currency: {v2_cur}")
    if old:
        print(f"  Plans: {old.plan_count:<25} Plans: {v2.plan_count if v2 else 0}")

    # Score breakdown
    if score:
        print(f"\n  SCORE: {score.total}/100")
        print(f"  {'─'*40}")
        for cat, pts in score.scores.items():
            max_pts = {"plan_count": 20, "plan_names": 20, "prices": 40,
                       "currency": 10, "features": 10}[cat]
            bar_len = int(pts / max_pts * 15) if max_pts > 0 else 0
            bar = "█" * bar_len + "░" * (15 - bar_len)
            print(f"  {cat:<14} {bar} {pts:>5.1f}/{max_pts}")

        # Paired plan details
        if score.plan_pairs:
            print(f"\n  PLAN PAIRS:")
            for pair in score.plan_pairs:
                name_match = f"name={pair.name_score:.0%}"
                op = pair.old_plan.monthly_price
                np_ = pair.new_plan.monthly_price
                if op is not None and np_ is not None:
                    price_match = "EXACT" if abs(op - np_) < 0.01 else f"old={op} vs new={np_}"
                elif pair.old_plan.is_free and pair.new_plan.is_free:
                    price_match = "both FREE"
                elif pair.old_plan.is_contact_sales and pair.new_plan.is_contact_sales:
                    price_match = "both Contact"
                else:
                    price_match = f"old={'FREE' if pair.old_plan.is_free else op} vs new={'FREE' if pair.new_plan.is_free else np_}"
                print(f"    {pair.old_plan.name} <-> {pair.new_plan.name}  ({name_match}, {price_match})")

    print(f"{'='*w}")


def print_summary(results: list[tuple[str, SiteScore | None, dict]]) -> None:
    """Print final summary table across all sites."""
    w = 70
    print(f"\n{'='*w}")
    print(f"  SUMMARY")
    print(f"{'='*w}")
    print(f"  {'Site':<18} {'Score':>7} {'Plans':>7} {'Tier':>8} {'Conf':>8}")
    print(f"  {'─'*18} {'─'*7} {'─'*7} {'─'*8} {'─'*8}")

    scored = []
    any_v2_only = any(meta.get("v2_only") for _, _, meta in results)

    for site_key, score, meta in results:
        is_v2_only = meta.get("v2_only", False)
        if is_v2_only:
            s = "  N/A"
        else:
            s = f"{score.total:>5.1f}" if score else "  N/A"
        plans_str = f"{meta.get('v2_plans', '?')}"
        tier = meta.get("v2_tier", "?") or "?"
        conf = meta.get("v2_confidence", "?") or "?"
        print(f"  {site_key:<18} {s:>7} {plans_str:>7} {tier:>8} {conf:>8}")
        if score and not is_v2_only:
            scored.append(score.total)

    if scored:
        avg = sum(scored) / len(scored)
        print(f"\n  Average score: {avg:.1f}/100 across {len(scored)} sites")
    elif any_v2_only:
        print(f"\n  Scores: N/A (v2-only mode, no old handler baseline)")

    print(f"{'='*w}")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    print(f"[test] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compare old site handlers vs v2 extraction pipeline",
    )
    parser.add_argument(
        "--sites", nargs="+", default=[],
        help="Site keys to test (e.g., grammarly spotify audible)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Test all sites with old handlers",
    )
    parser.add_argument(
        "--country", default="us",
        help="Country code (default: us)",
    )
    parser.add_argument(
        "--v2-only", action="store_true",
        help="Skip old handlers entirely; run v2 extraction pipeline only",
    )
    args = parser.parse_args()

    if args.all:
        sites = sorted(HANDLER_SITES.keys())
    elif args.sites:
        sites = [s.lower() for s in args.sites]
    else:
        parser.print_help()
        sys.exit(1)

    v2_only = getattr(args, "v2_only", False)

    print(f"Testing {len(sites)} sites: {', '.join(sites)}")
    print(f"Country: {args.country}")
    if v2_only:
        print(f"Mode: v2-only (old handlers bypassed)")
    print(f"Screenshots: {SCREENSHOT_DIR}")

    summary: list[tuple[str, SiteScore | None, dict]] = []

    with sync_playwright() as pw:
        for i, site_key in enumerate(sites, 1):
            print(f"\n{'#'*70}")
            print(f"  [{i}/{len(sites)}] {site_key.upper()}")
            print(f"{'#'*70}")

            old_norm, v2_norm, metadata = run_site_test(site_key, args.country, pw, v2_only=v2_only)

            # Score if we have both results (skip scoring in v2-only mode)
            score = None
            if v2_only:
                if v2_norm:
                    _log(f"v2 produced {v2_norm.plan_count} plans (v2-only mode, no scoring)")
                else:
                    _log(f"v2 produced no results")
            elif old_norm and v2_norm:
                score = score_comparison(old_norm, v2_norm)
            elif v2_norm and not old_norm:
                _log(f"v2 produced {v2_norm.plan_count} plans but no old handler result to compare")

            # Track v2 plan count in metadata for summary
            metadata["v2_plans"] = v2_norm.plan_count if v2_norm else 0

            print_site_result(site_key, old_norm, v2_norm, score, metadata)
            summary.append((site_key, score, metadata))

            # Small delay between sites
            if i < len(sites):
                delay = random.uniform(2.0, 4.0)
                _log(f"Waiting {delay:.1f}s before next site...")
                time.sleep(delay)

    print_summary(summary)


if __name__ == "__main__":
    main()

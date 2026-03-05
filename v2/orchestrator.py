"""
V2 Orchestrator — main entry point for the pricing scraper pipeline.

Reads site configs from the company registry, resolves URLs, manages
browser lifecycle, and feeds pages into the v2 extraction cascade.
No per-site handler code needed — all sites use the same generic pipeline.

Supports both sequential and concurrent processing modes.

Usage:
    python -m v2.orchestrator --sites spotify netflix --countries us uk de
    python -m v2.orchestrator --all --countries us
    python -m v2.orchestrator --all --all-countries
    python -m v2.orchestrator --all --countries us uk de --concurrent --max-workers 2
"""

import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from v2.browser import (
    launch_browser,
    create_context,
    dismiss_cookies,
    stabilize_page,
    capture_page,
)
from v2.extractor import ExtractionResult, extract_with_fallback, is_usable
from v2.interactions import pre_navigation_setup, run_interaction
from v2.registry import get_sites, resolve_url, get_proxy_config, get_all_countries

# Thread-safe logging
_log_lock = threading.Lock()


def _log(msg: str, site_id: str = "", country: str = "") -> None:
    """Thread-safe log to stderr."""
    prefix = ""
    if site_id and country:
        prefix = f"[{site_id}/{country.upper()}] "
    elif site_id:
        prefix = f"[{site_id}] "
    with _log_lock:
        print(f"[orchestrator] {prefix}{msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Retryable vs. structural error classification
# ---------------------------------------------------------------------------

# Transient failures — browser crashes, proxy hiccups, timeouts
RETRYABLE_PATTERNS = [
    "target page, context or browser has been closed",
    "browser has been closed",
    "net::err_tunnel_connection_failed",
    "net::err_connection_reset",
    "net::err_connection_timed_out",
    "net::err_proxy_connection_failed",
    "ns_error_abort",
    "ns_binding_aborted",
    "timeout",
    "connection refused",
]

# Structural failures — site-level issues that will never succeed on retry
STRUCTURAL_PATTERNS = [
    "interrupted by another navigation to",
]

# Default retry settings
DEFAULT_MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 3


def _is_retryable_error(error_str: str) -> bool:
    """Check if an error is transient and worth retrying."""
    error_lower = error_str.lower()
    for pattern in STRUCTURAL_PATTERNS:
        if pattern in error_lower:
            return False
    for pattern in RETRYABLE_PATTERNS:
        if pattern in error_lower:
            return True
    # Unknown errors: don't retry
    return False


# ---------------------------------------------------------------------------
# Post-processing: fill missing price fields + filter blocklisted plans
# ---------------------------------------------------------------------------

def _postprocess_extraction(result_dict: dict, site_config: dict) -> dict:
    """
    Post-process extraction results to fix common LLM gaps:
    1. Compute annual_price from annual_monthly_equivalent (and vice versa).
    2. Remove plans matching the site's plan_name_blocklist.

    Modifies result_dict["extraction"] in place and returns result_dict.
    """
    extraction = result_dict.get("extraction")
    if not extraction or not extraction.get("plans"):
        return result_dict

    plans = extraction["plans"]
    blocklist = [n.lower() for n in site_config.get("plan_name_blocklist", [])]

    # Filter blocklisted plans
    if blocklist:
        before = len(plans)
        plans = [
            p for p in plans
            if p.get("plan_name", "").lower() not in blocklist
        ]
        removed = before - len(plans)
        if removed:
            _log(
                f"Filtered {removed} blocklisted plan(s)",
                site_config["id"],
                result_dict.get("country", ""),
            )
        extraction["plans"] = plans

    # Fill missing price fields from annual_monthly_equivalent
    for plan in plans:
        ame = plan.get("annual_monthly_equivalent")
        annual = plan.get("annual_price")
        monthly = plan.get("monthly_price")

        # If annual_monthly_equivalent is set but annual_price is null: compute it
        if ame is not None and annual is None:
            plan["annual_price"] = round(ame * 12, 2)

        # If annual_price is set but annual_monthly_equivalent is null: compute it
        if plan.get("annual_price") is not None and ame is None:
            plan["annual_monthly_equivalent"] = round(plan["annual_price"] / 12, 2)

    # Rescue prices mentioned in notes but missing from price fields.
    # The LLM sometimes acknowledges a price in notes but fails to fill the field.
    # Pattern: "$X/month shown for monthly billing" or similar in notes.
    import re
    _NOTES_MONTHLY_RE = re.compile(
        r'[\£\$\€\¥\₹]?\s*([\d,]+(?:\.\d+)?)\s*/\s*(?:month|mo)\b'
        r'(?!.*(?:billed annually|billed yearly|per year))',
        re.IGNORECASE,
    )
    for plan in plans:
        notes = plan.get("notes") or ""
        if plan.get("monthly_price") is None and not plan.get("is_free_tier") and not plan.get("is_contact_sales"):
            m = _NOTES_MONTHLY_RE.search(notes)
            if m:
                try:
                    price = float(m.group(1).replace(",", ""))
                    plan["monthly_price"] = price
                    _log(
                        f"Rescued monthly_price={price} from notes for {plan.get('plan_name', '?')}",
                        site_config["id"],
                        result_dict.get("country", ""),
                    )
                except ValueError:
                    pass

    # Update plan_count in case blocklist removed some
    result_dict["plan_count"] = len(plans)

    return result_dict


# ---------------------------------------------------------------------------
# Extraction quality validation
# ---------------------------------------------------------------------------

def _describe_quality_failure(extraction) -> str:
    """Return a descriptive error string for an extraction that failed the quality gate."""
    if not extraction.plans:
        return "No pricing plans found"

    # Check if any plan has a numeric price
    has_numeric = any(
        p.monthly_price is not None
        or p.annual_price is not None
        or p.annual_monthly_equivalent is not None
        for p in extraction.plans
    )
    if not has_numeric:
        # Plans exist but no actual prices (only free/contact-sales, or empty)
        has_free_or_contact = any(
            p.is_free_tier or p.is_contact_sales for p in extraction.plans
        )
        if has_free_or_contact:
            return "Plans found but no numeric prices extracted (only free/contact-sales tiers)"
        return "Plans found but no numeric prices extracted"

    if extraction.extraction_confidence.value == "low":
        notes = extraction.extraction_notes or "no details"
        return f"Low confidence extraction: {notes}"

    return "Extraction failed quality gate"


# ---------------------------------------------------------------------------
# Single (site, country) scrape pipeline
# ---------------------------------------------------------------------------

def scrape_one(
    site_config: dict, country: str, max_retries: int = DEFAULT_MAX_RETRIES
) -> dict:
    """
    Run the full pipeline for a single (site, country) pair.

    Automatically retries transient failures (browser crashes, proxy hiccups,
    timeouts) up to max_retries times. Structural failures (e.g. site redirects
    to a different domain) fail immediately without retry.

    Args:
        site_config: Site config dict from the registry.
        country: ISO alpha-2 country code.
        max_retries: Max retry attempts for transient errors (default 2).

    Returns:
        Result dict with extraction data and metadata.
    """
    site_id = site_config["id"]
    display_name = site_config["display_name"]
    start_time = time.time()
    attempts = 0

    result = {
        "site_id": site_id,
        "display_name": display_name,
        "country": country,
        "url": "",
        "status": "error",
        "tier": "none",
        "confidence": "low",
        "plan_count": 0,
        "error": None,
        "extraction": None,
        "screenshot_path": "",
        "elapsed_seconds": 0,
        "attempts": 1,
        "retryable": None,
    }

    while attempts <= max_retries:
        attempts += 1
        try:
            # 1. Resolve URL
            url = resolve_url(site_config, country)
            result["url"] = url
            if attempts == 1:
                _log(f"URL: {url}", site_id, country)

            # 2. Get proxy
            proxy_url = get_proxy_config(site_config, country)
            if attempts == 1:
                if proxy_url:
                    _log(f"Using proxy for {country.upper()}", site_id, country)
                else:
                    _log(f"No proxy (US or unavailable)", site_id, country)

            # 3-9. Browser lifecycle
            html, screenshot_path = _browser_phase(site_config, country, url, proxy_url)
            result["screenshot_path"] = screenshot_path

            # 10. Extraction
            _log("Running extraction cascade...", site_id, country)
            extraction_result: ExtractionResult = extract_with_fallback(
                html=html,
                screenshot_path=screenshot_path,
                company=display_name,
                country=country,
            )

            result["tier"] = extraction_result.tier
            result["confidence"] = extraction_result.extraction.extraction_confidence.value
            result["plan_count"] = len(extraction_result.extraction.plans)
            result["extraction"] = extraction_result.extraction.model_dump()
            result["attempts"] = attempts
            result["retryable"] = None

            # Post-process: fill missing price fields, filter blocklisted plans
            _postprocess_extraction(result, site_config)

            if is_usable(extraction_result.extraction):
                result["status"] = "success"
                result["error"] = None
            else:
                result["status"] = "error"
                result["error"] = _describe_quality_failure(extraction_result.extraction)
                _log(f"Quality gate failed: {result['error']}", site_id, country)

            break  # Exit retry loop (quality failures are not retryable)

        except Exception as e:
            error_str = str(e)
            retryable = _is_retryable_error(error_str)
            result["error"] = error_str
            result["retryable"] = retryable
            result["attempts"] = attempts

            if retryable and attempts <= max_retries:
                _log(
                    f"TRANSIENT ERROR (attempt {attempts}/{max_retries + 1}): "
                    f"{error_str} — retrying in {RETRY_DELAY_SECONDS}s...",
                    site_id, country,
                )
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            elif not retryable:
                _log(f"STRUCTURAL ERROR: {error_str}", site_id, country)
                break  # Don't waste time retrying
            else:
                _log(
                    f"TRANSIENT ERROR (attempt {attempts}/{max_retries + 1}): "
                    f"{error_str} — no retries left",
                    site_id, country,
                )
                break

    result["elapsed_seconds"] = round(time.time() - start_time, 1)
    attempt_info = f" (attempt {attempts})" if attempts > 1 else ""
    _log(
        f"Done: {result['status']} | tier={result['tier']} | "
        f"confidence={result['confidence']} | plans={result['plan_count']} | "
        f"{result['elapsed_seconds']}s{attempt_info}",
        site_id, country,
    )
    return result


def _browser_phase(
    site_config: dict, country: str, url: str, proxy_url: str | None
) -> tuple[str, str]:
    """
    Browser lifecycle: launch → navigate → interact → capture → close.

    Returns (html, screenshot_path). Browser is closed before return.
    """
    site_id = site_config["id"]

    with sync_playwright() as pw:
        # 3. Launch browser
        _log("Launching browser...", site_id, country)
        browser = launch_browser(pw, site_config, proxy_url)

        try:
            # 4. Create context with stealth
            context = create_context(browser, site_config, country)

            # 5. Pre-navigation setup (cookie injection)
            pre_navigation_setup(context, site_config, country)

            page = context.new_page()

            # 6. Navigate
            _log("Navigating...", site_id, country)
            wait_until = site_config.get("navigation_wait_until", "networkidle")
            try:
                page.goto(url, wait_until=wait_until, timeout=45000)
            except Exception:
                _log(f"{wait_until} timeout, retrying with domcontentloaded", site_id, country)
                page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # 7. Dismiss cookies
            dismiss_cookies(page)
            page.wait_for_timeout(1000)

            # 8. Run post-navigation interaction
            if site_config.get("requires_interaction"):
                _log(f"Running interaction: {site_config['interaction_type']}", site_id, country)
                run_interaction(page, site_config, country)

            # 9. Stabilize page
            extra_wait = site_config.get("stabilization_wait_ms", 0)
            stabilize_page(page, extra_wait_ms=extra_wait)

            # 10. Capture HTML + screenshot
            _log("Capturing page...", site_id, country)
            html, screenshot_path = capture_page(page, site_id, country)
            _log(f"HTML: {len(html):,} chars | Screenshot: {screenshot_path}", site_id, country)

            return html, screenshot_path

        finally:
            # Close browser (free resources before LLM call)
            browser.close()


# ---------------------------------------------------------------------------
# Batch scrape (sequential + concurrent)
# ---------------------------------------------------------------------------

def run_scrape(
    sites: list[dict],
    countries: list[str],
    concurrent: bool = False,
    max_workers: int = 3,
) -> list[dict]:
    """
    Run the scrape pipeline for all (site, country) pairs.

    Args:
        sites: List of site config dicts.
        countries: List of ISO country codes.
        concurrent: If True, use ThreadPoolExecutor.
        max_workers: Max parallel workers for concurrent mode.

    Returns:
        List of result dicts.
    """
    # Build (site, country) pairs, filtering to countries the site supports
    pairs = []
    for site in sites:
        supported = set(site["countries"])
        for country in countries:
            if country.lower() in supported:
                pairs.append((site, country.lower()))
            else:
                _log(
                    f"Skipping {country.upper()} (not in site's country list)",
                    site["id"],
                )

    total = len(pairs)
    _log(f"Starting scrape: {total} (site, country) pairs")

    if concurrent and total > 1:
        return _run_concurrent(pairs, max_workers, total)
    else:
        return _run_sequential(pairs, total)


def _run_sequential(pairs: list[tuple[dict, str]], total: int) -> list[dict]:
    """Run scrapes sequentially."""
    results = []
    for i, (site, country) in enumerate(pairs, 1):
        _log(f"[{i}/{total}] Starting {site['id']}/{country.upper()}")
        result = scrape_one(site, country)
        results.append(result)
    return results


def _run_concurrent(
    pairs: list[tuple[dict, str]], max_workers: int, total: int
) -> list[dict]:
    """Run scrapes concurrently with ThreadPoolExecutor.

    After the concurrent batch, any failures are retried sequentially
    (fresh browser, no concurrency pressure) to recover from transient
    macOS resource-contention crashes.
    """
    results = []
    completed_count = 0

    _log(f"Concurrent mode: {max_workers} workers")

    # Build lookup so we can find site_config for retries
    pair_lookup = {(site["id"], country): site for site, country in pairs}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pair = {
            executor.submit(scrape_one, site, country): (site["id"], country)
            for site, country in pairs
        }

        for future in as_completed(future_to_pair):
            site_id, country = future_to_pair[future]
            completed_count += 1
            try:
                result = future.result()
                results.append(result)
                _log(f"[{completed_count}/{total}] Completed {site_id}/{country.upper()}")
            except Exception as e:
                _log(f"[{completed_count}/{total}] FAILED {site_id}/{country.upper()}: {e}")
                results.append({
                    "site_id": site_id,
                    "country": country,
                    "status": "error",
                    "error": str(e),
                    "tier": "none",
                    "confidence": "low",
                    "plan_count": 0,
                })

    # --- Sequential retry for retryable failures ---
    # Only retry transient errors; structural failures (e.g. site redirects)
    # already exhausted retries inside scrape_one and won't recover.
    failed_indices = [
        i for i, r in enumerate(results)
        if r.get("status") == "error" and r.get("retryable") is not False
    ]
    structural_count = sum(
        1 for r in results
        if r.get("status") == "error" and r.get("retryable") is False
    )

    if structural_count:
        _log(f"Skipping {structural_count} structural failure(s) (not retryable)")

    if failed_indices:
        _log(f"Retrying {len(failed_indices)} transient failure(s) sequentially...")
        recovered = 0

        for idx in failed_indices:
            r = results[idx]
            site_id = r["site_id"]
            country = r["country"]
            site_config = pair_lookup.get((site_id, country))

            if site_config is None:
                _log(f"Cannot retry {site_id}/{country.upper()} — config not found")
                continue

            _log(f"Concurrent retry: {site_id}/{country.upper()}", site_id, country)
            retry_result = scrape_one(site_config, country)
            retry_result["retried"] = True

            if retry_result.get("status") == "success":
                recovered += 1
                _log(f"Recovered: {site_id}/{country.upper()}", site_id, country)
            else:
                _log(f"Still failed: {site_id}/{country.upper()}", site_id, country)

            results[idx] = retry_result

        _log(
            f"Retry complete: {recovered}/{len(failed_indices)} recovered"
        )

    return results


# ---------------------------------------------------------------------------
# Result saving + summary
# ---------------------------------------------------------------------------

def save_results(results: list[dict]) -> list[str]:
    """
    Save each result as a JSON file in results/v2/.

    Returns list of saved file paths.
    """
    project_root = Path(__file__).parent.parent
    results_dir = project_root / "results" / "v2"
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = []

    for result in results:
        site_id = result.get("site_id", "unknown")
        country = result.get("country", "unknown")
        filename = f"{site_id}_{country}_{timestamp}.json"
        path = results_dir / filename

        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)

        saved.append(str(path))

    return saved


def print_summary(results: list[dict]) -> None:
    """Print a summary table of all results."""
    print(f"\n{'='*90}")
    print(f"  V2 ORCHESTRATOR RESULTS — {len(results)} extractions")
    print(f"{'='*90}")
    print(
        f"  {'Site':<16} {'Country':<8} {'Status':<8} {'Tier':<8} "
        f"{'Confidence':<12} {'Plans':<6} {'Time':<8}"
    )
    print(f"  {'─'*16} {'─'*8} {'─'*8} {'─'*8} {'─'*12} {'─'*6} {'─'*8}")

    for r in sorted(results, key=lambda x: (x.get("site_id", ""), x.get("country", ""))):
        site_id = r.get("site_id", "?")
        country = r.get("country", "?").upper()
        status = r.get("status", "?")
        tier = r.get("tier", "?")
        confidence = r.get("confidence", "?")
        plans = r.get("plan_count", 0)
        elapsed = r.get("elapsed_seconds", 0)

        status_icon = "ok" if status == "success" else "ERR"
        print(
            f"  {site_id:<16} {country:<8} {status_icon:<8} {tier:<8} "
            f"{confidence:<12} {plans:<6} {elapsed:>6.1f}s"
        )

    # Summary stats
    total = len(results)
    success = sum(1 for r in results if r.get("status") == "success")
    all_errors = [r for r in results if r.get("status") == "error"]

    # Split errors: quality failures (pipeline ran, data unusable) vs crashes (exceptions)
    quality_errors = [r for r in all_errors if r.get("tier", "none") != "none"]
    crashes = [r for r in all_errors if r.get("tier", "none") == "none"]

    tier_counts = {}
    confidence_counts = {}
    for r in results:
        if r.get("status") == "success":
            t = r.get("tier", "unknown")
            tier_counts[t] = tier_counts.get(t, 0) + 1
            c = r.get("confidence", "unknown")
            confidence_counts[c] = confidence_counts.get(c, 0) + 1

    print(f"\n  Summary: {success}/{total} with pricing, {len(all_errors)} without")

    # Quality error breakdown
    if quality_errors:
        # Count by error type
        no_plans = sum(1 for r in quality_errors if "No pricing plans" in (r.get("error") or ""))
        no_prices = sum(1 for r in quality_errors if "no numeric prices" in (r.get("error") or "").lower())
        low_conf = sum(1 for r in quality_errors if "Low confidence" in (r.get("error") or ""))
        other_quality = len(quality_errors) - no_plans - no_prices - low_conf
        parts = []
        if low_conf:
            parts.append(f"{low_conf} low confidence")
        if no_prices:
            parts.append(f"{no_prices} no prices")
        if no_plans:
            parts.append(f"{no_plans} no plans")
        if other_quality:
            parts.append(f"{other_quality} other")
        print(f"  Quality errors: {', '.join(parts)}")

    print(f"  Crashes: {len(crashes)}")

    # Retry stats
    multi_attempt = [r for r in results if r.get("attempts", 1) > 1]
    if multi_attempt:
        recovered_inline = sum(1 for r in multi_attempt if r.get("status") == "success")
        print(f"  Inline retries: {len(multi_attempt)} needed, {recovered_inline} recovered")
    retried = [r for r in results if r.get("retried")]
    if retried:
        retried_recovered = sum(1 for r in retried if r.get("status") == "success")
        print(f"  Concurrent retries: {len(retried)} attempted, {retried_recovered} recovered")

    # Structural vs transient breakdown for crashes
    if crashes:
        structural = sum(1 for r in crashes if r.get("retryable") is False)
        transient = len(crashes) - structural
        parts = []
        if structural:
            parts.append(f"{structural} structural")
        if transient:
            parts.append(f"{transient} transient (exhausted retries)")
        print(f"  Crash breakdown: {', '.join(parts)}")
    if tier_counts:
        tier_str = ", ".join(f"{k}: {v}" for k, v in sorted(tier_counts.items()))
        print(f"  Tiers: {tier_str}")
    if confidence_counts:
        conf_str = ", ".join(f"{k}: {v}" for k, v in sorted(confidence_counts.items()))
        print(f"  Confidence: {conf_str}")

    total_time = sum(r.get("elapsed_seconds", 0) for r in results)
    print(f"  Total time: {total_time:.1f}s")
    print(f"{'='*90}")


# ---------------------------------------------------------------------------
# Pricing coverage metric
# ---------------------------------------------------------------------------

def _count_pricing_coverage(results: list[dict]) -> tuple[int, int, list[dict]]:
    """
    Count paid plans with at least one price field populated.

    Returns:
        (plans_with_price, total_paid_plans, gaps_list)
        where gaps_list has dicts: {site_id, country, plan_name}
    """
    total_paid = 0
    with_price = 0
    gaps = []

    for r in results:
        if r.get("status") != "success":
            continue
        extraction = r.get("extraction")
        if not extraction:
            continue
        site_id = r.get("site_id", "?")
        country = r.get("country", "?")

        for plan in extraction.get("plans", []):
            if plan.get("is_free_tier") or plan.get("is_contact_sales"):
                continue
            total_paid += 1
            has_price = (
                plan.get("monthly_price") is not None
                or plan.get("annual_price") is not None
            )
            if has_price:
                with_price += 1
            else:
                gaps.append({
                    "site_id": site_id,
                    "country": country,
                    "plan_name": plan.get("plan_name", "?"),
                })

    return with_price, total_paid, gaps


def print_coverage(results: list[dict], show_gaps: bool = False) -> None:
    """Print pricing coverage metric. Optionally show per-plan gaps."""
    with_price, total_paid, gaps = _count_pricing_coverage(results)

    if total_paid == 0:
        pct = 0.0
    else:
        pct = (with_price / total_paid) * 100

    print(f"\n  Pricing coverage: {with_price}/{total_paid} paid plans ({pct:.1f}%)")

    if show_gaps and gaps:
        print(f"\n  PRICING COVERAGE GAPS ({len(gaps)} plans missing prices):")
        for g in sorted(gaps, key=lambda x: (x["site_id"], x["country"])):
            print(f"    {g['site_id']}/{g['country'].upper()}: {g['plan_name']} (no price)")
    elif show_gaps:
        print(f"\n  No pricing coverage gaps — all paid plans have prices!")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="V2 Pricing Scraper Orchestrator")
    parser.add_argument(
        "--sites", nargs="+",
        help="Site IDs to scrape (e.g., spotify netflix)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Scrape all sites in the registry",
    )
    parser.add_argument(
        "--countries", nargs="+", default=["us"],
        help="Country codes (default: us)",
    )
    parser.add_argument(
        "--all-countries", action="store_true",
        help="Scrape all countries defined in the registry",
    )
    parser.add_argument(
        "--concurrent", action="store_true",
        help="Enable concurrent processing",
    )
    parser.add_argument(
        "--max-workers", type=int, default=2,
        help="Max concurrent workers (default: 2)",
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Don't save results to disk",
    )
    parser.add_argument(
        "--no-db", action="store_true",
        help="Skip SQLite storage and change detection (JSON only)",
    )
    parser.add_argument(
        "--coverage-report", action="store_true",
        help="Print per-plan pricing coverage gaps after scrape",
    )
    args = parser.parse_args()

    # Resolve sites
    if args.all:
        sites = get_sites()
    elif args.sites:
        sites = get_sites(args.sites)
    else:
        parser.error("Specify --sites or --all")

    if not sites:
        print("No sites matched. Use --all or check site IDs.")
        sys.exit(1)

    # Resolve countries
    if args.all_countries:
        countries = get_all_countries()
    else:
        countries = [c.lower() for c in args.countries]

    print(f"V2 Orchestrator")
    print(f"  Sites: {', '.join(s['id'] for s in sites)} ({len(sites)} total)")
    print(f"  Countries: {', '.join(c.upper() for c in countries)} ({len(countries)} total)")
    print(f"  Mode: {'concurrent' if args.concurrent else 'sequential'}")
    if args.concurrent:
        print(f"  Workers: {args.max_workers}")
    print()

    # Run
    results = run_scrape(
        sites=sites,
        countries=countries,
        concurrent=args.concurrent,
        max_workers=args.max_workers,
    )

    # Save
    saved_paths = []
    if not args.no_save:
        saved_paths = save_results(results)
        _log(f"Results saved: {len(saved_paths)} files to results/v2/")

    # Store to SQLite + detect changes
    if not args.no_db:
        try:
            from v2.store import store_run
            from v2.diff import detect_changes, print_change_report

            mode = "concurrent" if args.concurrent else "sequential"
            total_time = sum(r.get("elapsed_seconds", 0) for r in results)
            run_id = store_run(
                results, saved_paths, countries, mode=mode, elapsed_sec=total_time,
            )
            _log(f"Stored in SQLite: run #{run_id}")

            changes = detect_changes(run_id)
            print_change_report(changes, run_id)
        except Exception as e:
            _log(f"SQLite storage/diff error (non-fatal): {e}")

    # Summary
    print_summary(results)

    # Pricing coverage metric (always shown; --coverage-report shows per-plan gaps)
    print_coverage(results, show_gaps=args.coverage_report)


if __name__ == "__main__":
    main()

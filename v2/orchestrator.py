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
    python -m v2.orchestrator --all --countries us uk de --concurrent --max-workers 3
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
from v2.extractor import ExtractionResult, extract_with_fallback
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
# Single (site, country) scrape pipeline
# ---------------------------------------------------------------------------

def scrape_one(site_config: dict, country: str) -> dict:
    """
    Run the full pipeline for a single (site, country) pair.

    Steps:
    1. Resolve URL
    2. Get proxy (if non-US)
    3. Launch browser + create context (stealth)
    4. Pre-navigation setup (cookie injection)
    5. Navigate (networkidle → domcontentloaded fallback)
    6. Dismiss cookies
    7. Run post-navigation interaction (Netflix, Adobe)
    8. Stabilize page
    9. Capture HTML + screenshot
    10. Close browser
    11. Run v2 extraction cascade
    12. Return result dict

    Args:
        site_config: Site config dict from the registry.
        country: ISO alpha-2 country code.

    Returns:
        Result dict with extraction data and metadata.
    """
    site_id = site_config["id"]
    display_name = site_config["display_name"]
    start_time = time.time()

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
    }

    try:
        # 1. Resolve URL
        url = resolve_url(site_config, country)
        result["url"] = url
        _log(f"URL: {url}", site_id, country)

        # 2. Get proxy
        proxy_url = get_proxy_config(site_config, country)
        if proxy_url:
            _log(f"Using proxy for {country.upper()}", site_id, country)
        else:
            _log(f"No proxy (US or unavailable)", site_id, country)

        # 3-9. Browser lifecycle
        html, screenshot_path = _browser_phase(site_config, country, url, proxy_url)
        result["screenshot_path"] = screenshot_path

        # 10. Already closed in _browser_phase

        # 11. Extraction
        _log("Running extraction cascade...", site_id, country)
        extraction_result: ExtractionResult = extract_with_fallback(
            html=html,
            screenshot_path=screenshot_path,
            company=display_name,
            country=country,
        )

        result["status"] = "success"
        result["tier"] = extraction_result.tier
        result["confidence"] = extraction_result.extraction.extraction_confidence.value
        result["plan_count"] = len(extraction_result.extraction.plans)
        result["extraction"] = extraction_result.extraction.model_dump()

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        _log(f"ERROR: {e}", site_id, country)

    result["elapsed_seconds"] = round(time.time() - start_time, 1)
    _log(
        f"Done: {result['status']} | tier={result['tier']} | "
        f"confidence={result['confidence']} | plans={result['plan_count']} | "
        f"{result['elapsed_seconds']}s",
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
            try:
                page.goto(url, wait_until="networkidle", timeout=45000)
            except Exception:
                _log("networkidle timeout, retrying with domcontentloaded", site_id, country)
                page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # 7. Dismiss cookies
            dismiss_cookies(page)
            page.wait_for_timeout(1000)

            # 8. Run post-navigation interaction
            if site_config.get("requires_interaction"):
                _log(f"Running interaction: {site_config['interaction_type']}", site_id, country)
                run_interaction(page, site_config, country)

            # 9. Stabilize page
            stabilize_page(page)

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
    """Run scrapes concurrently with ThreadPoolExecutor."""
    results = []
    completed_count = 0

    _log(f"Concurrent mode: {max_workers} workers")

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
    errors = total - success

    tier_counts = {}
    confidence_counts = {}
    for r in results:
        if r.get("status") == "success":
            t = r.get("tier", "unknown")
            tier_counts[t] = tier_counts.get(t, 0) + 1
            c = r.get("confidence", "unknown")
            confidence_counts[c] = confidence_counts.get(c, 0) + 1

    print(f"\n  Summary: {success}/{total} succeeded, {errors} errors")
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
        "--max-workers", type=int, default=3,
        help="Max concurrent workers (default: 3)",
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Don't save results to disk",
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
    if not args.no_save:
        saved_paths = save_results(results)
        _log(f"Results saved: {len(saved_paths)} files to results/v2/")

    # Summary
    print_summary(results)


if __name__ == "__main__":
    main()

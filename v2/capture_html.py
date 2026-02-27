"""
Quick HTML capture script for testing the v2 cleaner.

Captures page HTML + screenshot for specified sites (US only, no proxy).
Saves to screenshots/html/ for offline cleaner testing.

Usage:
    python -m v2.capture_html spotify audible notion
    python -m v2.capture_html --all
"""

import os
import sys
import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright

# Site configs: url, browser, needs_interaction_notes
SITES = {
    "spotify": {
        "url": "https://www.spotify.com/us/premium/",
        "browser": "chromium",
    },
    "netflix": {
        "url": "https://www.netflix.com/signup/planform",
        "browser": "firefox",
    },
    "canva": {
        "url": "https://www.canva.com/pricing/",
        "browser": "firefox",
    },
    "audible": {
        "url": "https://www.audible.com/ep/memberbenefits",
        "browser": "chromium",
    },
    "notion": {
        "url": "https://www.notion.com/pricing",
        "browser": "chromium",
    },
    "dropbox": {
        "url": "https://www.dropbox.com/plans?billing=monthly",
        "browser": "chromium",
    },
    "adobe": {
        "url": "https://www.adobe.com/creativecloud/plans.html",
        "browser": "firefox",
    },
    "evernote": {
        "url": "https://evernote.com/compare-plans",
        "browser": "chromium",
    },
    "chatgpt_plus": {
        "url": "https://openai.com/pricing",
        "browser": "firefox",
    },
    "peacock": {
        "url": "https://www.peacocktv.com/",
        "browser": "firefox",
    },
    "disney_plus": {
        "url": "https://www.disneyplus.com/en/commerce/plans",
        "browser": "firefox",
    },
    "youtube": {
        "url": "https://www.youtube.com/premium",
        "browser": "firefox",
    },
    "box": {
        "url": "https://www.box.com/pricing/individual",
        "browser": "firefox",
    },
    "figma": {
        "url": "https://www.figma.com/pricing/",
        "browser": "chromium",
    },
    "grammarly": {
        "url": "https://www.grammarly.com/plans",
        "browser": "chromium",
    },
    "zwift": {
        "url": "https://www.zwift.com/us/pricing",
        "browser": "chromium",
    },
}

CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-web-security",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
    ]
});
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""


def try_dismiss_cookies(page):
    """Try common cookie consent patterns."""
    selectors = [
        'button:has-text("Accept")',
        'button:has-text("Accept All")',
        'button:has-text("Accept all")',
        'button:has-text("Accept Cookies")',
        'button:has-text("I Accept")',
        'button:has-text("Got it")',
        'button:has-text("OK")',
        '#onetrust-accept-btn-handler',
        '[data-testid="cookie-policy-dialog-accept-button"]',
    ]
    for sel in selectors:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
                return True
        except Exception:
            continue
    # Try pressing Escape as a last resort
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    return False


def capture_site(site_name, site_config, output_dir, p):
    """Capture HTML + screenshot for a single site."""
    url = site_config["url"]
    use_firefox = site_config["browser"] == "firefox"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'─'*50}")
    print(f"  {site_name.upper()} — {url}")
    print(f"  Browser: {'Firefox' if use_firefox else 'Chromium'}")

    try:
        # Launch browser
        if use_firefox:
            browser = p.firefox.launch(
                headless=True,
                args=["--width=1920", "--height=1080"],
                timeout=60000,
            )
        else:
            browser = p.chromium.launch(
                headless=True,
                args=CHROMIUM_ARGS,
                timeout=60000,
            )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=USER_AGENT,
            java_script_enabled=True,
            bypass_csp=True,
        )

        # Add stealth for Chromium only (Firefox doesn't need/support init_script well)
        if not use_firefox:
            context.add_init_script(STEALTH_JS)

        page = context.new_page()

        # Navigate
        print(f"  Navigating...", end=" ", flush=True)
        page.goto(url, wait_until="networkidle", timeout=45000)
        print("done")

        # Small random delay (human-like)
        delay = random.uniform(1.5, 3.0)
        page.wait_for_timeout(int(delay * 1000))

        # Try cookie consent
        try_dismiss_cookies(page)
        page.wait_for_timeout(1000)

        # Gentle scroll to trigger lazy content
        page.evaluate("window.scrollBy(0, 300)")
        page.wait_for_timeout(1000)
        page.evaluate("window.scrollBy(0, 500)")
        page.wait_for_timeout(1500)

        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        # Capture HTML
        html_content = page.content()
        html_path = os.path.join(output_dir, f"{site_name}_us_{timestamp}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Capture screenshot
        screenshot_path = os.path.join(
            output_dir, "..", f"{site_name}_us_{timestamp}.png"
        )
        page.screenshot(path=screenshot_path, full_page=True)

        print(f"  HTML: {len(html_content):,} chars → {html_path}")
        print(f"  Screenshot: {screenshot_path}")
        print(f"  ✓ Success")

        browser.close()
        return html_path

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        try:
            browser.close()
        except Exception:
            pass
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m v2.capture_html <site1> <site2> ...")
        print(f"       python -m v2.capture_html --all")
        print(f"\nAvailable sites: {', '.join(sorted(SITES.keys()))}")
        sys.exit(1)

    if "--all" in sys.argv:
        sites_to_capture = list(SITES.keys())
    else:
        sites_to_capture = [s.lower() for s in sys.argv[1:]]
        for s in sites_to_capture:
            if s not in SITES:
                print(f"Unknown site: {s}")
                print(f"Available: {', '.join(sorted(SITES.keys()))}")
                sys.exit(1)

    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "screenshots", "html",
    )
    os.makedirs(output_dir, exist_ok=True)

    print(f"Capturing {len(sites_to_capture)} sites → {output_dir}")

    results = {}
    with sync_playwright() as p:
        for site_name in sites_to_capture:
            html_path = capture_site(site_name, SITES[site_name], output_dir, p)
            results[site_name] = html_path

    # Summary
    print(f"\n{'='*50}")
    print(f"  CAPTURE SUMMARY")
    print(f"{'='*50}")
    succeeded = [s for s, p in results.items() if p]
    failed = [s for s, p in results.items() if not p]
    print(f"  Succeeded: {len(succeeded)}/{len(results)}")
    for s in succeeded:
        print(f"    ✓ {s}")
    if failed:
        print(f"  Failed: {len(failed)}")
        for s in failed:
            print(f"    ✗ {s}")

    # If any succeeded, run the cleaner on them
    if succeeded:
        print(f"\n{'='*50}")
        print(f"  RUNNING HTML CLEANER")
        print(f"{'='*50}")
        from v2.html_cleaner import clean_html, PRICING_KEYWORDS, MAX_OUTPUT_CHARS

        for site_name in succeeded:
            path = results[site_name]
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            cleaned = clean_html(raw)
            pricing_hits = len(PRICING_KEYWORDS.findall(cleaned))
            under_limit = len(cleaned) <= MAX_OUTPUT_CHARS
            print(
                f"  {site_name:<16} "
                f"raw={len(raw):>10,}  "
                f"cleaned={len(cleaned):>8,}  "
                f"reduction={100*(1-len(cleaned)/len(raw)):>5.1f}%  "
                f"pricing_kw={pricing_hits:<4} "
                f"{'✓' if under_limit else '✗ OVER 32K'}"
            )


if __name__ == "__main__":
    main()

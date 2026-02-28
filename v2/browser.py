"""
Browser lifecycle manager for the v2 pipeline.

Handles browser launch, stealth injection, cookie consent dismissal,
page stabilization, and HTML/screenshot capture. Two stealth profiles:

- chromium_standard: anti-detection args + init_script stealth JS
- firefox_stealth: minimal args, inherent lower detection surface

Usage:
    python -m v2.browser --site spotify --country us
    python -m v2.browser --site netflix --country us
"""

import os
import sys
import random
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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

COOKIE_SELECTORS = [
    'button:has-text("Accept")',
    'button:has-text("Accept All")',
    'button:has-text("Accept all")',
    'button:has-text("Accept Cookies")',
    'button:has-text("I Accept")',
    'button:has-text("Got it")',
    'button:has-text("OK")',
    'button:has-text("Allow all")',
    'button:has-text("I agree")',
    'button:has-text("Allow cookies")',
    '#onetrust-accept-btn-handler',
    '[data-testid="cookie-policy-dialog-accept-button"]',
    '[data-testid="cookie-notice-accept-button"]',
    'button.accept-cookies',
    '.cookie-banner button',
    'button.consent-accept',
    '[aria-label="Accept cookies"]',
]

# CSS to inject that hides common consent banners
CONSENT_HIDE_CSS = """
#onetrust-consent-sdk, #onetrust-banner-sdk, #CybotCookiebotDialog,
.cookie-banner, .cookie-consent, [class*="cookie-banner"],
[class*="consent-banner"], [id*="cookie-banner"],
[class*="CookieConsent"], [id*="CookieConsent"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
    z-index: -9999 !important;
}
"""


# ---------------------------------------------------------------------------
# Browser launch + context
# ---------------------------------------------------------------------------

def _parse_proxy_url(proxy_url: str) -> dict:
    """
    Parse a proxy URL with embedded credentials into Playwright's proxy dict format.

    Input:  http://username:password@host:port
    Output: {"server": "http://host:port", "username": "...", "password": "..."}
    """
    from urllib.parse import urlparse
    parsed = urlparse(proxy_url)
    server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
    result = {"server": server}
    if parsed.username:
        result["username"] = parsed.username
    if parsed.password:
        result["password"] = parsed.password
    return result


def launch_browser(pw, site_config: dict, proxy_url: str | None = None):
    """
    Launch a browser instance based on site config.

    Args:
        pw: Playwright instance (from sync_playwright).
        site_config: Site config dict from the registry.
        proxy_url: Optional proxy URL string.

    Returns:
        Browser instance.
    """
    use_firefox = site_config["browser"] == "firefox"
    headless = site_config.get("headless", True)

    proxy_arg = None
    if proxy_url:
        proxy_arg = _parse_proxy_url(proxy_url)

    if use_firefox:
        browser = pw.firefox.launch(
            headless=headless,
            args=["--width=1920", "--height=1080"],
            proxy=proxy_arg,
            timeout=60000,
        )
    else:
        browser = pw.chromium.launch(
            headless=headless,
            args=CHROMIUM_ARGS,
            proxy=proxy_arg,
            timeout=60000,
        )

    return browser


def create_context(browser, site_config: dict, country: str):
    """
    Create a browser context with stealth settings.

    Args:
        browser: Browser instance.
        site_config: Site config dict from the registry.
        country: ISO alpha-2 country code.

    Returns:
        BrowserContext instance.
    """
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=USER_AGENT,
        java_script_enabled=True,
        bypass_csp=True,
    )

    # Stealth injection: Chromium only, and skip for Canva (documented crash)
    use_firefox = site_config["browser"] == "firefox"
    skip_init = site_config.get("skip_init_script", False)

    if not use_firefox and not skip_init:
        context.add_init_script(STEALTH_JS)

    return context


# ---------------------------------------------------------------------------
# Cookie consent dismissal
# ---------------------------------------------------------------------------

def dismiss_cookies(page) -> bool:
    """
    Try to dismiss cookie consent banners.

    Strategy:
    1. Try clicking common accept buttons (selector-based).
    2. Inject JS to set common cookie consent cookies silently.
    3. Inject CSS to hide remaining banners.
    4. Press Escape as a last resort.

    Args:
        page: Playwright page object.

    Returns:
        True if any dismissal action succeeded.
    """
    dismissed = False

    # Strategy 1: Click common accept buttons
    for sel in COOKIE_SELECTORS:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
                dismissed = True
                break
        except Exception:
            continue

    # Strategy 2: Silent JS cookie injection
    try:
        page.evaluate("""() => {
            const expires = new Date(Date.now() + 365*24*60*60*1000).toUTCString();
            document.cookie = 'OptanonAlertBoxClosed=' + new Date().toISOString() + ';path=/;expires=' + expires;
            document.cookie = 'OptanonConsent=isGpcEnabled=0&datestamp=' + new Date().toISOString() + '&version=6.0.0&isIABGlobal=false&hosts=&consentId=consent123&interactionCount=1&landingPath=NotLandingPage&groups=C0001:1,C0002:1,C0003:1,C0004:1;path=/;expires=' + expires;
            document.cookie = 'cookieConsent=true;path=/;expires=' + expires;
            document.cookie = 'cookie_consent=accepted;path=/;expires=' + expires;
        }""")
    except Exception:
        pass

    # Strategy 3: CSS injection to hide remaining banners
    try:
        page.add_style_tag(content=CONSENT_HIDE_CSS)
    except Exception:
        pass

    # Strategy 4: Escape key fallback
    if not dismissed:
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception:
            pass

    return dismissed


# ---------------------------------------------------------------------------
# Page stabilization
# ---------------------------------------------------------------------------

def stabilize_page(page) -> None:
    """
    Stabilize the page by scrolling to trigger lazy-loaded content,
    then scrolling back to top.

    Args:
        page: Playwright page object.
    """
    delay = random.uniform(1.5, 3.0)
    page.wait_for_timeout(int(delay * 1000))

    # Gentle scroll to trigger lazy content
    page.evaluate("window.scrollBy(0, 300)")
    page.wait_for_timeout(1000)
    page.evaluate("window.scrollBy(0, 500)")
    page.wait_for_timeout(1500)

    # Scroll back to top
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)


# ---------------------------------------------------------------------------
# Page capture
# ---------------------------------------------------------------------------

def capture_page(page, site_id: str, country: str) -> tuple[str, str]:
    """
    Capture page HTML and a full-page screenshot.

    Args:
        page: Playwright page object.
        site_id: Site identifier (e.g., "spotify").
        country: ISO alpha-2 country code.

    Returns:
        Tuple of (html_content, screenshot_path).
    """
    # Ensure output directories exist
    project_root = Path(__file__).parent.parent
    screenshot_dir = project_root / "screenshots" / "v2"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Capture HTML
    html_content = page.content()

    # Capture screenshot
    screenshot_path = str(screenshot_dir / f"{site_id}_{country}_{timestamp}.png")
    page.screenshot(path=screenshot_path, full_page=True)

    return html_content, screenshot_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Quick test: launch browser, navigate, screenshot, close."""
    import argparse
    from playwright.sync_api import sync_playwright
    from v2.registry import get_sites, resolve_url

    parser = argparse.ArgumentParser(description="V2 Browser Test")
    parser.add_argument("--site", required=True, help="Site ID to test")
    parser.add_argument("--country", default="us", help="Country code (default: us)")
    args = parser.parse_args()

    sites = get_sites([args.site])
    if not sites:
        print(f"Unknown site: {args.site}")
        sys.exit(1)

    site_config = sites[0]
    country = args.country.lower()
    url = resolve_url(site_config, country)

    print(f"Testing browser for {site_config['display_name']} ({country.upper()})")
    print(f"  URL: {url}")
    print(f"  Browser: {site_config['browser']}")
    print(f"  Headless: {site_config['headless']}")

    with sync_playwright() as pw:
        browser = launch_browser(pw, site_config)
        context = create_context(browser, site_config, country)
        page = context.new_page()

        print(f"  Navigating...", end=" ", flush=True)
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
        except Exception:
            print("networkidle timeout, falling back to domcontentloaded")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        print("done")

        dismiss_cookies(page)
        stabilize_page(page)

        html, screenshot_path = capture_page(page, args.site, country)

        print(f"  HTML: {len(html):,} chars")
        print(f"  Screenshot: {screenshot_path}")

        browser.close()
        print(f"  Done")


if __name__ == "__main__":
    main()

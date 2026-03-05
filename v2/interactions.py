"""
Site-specific interaction overrides for the v2 pipeline.

Handles pre-navigation setup (cookie injection, anti-detection) and
post-navigation interactions (Netflix signup flow, Adobe geo-popup,
Disney+ price wait, Zwift region popup).

Usage:
    from v2.interactions import pre_navigation_setup, run_interaction
    pre_navigation_setup(context, site_config, country)
    # ... navigate ...
    run_interaction(page, site_config, country)
"""

import re
import sys
import random
import time


# Zero-width characters used by Netflix (and others) as anti-scraping.
# Must be stripped before any text pattern matching.
_ZERO_WIDTH_RE = re.compile(r'[\ufeff\u200b\u200c\u200d\u00ad\ufffe]')


def _strip_zero_width(text: str) -> str:
    """Remove zero-width / invisible Unicode characters from text."""
    return _ZERO_WIDTH_RE.sub('', text)


# ---------------------------------------------------------------------------
# Language mappings for Netflix multi-step flow
# ---------------------------------------------------------------------------

COUNTRY_TO_LANG = {
    "us": "en", "uk": "en", "ca": "en", "au": "en",
    "de": "de", "fr": "fr", "it": "it", "es": "es",
    "br": "pt", "mx": "es", "jp": "ja", "in": "en", "nl": "nl",
}

# Button text by language for Netflix "Next"/"Continue" buttons
NETFLIX_BUTTON_TEXT = {
    "en": ["Next", "Continue", "Get Started", "See the Plans"],
    "de": ["Weiter", "Fortfahren", "Jetzt loslegen"],
    "fr": ["Suivant", "Continuer", "Commencer"],
    "it": ["Avanti", "Continua", "Inizia"],
    "es": ["Siguiente", "Continuar", "Comenzar", "Empezar"],
    "pt": ["Próximo", "Continuar", "Avançar", "Começar"],
    "ja": ["続ける", "次へ", "開始", "始める"],
    "nl": ["Volgende", "Doorgaan", "Aan de slag"],
}

# Step indicators by language — multiple patterns per language
NETFLIX_STEP_PATTERNS = {
    "en": ["STEP 1 OF 4", "STEP 1 OF 3", "Choose your plan", "STEP"],
    "de": ["SCHRITT 1 VON 3", "SCHRITT 1 VON 4", "Wählen Sie Ihr Abo", "SCHRITT"],
    "fr": ["ÉTAPE 1 SUR", "Choisissez votre forfait", "ÉTAPE"],
    "it": ["PASSAGGIO 1 DI 3", "PASSAGGIO 1 DI 4", "Scegli un piano", "PASSAGGIO"],
    "es": ["PASO 1 DE", "Elige tu plan", "PASO"],
    "pt": ["PASSO 1 DE 3", "PASSO 1 DE 4", "Escolha seu plano", "PASSO"],
    "ja": ["ステップ1/3", "ステップ1/4", "プランを選択", "プランをお選びください", "ステップ"],
    "nl": ["STAP 1 VAN 3", "STAP 1 VAN 4", "Kies je abonnement", "STAP"],
}

# Pricing indicators to detect if we've reached the plan form.
# Split into "price" signals (currency) and "billing" signals (period text).
# We require BOTH a price signal AND a billing signal in VISIBLE text to confirm
# real pricing content — checking raw HTML matches too much JS/CSS noise.
PRICE_SIGNALS = [
    "$", "€", "£", "¥", "₹", "R$", "￥", "月額",
]
BILLING_SIGNALS = [
    "/month", "/mo", "/mes", "/mois", "/monat", "/mese", "/maand",
    "per month", "por mes", "par mois", "pro monat", "al mese", "per maand",
    "a month", "ao mês",
    "monthly price", "precio mensual", "prix mensuel", "monatlicher preis",
    "prezzo mensile", "maandelijkse prijs", "prijs per maand",
    "月額", "月額料金", "プラン",
]


# ---------------------------------------------------------------------------
# Pre-navigation setup
# ---------------------------------------------------------------------------

def pre_navigation_setup(context, site_config: dict, country: str) -> None:
    """
    Inject cookies and anti-detection into the browser context BEFORE page navigation.

    Called before page.goto() to pre-set consent and geo-preference cookies.

    Args:
        context: Playwright BrowserContext.
        site_config: Site config dict from the registry.
        country: ISO alpha-2 country code.
    """
    interaction_type = site_config.get("interaction_type")

    if interaction_type == "netflix_multi_step":
        _netflix_pre_nav(context, country)
    elif interaction_type == "adobe_geo_popup":
        _adobe_pre_nav(context, country)


def _netflix_pre_nav(context, country: str) -> None:
    """
    Inject Netflix anti-detection scripts, cookies, and HTTP headers before navigation.

    Ports proven techniques from the old handler (archive/site_handlers/netflix.py).
    Language/locale settings are matched to the target country so Netflix doesn't
    switch to English after client-side navigation.
    """
    # Build locale-appropriate language settings
    lang = COUNTRY_TO_LANG.get(country.lower(), "en")
    locale_map = {
        "en": ("en-US", "en-US,en"),
        "de": ("de-DE", "de-DE,de;q=0.9,en;q=0.5"),
        "fr": ("fr-FR", "fr-FR,fr;q=0.9,en;q=0.5"),
        "it": ("it-IT", "it-IT,it;q=0.9,en;q=0.5"),
        "es": ("es-ES", "es-ES,es;q=0.9,en;q=0.5"),
        "pt": ("pt-BR", "pt-BR,pt;q=0.9,en;q=0.5"),
        "ja": ("ja-JP", "ja-JP,ja;q=0.9,en;q=0.5"),
        "nl": ("nl-NL", "nl-NL,nl;q=0.9,en;q=0.5"),
    }
    primary_locale, accept_lang = locale_map.get(lang, ("en-US", "en-US,en"))
    nav_languages = f"['{primary_locale}', '{lang}']"

    # 1. Anti-detection init_script (webdriver masking, fake plugins, automation trace removal)
    try:
        context.add_init_script(f"""
            // Remove webdriver property completely
            Object.defineProperty(navigator, 'webdriver', {{
                get: () => undefined,
            }});

            // Mock realistic plugins array
            Object.defineProperty(navigator, 'plugins', {{
                get: () => [
                    {{name: "Chrome PDF Plugin", filename: "internal-pdf-viewer"}},
                    {{name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai"}},
                    {{name: "Native Client", filename: "internal-nacl-plugin"}}
                ]
            }});

            // Mock languages matching target country
            Object.defineProperty(navigator, 'languages', {{
                get: () => {nav_languages}
            }});

            // Remove automation traces
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
        """)
        _log(f"Netflix: anti-detection init_script injected (locale={primary_locale})")
    except Exception as e:
        _log(f"Netflix: init_script injection failed (non-fatal): {e}")

    # 2. Extra HTTP headers for stealth (locale-matched)
    try:
        context.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": accept_lang,
            "Cache-Control": "max-age=0",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        })
    except Exception as e:
        _log(f"Netflix: header injection failed (non-fatal): {e}")

    # 3. Pre-nav cookies
    try:
        context.add_cookies([
            {
                "name": "nfvdid",
                "value": f"BQFmAAEBEHQ{random.randint(10000, 99999)}",
                "domain": ".netflix.com",
                "path": "/",
            },
            {
                "name": "SecureNetflixId",
                "value": f"v%3D2%26mac%3DAQEAEAABABQdwdGV{random.randint(1000, 9999)}",
                "domain": ".netflix.com",
                "path": "/",
            },
        ])
        _log("Netflix: pre-nav cookies injected")
    except Exception as e:
        _log(f"Netflix: pre-nav cookie injection failed: {e}")


def _adobe_pre_nav(context, country: str) -> None:
    """Inject Adobe geo-preference and consent cookies before navigation."""
    try:
        context.add_cookies([
            {
                "name": "OptanonAlertBoxClosed",
                "value": "2024-07-16T12:00:00.000Z",
                "domain": ".adobe.com",
                "path": "/",
            },
            {
                "name": "CookieConsent",
                "value": "true",
                "domain": ".adobe.com",
                "path": "/",
            },
            {
                "name": "privacy_accepted",
                "value": "true",
                "domain": ".adobe.com",
                "path": "/",
            },
            {
                "name": "adobe_mc_geo",
                "value": country.upper(),
                "domain": ".adobe.com",
                "path": "/",
            },
            {
                "name": "geo_preference_set",
                "value": "true",
                "domain": ".adobe.com",
                "path": "/",
            },
        ])
        _log("Adobe: pre-nav cookies injected")
    except Exception as e:
        _log(f"Adobe: pre-nav cookie injection failed: {e}")


# ---------------------------------------------------------------------------
# Post-navigation interactions
# ---------------------------------------------------------------------------

def run_interaction(page, site_config: dict, country: str) -> bool:
    """
    Run site-specific post-navigation interaction.

    Dispatches based on site_config["interaction_type"].

    Args:
        page: Playwright page object (already navigated).
        site_config: Site config dict from the registry.
        country: ISO alpha-2 country code.

    Returns:
        True if interaction succeeded or no interaction needed.
    """
    interaction_type = site_config.get("interaction_type")

    if not interaction_type:
        return True

    if interaction_type == "netflix_multi_step":
        return _netflix_multi_step(page, country)
    elif interaction_type == "adobe_geo_popup":
        return _adobe_geo_popup(page, country)
    elif interaction_type == "disney_wait_for_prices":
        return _disney_wait_for_prices(page, country)
    elif interaction_type == "zwift_region_popup":
        return _zwift_region_popup(page, country)
    elif interaction_type == "canva_toggle_billing":
        return _canva_toggle_billing(page, country)
    else:
        _log(f"Unknown interaction type: {interaction_type}")
        return True


# ---------------------------------------------------------------------------
# Netflix multi-step signup flow (ported from archive/site_handlers/netflix.py)
# ---------------------------------------------------------------------------

def _has_pricing_content(page_or_html) -> bool:
    """
    Check if the page has VISIBLE pricing content.

    Accepts either a Playwright page object (preferred — uses inner_text)
    or a raw HTML string (fallback — less reliable).

    Requires BOTH a currency/price signal AND a billing-period signal
    to avoid false positives from JS/CSS class names like "planCard",
    "Standard", "$" in template literals, etc.
    """
    try:
        # Prefer visible text from the page object
        if hasattr(page_or_html, 'inner_text'):
            text = page_or_html.inner_text('body')
        else:
            text = page_or_html
    except Exception:
        return False

    # Strip zero-width anti-scraping characters (Netflix JP etc.)
    text = _strip_zero_width(text)

    has_price = any(sig in text for sig in PRICE_SIGNALS)
    has_billing = any(sig in text.lower() for sig in BILLING_SIGNALS)
    return has_price and has_billing


def _netflix_cookie_consent(page) -> None:
    """
    Ultra-stealth cookie consent handling for Netflix.

    Sets consent cookies via JS eval and injects CSS to hide any consent UI.
    Ported from old handler's handle_cookie_consent().
    """
    try:
        page.evaluate("""() => {
            try {
                document.cookie = "OptanonAlertBoxClosed=2024-01-01T00:00:00.000Z; path=/; domain=.netflix.com; max-age=31536000";
                document.cookie = "OptanonConsent=isGpcEnabled=0&datestamp=Mon+Jan+01+2024; path=/; domain=.netflix.com; max-age=31536000";
                document.cookie = "cookieConsent=true; path=/; domain=.netflix.com; max-age=31536000";

                const style = document.createElement('style');
                style.textContent = `
                    div[class*="cookie"], div[id*="cookie"],
                    div[class*="consent"], div[id*="consent"],
                    div[class*="gdpr"], div[id*="gdpr"],
                    .cookie-disclosure, .gdpr-disclosure,
                    [data-uia*="cookie"], [data-uia*="consent"] {
                        opacity: 0 !important;
                        pointer-events: none !important;
                        z-index: -9999 !important;
                        display: none !important;
                    }
                `;
                document.head.appendChild(style);
            } catch(e) {}
        }""")
        _log("Netflix: cookie consent handled via JS")
    except Exception as e:
        _log(f"Netflix: cookie consent JS failed (non-fatal): {e}")


def _netflix_click_button(page, element, description: str) -> bool:
    """
    Try multiple click methods on a Netflix button element.

    Returns True if any click method succeeded.
    """
    methods = [
        ("normal", lambda: element.click()),
        ("force", lambda: element.click(force=True)),
    ]
    for method_name, click_fn in methods:
        try:
            click_fn()
            _log(f"Netflix: clicked {description} ({method_name})")
            return True
        except Exception:
            continue
    return False


def _netflix_js_click_cta(page) -> bool:
    """
    Click Netflix's primary CTA button via JavaScript, bypassing text selectors.

    Netflix JP (and potentially other locales) injects U+FEFF zero-width chars
    between every character, breaking Playwright's :has-text() selectors.
    This function finds the CTA by DOM structure instead of text content.

    Uses both element.click() and dispatchEvent(MouseEvent) for reliability —
    some React hydration states only respond to one or the other.
    """
    # JS that finds the big CTA button by size/position (text-independent)
    find_cta_js = """() => {
        // Try Netflix data-uia attributes first
        var selectors = [
            '[data-uia="nmhp-card-cta"]',
            '[data-uia="next-button"]',
            '[data-uia="cta-link"]',
            '[data-uia="action-button"]',
            'button[type="submit"]',
        ];
        for (var s = 0; s < selectors.length; s++) {
            var el = document.querySelector(selectors[s]);
            if (el) {
                var rect = el.getBoundingClientRect();
                if (rect.width > 50 && rect.height > 20) return el;
            }
        }
        // Fallback: find big visible button by size
        var btns = document.querySelectorAll('button, a[role="button"]');
        for (var i = 0; i < btns.length; i++) {
            var b = btns[i];
            var rect = b.getBoundingClientRect();
            if (rect.width > 100 && rect.height > 30 && rect.top > 100 && rect.top < 800) {
                return b;
            }
        }
        return null;
    }"""

    # Try Playwright's native click on the element (most reliable for React)
    try:
        handle = page.evaluate_handle(find_cta_js)
        if handle:
            el = handle.as_element()
            if el:
                # Use Playwright's click which simulates real mouse events
                el.click()
                _log("Netflix: JS CTA click succeeded (Playwright click)")
                return True
    except Exception:
        pass

    # Fallback: use JS dispatchEvent with full MouseEvent
    try:
        clicked = page.evaluate(f"""() => {{
            var el = ({find_cta_js})();
            if (!el) return false;
            // Try .click() first
            el.click();
            // Also dispatch a proper MouseEvent in case React needs it
            var rect = el.getBoundingClientRect();
            var evt = new MouseEvent('click', {{
                bubbles: true, cancelable: true, view: window,
                clientX: rect.x + rect.width / 2,
                clientY: rect.y + rect.height / 2
            }});
            el.dispatchEvent(evt);
            return true;
        }}""")
        if clicked:
            _log("Netflix: JS CTA click succeeded (dispatchEvent)")
            return True
    except Exception:
        pass

    _log("Netflix: JS CTA click — no button found")
    return False


def _netflix_wait_for_pricing(page, timeout_sec: float = 18.0) -> bool:
    """
    Poll for visible pricing content after a click/navigation.

    Netflix's React app updates the DOM asynchronously after a click —
    a single sleep isn't reliable. Poll every 2s up to timeout.
    Also re-clicks the CTA at the halfway point if pricing hasn't appeared
    (handles cases where the first click didn't trigger React's handler).
    """
    elapsed = 0.0
    interval = 2.0
    reclicked = False
    while elapsed < timeout_sec:
        time.sleep(interval)
        elapsed += interval
        if _has_pricing_content(page):
            return True
        # Re-click at the halfway point in case the first click didn't take
        if not reclicked and elapsed >= timeout_sec / 2:
            reclicked = True
            _netflix_js_click_cta(page)
    return False


def _netflix_multi_step(page, country: str) -> bool:
    """
    Handle Netflix's multi-step signup flow.

    Robust implementation ported from the old handler. Key improvements over
    the previous v2 version:
    - Ultra-stealth cookie consent (JS eval + CSS injection)
    - Longer wait times after clicks (4-6s instead of 3s)
    - Multiple click fallback methods per button
    - Japanese-specific direct locator handling
    - Expanded CSS selector strategies
    - Country-prefixed fallback navigation
    - Natural scrolling after reaching plan form
    - Multiple step detection patterns per language

    Args:
        page: Playwright page object.
        country: ISO alpha-2 country code.

    Returns:
        True if we reached the plan form (or were already there).
    """
    expected_lang = COUNTRY_TO_LANG.get(country.lower(), "en")

    # Handle cookie consent first (ultra-stealth)
    _netflix_cookie_consent(page)
    time.sleep(random.uniform(2.0, 3.0))

    # Check if we're already on the plan form (uses visible text, not raw HTML)
    if _has_pricing_content(page):
        _log("Netflix: pricing content detected, already on plan form")
        _netflix_natural_scroll(page)
        return True

    # Check for step indicator using visible text.
    # Netflix may serve a different language than expected (e.g. English for JP),
    # so check ALL languages' step patterns plus English as fallback.
    # Strip zero-width chars first (Netflix JP injects U+FEFF between characters).
    visible_text = ""
    try:
        visible_text = _strip_zero_width(page.inner_text("body"))
    except Exception:
        pass
    text_lower = visible_text.lower()

    # Detect which language the page is actually in
    lang = expected_lang
    step_found = False
    for check_lang, patterns in NETFLIX_STEP_PATTERNS.items():
        if any(p.lower() in text_lower for p in patterns):
            step_found = True
            lang = check_lang
            break

    if not step_found:
        _log("Netflix: no step indicator found, assuming we're on the right page")
        return True

    _log(f"Netflix: step indicator found, attempting click-through (lang={lang})")

    # --- Strategy 0: JS-based click on the primary CTA button ---
    # Netflix injects zero-width characters (U+FEFF) in non-English pages,
    # breaking all text-based selectors. Use data-uia or role-based JS click first.
    cta_clicked = _netflix_js_click_cta(page)
    if cta_clicked:
        if _netflix_wait_for_pricing(page):
            _log("Netflix: JS CTA click reached plan form")
            _netflix_natural_scroll(page)
            return True
        _log("Netflix: JS CTA clicked but no pricing yet, trying other strategies...")

    # --- Japanese-specific handling: try direct locator ---
    if lang == "ja":
        _log("Netflix: trying direct Japanese button locator...")
        for jp_text in ["続ける", "次へ"]:
            try:
                locator = page.locator(f"text={jp_text}").first
                if locator.count() > 0:
                    locator.click()
                    _log(f"Netflix: clicked Japanese '{jp_text}' via direct locator")

                    if _netflix_wait_for_pricing(page):
                        _log("Netflix: Japanese click reached plan form")
                        _netflix_natural_scroll(page)
                        return True
            except Exception:
                continue

    # --- Generic button click strategies ---
    button_texts = NETFLIX_BUTTON_TEXT.get(lang, NETFLIX_BUTTON_TEXT["en"])

    for text in button_texts:
        selectors = [
            f'button:has-text("{text}")',
            f'[role="button"]:has-text("{text}")',
            f'input[value="{text}"]',
            f'a:has-text("{text}")',
        ]

        for sel in selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    if _netflix_click_button(page, btn, f"'{text}'"):
                        if _netflix_wait_for_pricing(page):
                            _log("Netflix: successfully reached plan form")
                            _netflix_natural_scroll(page)
                            return True

                        # Maybe we moved to step 2 — try clicking again
                        _log("Netflix: clicked but no pricing yet, trying next...")
            except Exception:
                continue

    # --- Fallback: Netflix-specific data-uia and CSS selectors ---
    fallback_selectors = [
        '[data-uia="next-button"]',
        '[data-uia="cta-link"]',
        '[data-uia="action-button"]',
        'button[type="submit"]',
        '.btn-red',
        '.nf-btn-primary',
        'button.btn',
    ]

    for sel in fallback_selectors:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                if _netflix_click_button(page, btn, f"fallback {sel}"):
                    if _netflix_wait_for_pricing(page):
                        _log("Netflix: fallback click reached plan form")
                        _netflix_natural_scroll(page)
                        return True
        except Exception:
            continue

    # --- Last resort: direct navigation to country-prefixed planform ---
    country_lower = country.lower()
    fallback_urls = [
        f"https://www.netflix.com/{country_lower}/signup/planform",
        "https://www.netflix.com/signup/planform",
    ]

    for fallback_url in fallback_urls:
        _log(f"Netflix: trying direct navigation to {fallback_url}")
        try:
            page.goto(fallback_url, wait_until="domcontentloaded", timeout=30000)

            if _netflix_wait_for_pricing(page):
                _log("Netflix: direct navigation reached plan form")
                _netflix_natural_scroll(page)
                return True
        except Exception as e:
            _log(f"Netflix: direct navigation failed: {e}")

    _log("Netflix: all click strategies exhausted")
    return False


def _netflix_natural_scroll(page) -> None:
    """Natural scrolling to trigger lazy-loaded content on Netflix plan form."""
    try:
        page.evaluate("window.scrollTo(0, 100)")
        time.sleep(random.uniform(1.0, 2.0))
        page.evaluate("window.scrollTo(0, 400)")
        time.sleep(random.uniform(1.5, 2.5))
        page.evaluate("window.scrollTo(0, 800)")
        time.sleep(random.uniform(1.0, 1.8))
        page.evaluate("window.scrollTo(0, 200)")
        time.sleep(random.uniform(0.8, 1.5))
    except Exception:
        pass


def _adobe_geo_popup(page, country: str) -> bool:
    """
    Handle Adobe's geo-preference popup.

    Injects CSS to hide geo/region popups and tries to click
    "Stay" / "Continue" buttons.

    Args:
        page: Playwright page object.
        country: ISO alpha-2 country code.

    Returns:
        True if popup was handled (or wasn't present).
    """
    # CSS injection to hide geo-popups and modals
    geo_hide_css = """
    [class*="geo-popup"], [id*="geo-popup"],
    [class*="location-popup"], [id*="location-popup"],
    [class*="region-popup"], [id*="region-popup"],
    [aria-label*="location"], [aria-label*="region"],
    [aria-label*="wrong site"],
    .modal-backdrop, .overlay,
    [role="dialog"][aria-modal="true"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        z-index: -9999 !important;
    }
    """

    try:
        page.add_style_tag(content=geo_hide_css)
        _log("Adobe: geo-popup CSS injected")
    except Exception as e:
        _log(f"Adobe: CSS injection failed: {e}")

    # Try clicking "Stay" / "Continue" / "Remain" buttons
    stay_selectors = [
        'button:has-text("Stay")',
        'button:has-text("Continue")',
        'button:has-text("Remain")',
        '[class*="stay-button"]',
        '[class*="continue-button"]',
        '.modal-footer button:nth-child(2)',
        '.btn-secondary',
        '.button-secondary',
    ]

    for sel in stay_selectors:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                _log(f"Adobe: clicking geo-popup button ({sel})")
                btn.click()
                page.wait_for_timeout(1000)
                return True
        except Exception:
            continue

    # Stabilization wait
    page.wait_for_timeout(3000)
    _log("Adobe: geo-popup handling complete (no popup detected or CSS hid it)")
    return True


# ---------------------------------------------------------------------------
# Disney+ price wait interaction
# ---------------------------------------------------------------------------

_DISNEY_PRICE_RE = re.compile(r'[\$€£¥₹][\s]?\d+[.,]?\d*|R\$[\s]?\d+')

# Commerce page fallback for when help page 404s
_DISNEY_COMMERCE_URL = "https://www.disneyplus.com/en/commerce/plans"


def _disney_wait_for_prices(page, country: str) -> bool:
    """
    Wait for Disney+ pricing page to fully render.

    Handles two page types:
    - Help page (US via country_urls): Salesforce LWR SPA, needs time to render
    - Commerce page (all other countries): React app with async price loading

    For both: detects errors/spinners, retries via reload, verifies price text.
    If help page 404s, falls back to the commerce page.

    Args:
        page: Playwright page object.
        country: ISO alpha-2 country code.

    Returns:
        True (always — best-effort).
    """
    is_help_page = "help.disneyplus.com" in page.url

    if is_help_page:
        return _disney_wait_help_page(page, country)
    else:
        return _disney_wait_commerce_page(page, country)


def _disney_wait_help_page(page, country: str) -> bool:
    """Handle Disney+ help page (Salesforce LWR). Falls back to commerce on 404."""
    # Wait for SPA to render
    _log("Disney+ help: waiting for Salesforce LWR to render...")
    page.wait_for_timeout(6000)

    visible = _get_visible_text(page)

    # Check for 404
    if "can't find the page" in visible.lower() or len(visible) < 1000:
        _log("Disney+ help: got 404, falling back to commerce page")
        try:
            page.goto(_DISNEY_COMMERCE_URL, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(5000)
            return _disney_wait_commerce_page(page, country)
        except Exception as e:
            _log(f"Disney+ help: commerce fallback failed: {e}")
            return True

    if _DISNEY_PRICE_RE.search(visible):
        _log(f"Disney+ help: pricing content found ({len(visible)} chars)")
        _disney_dismiss_cookies(page)
        # Scroll to load all content
        try:
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            page.evaluate("() => window.scrollTo(0, 0)")
        except Exception:
            pass
        return True

    _log(f"Disney+ help: no pricing found ({len(visible)} chars), continuing")
    return True


def _disney_wait_commerce_page(page, country: str) -> bool:
    """Handle Disney+ commerce/plans page with async price loading."""
    max_reloads = 1

    for attempt in range(max_reloads + 1):
        if attempt > 0:
            _log(f"Disney+: reload attempt {attempt}")
            try:
                page.reload(wait_until="networkidle", timeout=30000)
            except Exception as e:
                _log(f"Disney+: reload failed: {e}")
                continue
            page.wait_for_timeout(5000)

        visible = _get_visible_text(page)

        # Check for error page
        if "unexpected error" in visible.lower():
            _log("Disney+: detected error page")
            if attempt < max_reloads:
                continue
            return True

        # Wait for price elements via CSS selectors
        price_found = False
        for sel in [
            '[class*="price"]', '[data-testid*="price"]',
            '[class*="Price"]', '[class*="cost"]',
        ]:
            try:
                page.wait_for_selector(sel, timeout=8000)
                _log(f"Disney+: price element found ({sel})")
                price_found = True
                break
            except Exception:
                continue

        if price_found:
            page.wait_for_timeout(3000)

        visible = _get_visible_text(page)
        if _DISNEY_PRICE_RE.search(visible):
            _log(f"Disney+: pricing text confirmed ({len(visible)} chars)")
            _disney_dismiss_cookies(page)
            return True

        # Extra wait for slow proxy connections
        _log("Disney+: no price text yet, extra wait...")
        page.wait_for_timeout(5000)

        visible = _get_visible_text(page)
        if _DISNEY_PRICE_RE.search(visible):
            _log(f"Disney+: pricing text confirmed after extra wait")
            _disney_dismiss_cookies(page)
            return True

        _log(f"Disney+: still no price text ({len(visible)} chars)")

    _log("Disney+: all attempts exhausted, continuing anyway")
    return True


def _get_visible_text(page) -> str:
    """Safely get visible text from page."""
    try:
        return page.inner_text("body")
    except Exception:
        return ""


def _disney_dismiss_cookies(page) -> None:
    """Try to dismiss cookie consent on Disney+ pages."""
    for selector in [
        'button:has-text("Accept All")',
        'button:has-text("Accept all")',
        'button:has-text("Accepter tout")',
        'button:has-text("Alle akzeptieren")',
        'button:has-text("Accetta tutto")',
        'button:has-text("Aceptar todo")',
        'button:has-text("Aceitar tudo")',
        'button:has-text("Alles accepteren")',
        '#onetrust-accept-btn-handler',
    ]:
        try:
            btn = page.locator(selector)
            if btn.count() > 0:
                btn.first.click(timeout=2000)
                _log(f"Disney+: dismissed cookies ({selector})")
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


# ---------------------------------------------------------------------------
# Zwift region popup dismissal
# ---------------------------------------------------------------------------

def _zwift_region_popup(page, country: str) -> bool:
    """
    Dismiss Zwift's country/region selector overlay.

    Zwift UK (and some other countries) shows a region popup. Try close
    buttons, dismiss buttons, and Escape key.

    Args:
        page: Playwright page object.
        country: ISO alpha-2 country code.

    Returns:
        True (always — popup may not appear).
    """
    # Try close/dismiss buttons
    close_selectors = [
        'button[aria-label="Close"]',
        'button[aria-label="close"]',
        '[class*="close-button"]',
        '[class*="dismiss"]',
        'button:has-text("Stay")',
        'button:has-text("Continue")',
        'button:has-text("OK")',
        '.modal-close',
        '[data-testid="close-button"]',
    ]

    for sel in close_selectors:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                _log(f"Zwift: dismissed region popup ({sel})")
                page.wait_for_timeout(1000)
                return True
        except Exception:
            continue

    # Try Escape key
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        _log("Zwift: pressed Escape for region popup")
    except Exception:
        pass

    return True


# ---------------------------------------------------------------------------
# Canva billing toggle (capture both Monthly and Yearly prices)
# ---------------------------------------------------------------------------

# Multilingual keywords for the Monthly toggle (from archived handler)
_CANVA_MONTHLY_KEYWORDS = [
    "monthly", "month", "mensuel", "monatlich", "mensual", "mensal",
    "mensile", "maandelijks", "月払い", "月額",
]

_CANVA_YEARLY_KEYWORDS = [
    "yearly", "annual", "year", "annuel", "jährlich", "anual",
    "annuale", "jaarlijks", "年払い", "年額",
]


def _canva_toggle_billing(page, country: str) -> bool:
    """
    Capture both Monthly and Yearly prices from Canva's pricing page.

    Canva defaults to the Yearly tab. This interaction:
    1. Reads yearly pricing text from the visible cards via JS
    2. Clicks the Monthly toggle
    3. Waits for the DOM to update with monthly prices
    4. Injects the yearly prices as visible text so the LLM extractor sees both

    Techniques ported from archive/site_handlers/canva.py:
    - Multi-strategy toggle detection (CSS selectors, then JS keyword search)
    - Multilingual keyword matching for button text
    - Fallback: assume first option in a 2-option toggle is Monthly
    """
    _log("Canva: starting billing toggle interaction")

    # Step 1: Read visible pricing text from the Yearly tab (default view)
    yearly_text = _canva_read_visible_prices(page)
    if yearly_text:
        _log(f"Canva: captured yearly pricing text ({len(yearly_text)} chars)")
    else:
        _log("Canva: could not read yearly pricing text")

    # Step 2: Click the Monthly toggle
    toggled = _canva_click_monthly(page)
    if toggled:
        # Wait for prices to update (React/DOM re-render)
        page.wait_for_timeout(2500)
        _log("Canva: toggled to Monthly tab")
    else:
        _log("Canva: could not find Monthly toggle, continuing with default view")

    # Step 3: Inject yearly pricing text at the TOP of the DOM.
    # The page now shows monthly prices natively. The injected yearly text
    # ensures the LLM sees both billing periods. Inserting at the top
    # guarantees the HTML cleaner preserves it (it truncates from the bottom).
    if yearly_text and toggled:
        _canva_inject_text_at_top(page, yearly_text, "Annual/Yearly Billing Prices")

    return True


def _canva_read_visible_prices(page) -> str:
    """
    Read visible pricing text from Canva's pricing cards.

    Uses innerText on the pricing card section to get a clean representation
    of plan names, prices, and descriptions as they appear to a user.
    """
    try:
        text = page.evaluate("""() => {
            // Try to find the pricing cards section specifically
            // Canva wraps pricing cards in a section before "Compare features"
            const sections = document.querySelectorAll('section, [role="main"], main');
            for (const sec of sections) {
                const t = sec.innerText || '';
                // A pricing section should have plan names AND currency symbols
                if (t.includes('Pro') && t.includes('Business') && /[£$€¥₹]/.test(t)) {
                    // Trim to just the pricing cards area (before FAQ/footer)
                    const cutoff = t.indexOf('Compare features');
                    return cutoff > 0 ? t.substring(0, cutoff).trim() : t.substring(0, 3000).trim();
                }
            }
            // Fallback: use body text, trimmed
            const body = document.body.innerText || '';
            const cutoff = body.indexOf('Compare features');
            return cutoff > 0 ? body.substring(0, cutoff).trim() : body.substring(0, 3000).trim();
        }""")
        return text.strip() if text else ""
    except Exception as e:
        _log(f"Canva: error reading visible prices: {e}")
        return ""


def _canva_click_monthly(page) -> bool:
    """
    Click the Monthly toggle on Canva's pricing page.

    Canva uses a <button role="switch" aria-checked="true"> for the billing
    toggle. When aria-checked="true", Yearly is selected. Clicking the switch
    toggles to Monthly (aria-checked="false").

    The "Monthly" text is a <p> label next to the switch — clicking it does
    nothing. We must click the actual <button role="switch">.
    """
    # Strategy 1: Find the billing switch button directly
    # It's a role="switch" near "Monthly"/"Yearly" text
    try:
        handle = page.evaluate_handle("""() => {
            // Find all switch buttons
            const switches = document.querySelectorAll('button[role="switch"]');
            for (const sw of switches) {
                // Check if this switch is near billing-related text
                const parent = sw.closest('div');
                if (!parent) continue;
                const context = parent.textContent.toLowerCase();
                if (context.includes('monthly') || context.includes('yearly') ||
                    context.includes('annual')) {
                    return sw;
                }
            }
            // Broader: any switch with aria-checked="true" near pricing area
            for (const sw of switches) {
                if (sw.getAttribute('aria-checked') === 'true') {
                    return sw;
                }
            }
            return null;
        }""")
        el = handle.as_element()
        if el:
            el.click()
            _log("Canva: clicked billing switch (role=switch)")
            return True
    except Exception as e:
        _log(f"Canva: switch button click failed: {e}")

    # Strategy 2: Playwright locator for the switch
    try:
        locator = page.locator('button[role="switch"]').first
        if locator.count() > 0 and locator.is_visible():
            locator.click()
            _log("Canva: clicked switch via Playwright locator")
            return True
    except Exception:
        pass

    # Strategy 3: Fallback — multilingual keyword search for clickable elements
    monthly_kw_js = ", ".join(f'"{kw}"' for kw in _CANVA_MONTHLY_KEYWORDS)

    try:
        handle = page.evaluate_handle(f"""() => {{
            const monthlyKeywords = [{monthly_kw_js}];
            const candidates = document.querySelectorAll(
                'button, [role="tab"], [role="radio"], [role="switch"], label'
            );
            for (const el of candidates) {{
                const text = (el.textContent || '').toLowerCase().trim();
                if (!text || text.length > 30) continue;
                if (monthlyKeywords.some(kw => text.includes(kw))) {{
                    return el;
                }}
            }}
            return null;
        }}""")
        el = handle.as_element()
        if el:
            el.click()
            _log("Canva: clicked Monthly via keyword fallback")
            return True
    except Exception as e:
        _log(f"Canva: keyword fallback failed: {e}")

    return False


def _canva_inject_text_at_top(page, text: str, label: str) -> None:
    """
    Inject pricing text at the TOP of the DOM.

    Inserting at the top ensures the HTML cleaner preserves it during
    truncation (which cuts from the bottom). The text is wrapped in a
    clearly labeled container so the LLM understands the context.
    """
    try:
        page.evaluate("""(data) => {
            const div = document.createElement('div');
            div.id = 'canva-billing-reference';
            div.style.cssText = 'padding: 16px; margin: 16px; border: 2px solid #7c3aed; background: #faf5ff;';
            div.innerHTML = '<h3>' + data.label + '</h3><pre style="white-space:pre-wrap">' +
                data.text.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</pre>';

            const main = document.querySelector('main') || document.body;
            main.insertBefore(div, main.firstChild);
        }""", {"text": text, "label": label})
        _log("Canva: injected structured price summary into DOM")
    except Exception as e:
        _log(f"Canva: failed to inject price summary: {e}")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    """Log interaction progress to stderr."""
    print(f"[interactions] {msg}", file=sys.stderr)

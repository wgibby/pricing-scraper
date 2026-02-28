"""
Site-specific interaction overrides for the v2 pipeline.

Only 2 sites need post-navigation interactions:
- Netflix: multi-step signup flow (click "Next" to reach plan form)
- Adobe: geo-popup dismissal

Also handles pre-navigation setup (cookie injection before page.goto).

Usage:
    from v2.interactions import pre_navigation_setup, run_interaction
    pre_navigation_setup(context, site_config, country)
    # ... navigate ...
    run_interaction(page, site_config, country)
"""

import sys
import random


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
    "es": ["Siguiente", "Continuar", "Comenzar"],
    "pt": ["Próximo", "Continuar", "Começar"],
    "ja": ["続ける", "次へ", "開始", "始める"],
    "nl": ["Volgende", "Doorgaan", "Aan de slag"],
}

# Step indicators by language
NETFLIX_STEP_PATTERNS = {
    "en": "STEP",
    "de": "SCHRITT",
    "fr": "ÉTAPE",
    "it": "PASSAGGIO",
    "es": "PASO",
    "pt": "PASSO",
    "ja": "ステップ",
    "nl": "STAP",
}


# ---------------------------------------------------------------------------
# Pre-navigation setup
# ---------------------------------------------------------------------------

def pre_navigation_setup(context, site_config: dict, country: str) -> None:
    """
    Inject cookies into the browser context BEFORE page navigation.

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
    """Inject Netflix cookies before navigation."""
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
    else:
        _log(f"Unknown interaction type: {interaction_type}")
        return True


def _netflix_multi_step(page, country: str) -> bool:
    """
    Handle Netflix's multi-step signup flow.

    Detects if we're on a "Step X of Y" page and clicks through
    to the plan selection form.

    Args:
        page: Playwright page object.
        country: ISO alpha-2 country code.

    Returns:
        True if we reached the plan form (or were already there).
    """
    lang = COUNTRY_TO_LANG.get(country.lower(), "en")
    step_pattern = NETFLIX_STEP_PATTERNS.get(lang, "STEP")

    # Check if we're already on the plan form
    page_html = ""
    try:
        page_html = page.content()
    except Exception:
        pass

    # If page has pricing content, we're already there
    pricing_indicators = ["$", "€", "£", "¥", "₹", "R$", "/month", "/mo", "planGrid", "planCard"]
    if any(indicator in page_html for indicator in pricing_indicators):
        _log("Netflix: pricing content detected, already on plan form")
        return True

    # Check for step indicator
    if step_pattern.lower() not in page_html.lower():
        _log("Netflix: no step indicator found, assuming we're on the right page")
        return True

    _log(f"Netflix: step indicator found, attempting click-through (lang={lang})")

    # Try language-specific button texts
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
                    _log(f"Netflix: clicking '{text}' button")
                    btn.click()
                    page.wait_for_timeout(3000)

                    # Verify we moved forward
                    new_html = page.content()
                    if any(ind in new_html for ind in pricing_indicators):
                        _log("Netflix: successfully reached plan form")
                        return True

                    # Might need another click (multi-step)
                    _log("Netflix: clicked but no pricing yet, trying again...")
                    break
            except Exception:
                continue

    # Fallback: try data-uia selectors (Netflix-specific)
    for sel in ['[data-uia="cta-link"]', '[data-uia="action-button"]', 'button[type="submit"]']:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                _log(f"Netflix: clicking fallback selector {sel}")
                btn.click()
                page.wait_for_timeout(3000)

                new_html = page.content()
                if any(ind in new_html for ind in pricing_indicators):
                    _log("Netflix: fallback click reached plan form")
                    return True
        except Exception:
            continue

    # Last resort: direct navigation to planform
    _log("Netflix: button clicks failed, trying direct navigation to /signup/planform")
    try:
        page.goto("https://www.netflix.com/signup/planform", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        _log("Netflix: direct navigation to planform complete")
        return True
    except Exception as e:
        _log(f"Netflix: direct navigation failed: {e}")
        return False


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
# Logging
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    """Log interaction progress to stderr."""
    print(f"[interactions] {msg}", file=sys.stderr)

#!/usr/bin/env python3
"""
Backwards Compatible Enhanced Scraper
Ensures compatibility with existing Netflix and Spotify handlers while adding YouTube enhancements.
"""
import os
import json
import time
import argparse
import random
from datetime import datetime
from playwright.sync_api import sync_playwright

import site_handlers
from enhanced_proxy_utils import get_validated_proxy_for_country, handle_youtube_geo_issues
from proxy_utils import get_proxy_url

# --- COPIED FUNCTIONS FROM modified_scraper.py FOR COMPATIBILITY ---

def load_config():
    """Load the configuration file."""
    with open('config.json', 'r') as f:
        return json.load(f)

def verify_proxy(proxy_url, country):
    """Verify the proxy works using requests."""
    try:
        import requests
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        print(f"  Verifying proxy connection...")
        response = requests.get('https://ipinfo.io/json', proxies=proxies, timeout=30)
        
        if response.status_code == 200:
            ip_data = response.json()
            print(f"  ✓ Proxy verified. IP: {ip_data.get('ip')} ({ip_data.get('country')})")
            return True
        else:
            print(f"  ✗ Proxy verification failed. Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Proxy verification failed: {e}")
        return False

def format_proxy_for_playwright(proxy_url):
    """Convert a requests proxy URL to Playwright format."""
    parts = proxy_url.replace('http://', '')
    auth_part, server_part = parts.split('@')
    username, password = auth_part.split(':')
    
    return {
        "server": f"http://{server_part}",
        "username": username,
        "password": password
    }

def get_browser_args_for_site(site_handler, default_args):
    """Get browser arguments, using site-specific ones if available."""
    if hasattr(site_handler, 'get_stealth_browser_args'):
        stealth_args = site_handler.get_stealth_browser_args()
        print(f"  Using stealth browser args for {site_handler.site_name}")
        return stealth_args
    else:
        return default_args

def create_browser_context(browser, site_handler, country, browser_type="chromium"):
    """Create browser context with appropriate settings."""
    base_settings = {
        "locale": f"{country}-{country.upper()}",
        "ignore_https_errors": True,
        "java_script_enabled": True
    }
    
    if browser_type == "firefox":
        context_settings = {
            **base_settings,
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
            "viewport": {"width": 1920, "height": 1080}
        }
    else:  # chromium
        context_settings = {
            **base_settings,
            "viewport": {"width": 1280, "height": 800}
        }
        
        if site_handler and hasattr(site_handler, 'get_stealth_browser_args'):
            context_settings.update({
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                "viewport": {"width": 1920, "height": 1080},
                "bypass_csp": True,
                "extra_http_headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Cache-Control": "max-age=0",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1"
                }
            })
        else:
            context_settings["user_agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36"
    
    context = browser.new_context(**context_settings)
    print(f"  Created {browser_type} context with appropriate settings")
    return context

def set_language_preferences(context, country):
    """Set strict language preferences for the browser context."""
    language_mapping = {
        "uk": "en-GB",
        "us": "en-US", 
        "de": "de-DE",
        "fr": "fr-FR",
        "jp": "ja-JP",
        "br": "pt-BR",
        "in": "en-IN",
        "ca": "en-CA",
        "au": "en-AU",
        "mx": "es-MX"
    }
    
    language = language_mapping.get(country.lower(), "en-US")
    
    context.set_extra_http_headers({
        "Accept-Language": f"{language},en;q=0.9",
    })
    
    print(f"  Set language preferences: {language}")
    return language

def is_page_valid(page):
    """Check if the page is still accessible."""
    try:
        page.title()
        return True
    except Exception:
        return False

def universal_cookie_handler(page, site_name=""):
    """Universal cookie banner handler that's safer for all sites."""
    print("  Attempting universal cookie banner handling...")
    
    try:
        page.title()
    except Exception:
        print("  Page already invalid, skipping cookie handling")
        return False
    
    # Site-specific gentle handling
    if "netflix" in site_name.lower():
        print("  Using gentle approach for Netflix...")
        try:
            netflix_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                '[data-uia="cookie-disclosure-accept-button"]',
                '.cookie-disclosure button'
            ]
            
            for selector in netflix_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Found Netflix cookie button: {selector}")
                        page.click(selector, timeout=3000)
                        page.wait_for_timeout(500)
                        
                        if is_page_valid(page):
                            return True
                        else:
                            print("  Page became invalid after Netflix cookie click")
                            return False
                except Exception as e:
                    continue
            
            page.evaluate("""() => {
                try {
                    document.cookie = "OptanonAlertBoxClosed=2024-01-01T00:00:00.000Z; path=/; domain=.netflix.com; max-age=31536000";
                    document.cookie = "OptanonConsent=isGpcEnabled=0; path=/; domain=.netflix.com; max-age=31536000";
                } catch(e) {
                    console.log("Netflix cookie setting failed:", e);
                }
            }""")
            return True
            
        except Exception as e:
            print(f"  Netflix cookie handling failed: {e}")
            return False
    
    if "spotify" in site_name.lower():
        print("  Using optimized approach for Spotify...")
        try:
            spotify_selectors = [
                '[data-testid="cookie-notice-accept-button"]',
                'button:has-text("Accept All")',
                'button:has-text("Accept cookies")',
                'button:has-text("Accept")'
            ]
            
            for selector in spotify_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Found Spotify cookie button: {selector}")
                        page.click(selector, timeout=3000)
                        page.wait_for_timeout(500)
                        
                        if is_page_valid(page):
                            return True
                        else:
                            print("  Page became invalid after Spotify cookie click")
                            return False
                except Exception as e:
                    continue
            
            page.evaluate("""() => {
                try {
                    document.cookie = "sp_privacy_settings=all; path=/; domain=.spotify.com; max-age=31536000";
                    document.cookie = "cookieConsent=true; path=/; domain=.spotify.com; max-age=31536000";
                } catch(e) {
                    console.log("Spotify cookie setting failed:", e);
                }
            }""")
            return True
            
        except Exception as e:
            print(f"  Spotify cookie handling failed: {e}")
            return False
    
    # General approach for other sites
    print("  Using general approach for other sites...")
    general_accept_selectors = [
        'button:has-text("Accept")',
        'button:has-text("Accept All")', 
        'button:has-text("Allow all")',
        'button:has-text("I agree")',
        'button:has-text("Allow cookies")',
        '#onetrust-accept-btn-handler',
        '.accept-cookies',
        '.cookie-accept-button',
        '[aria-label="Accept cookies"]'
    ]
    
    for selector in general_accept_selectors:
        try:
            if page.locator(selector).count() > 0:
                print(f"  Found cookie button with selector: {selector}")
                page.click(selector, timeout=3000)
                page.wait_for_timeout(500)
                
                if is_page_valid(page):
                    return True
                else:
                    print(f"  Page became invalid after clicking {selector}")
                    return False
        except Exception as e:
            continue
    
    try:
        page.add_style_tag(content="""
            div[class*="cookie"]:not([class*="essential"]), 
            div[id*="cookie"]:not([id*="essential"]),
            div[class*="consent"]:not([class*="essential"]),
            .cookie-banner, .cookie-notice, #cookie-banner, #cookie-notice {
                opacity: 0 !important;
                pointer-events: none !important;
                z-index: -9999 !important;
            }
            body, html {
                overflow: auto !important;
            }
        """)
        print("  Applied gentle CSS hiding for cookie banners")
    except Exception as e:
        print(f"  Error in CSS hiding: {e}")
    
    return True

def safe_cookie_handling(page, site_handler=None):
    """Safely handle cookies with validation checks."""
    try:
        if not is_page_valid(page):
            print("  Page invalid before cookie handling")
            return False
        
        cookie_handled = False
        if site_handler:
            try:
                print("  Trying site-specific cookie handling...")
                cookie_handled = site_handler.handle_cookie_consent(page)
                
                if not is_page_valid(page):
                    print("  Page became invalid after site-specific cookie handling")
                    return False
                    
            except Exception as e:
                print(f"  Error in site-specific cookie handling: {e}")
        
        if not cookie_handled and is_page_valid(page):
            try:
                print("  Trying universal cookie handling...")
                cookie_handled = universal_cookie_handler(page, site_handler.site_name if site_handler else "")
                
                if not is_page_valid(page):
                    print("  Page became invalid after universal cookie handling")
                    return False
                    
            except Exception as e:
                print(f"  Error in universal cookie handling: {e}")
        
        return cookie_handled
        
    except Exception as e:
        print(f"  Error in safe cookie handling: {e}")
        return False

def force_scroll_past_banners(page):
    """Force scroll to ensure content is visible."""
    try:
        if not is_page_valid(page):
            return False
            
        page.evaluate("window.scrollTo(0, 200)")
        page.wait_for_timeout(500)
        
        page.evaluate("""() => {
            const mainContent = document.querySelector('main, #content, .content, [role="main"]');
            if (mainContent) {
                mainContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                window.scrollTo(0, document.body.scrollHeight * 0.25);
            }
        }""")
        page.wait_for_timeout(1000)
        
        print("  Forced scroll past potential banners")
        return True
    except Exception as e:
        print(f"  Error forcing scroll: {e}")
        return False

def safe_page_interactions(page, site_handler=None):
    """Safely perform page interactions with validation checks."""
    try:
        if not is_page_valid(page):
            print("  Page invalid before interactions")
            return False
        
        try:
            force_scroll_past_banners(page)
            if not is_page_valid(page):
                print("  Page became invalid after scrolling")
                return False
        except Exception as e:
            print(f"  Error in scrolling: {e}")
        
        if site_handler and is_page_valid(page):
            try:
                site_handler.perform_site_interactions(page)
                if not is_page_valid(page):
                    print("  Page became invalid after site interactions")
                    return False
            except Exception as e:
                print(f"  Error in site-specific interactions: {e}")
        
        return True
        
    except Exception as e:
        print(f"  Error in safe page interactions: {e}")
        return False

# --- ENHANCED SCRAPER WITH BACKWARDS COMPATIBILITY ---

def should_use_enhanced_proxy_validation(website_name):
    """Determine if a website needs enhanced proxy validation."""
    geo_sensitive_sites = ['youtube', 'netflix', 'disney', 'hulu', 'prime']
    return website_name.lower() in geo_sensitive_sites

def launch_browser_with_site_specific_handling(p, proxy_config, site_handler, country, website_name):
    """Launch browser with site-specific handling for compatibility."""
    
    # Special handling for Netflix (force Firefox)
    if website_name.lower() in ["netflix", "adobe"]:
        print("  Netflix detected - forcing Firefox browser...")
        try:
            firefox_args = ["--width=1920", "--height=1080", "--new-instance", "--private-window"]
            
            if site_handler and hasattr(site_handler, 'get_firefox_args'):
                firefox_args = site_handler.get_firefox_args()
            
            if proxy_config:
                browser = p.firefox.launch(
                    headless=True,
                    proxy=proxy_config,
                    args=firefox_args,
                    timeout=60000
                )
            else:
                browser = p.firefox.launch(
                    headless=True,
                    args=firefox_args,
                    timeout=60000
                )
            
            context = create_browser_context(browser, site_handler, country, browser_type="firefox")
            return browser, context, "firefox"
            
        except Exception as e:
            print(f"  ✗ Firefox launch failed for Netflix: {e}")
            return None, None, None
    
    # Special handling for YouTube (prefer Firefox for geo-handling)
    elif website_name.lower() == "youtube":
        print("  YouTube detected - using enhanced geo-handling...")
        try:
            # Try Firefox first for YouTube
            firefox_args = ["--width=1920", "--height=1080", "--new-instance"]
            
            if site_handler and hasattr(site_handler, 'get_firefox_args'):
                firefox_args = site_handler.get_firefox_args()
            
            if proxy_config:
                browser = p.firefox.launch(
                    headless=True,
                    proxy=proxy_config,
                    args=firefox_args,
                    timeout=60000
                )
            else:
                browser = p.firefox.launch(
                    headless=True,
                    args=firefox_args,
                    timeout=60000
                )
            
            context = create_browser_context(browser, site_handler, country, browser_type="firefox")
            return browser, context, "firefox"
            
        except Exception as e:
            print(f"  Firefox launch failed for YouTube: {e}, trying Chromium...")
            # Fall through to normal browser launch
    
    # Normal browser launch with fallback (for Spotify and others)
    default_args = [
        "--disable-extensions",
        "--disable-gpu", 
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ]
    
    # Try Chromium first
    try:
        print("  Attempting Chromium launch...")
        
        browser_args = get_browser_args_for_site(site_handler, default_args)
        
        if proxy_config:
            browser = p.chromium.launch(
                headless=True,
                proxy=proxy_config,
                args=browser_args,
                timeout=60000
            )
        else:
            browser = p.chromium.launch(
                headless=True,
                args=browser_args,
                timeout=60000
            )
        
        context = create_browser_context(browser, site_handler, country, browser_type="chromium")
        print("  ✓ Chromium launched successfully")
        return browser, context, "chromium"
        
    except Exception as chromium_error:
        print(f"  ✗ Chromium launch failed: {chromium_error}")
        print("  Falling back to Firefox...")
        
        try:
            firefox_args = ["--width=1920", "--height=1080"]
            
            if site_handler and hasattr(site_handler, 'get_firefox_args'):
                firefox_args = site_handler.get_firefox_args()
            
            if proxy_config:
                browser = p.firefox.launch(
                    headless=True,
                    proxy=proxy_config,
                    args=firefox_args,
                    timeout=60000
                )
            else:
                browser = p.firefox.launch(
                    headless=True,
                    args=firefox_args,
                    timeout=60000
                )
            
            context = create_browser_context(browser, site_handler, country, browser_type="firefox")
            print("  ✓ Firefox launched successfully")
            return browser, context, "firefox"
            
        except Exception as firefox_error:
            print(f"  ✗ Firefox launch also failed: {firefox_error}")
            return None, None, None

def take_screenshots_enhanced_compatible(website_filter=None, country_filter=None, save_html=True):
    """Enhanced screenshot function with full backwards compatibility."""
    
    print(f"Starting enhanced scraper with filters: website='{website_filter}', country='{country_filter}'")
    
    config = load_config()
    
    # Create output directories
    screenshots_dir = os.path.join(config['output_dir'], datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(screenshots_dir, exist_ok=True)
    
    logs_dir = os.path.join(screenshots_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    if save_html:
        html_dir = os.path.join(screenshots_dir, "html")
        os.makedirs(html_dir, exist_ok=True)
    
    # Filter websites
    websites = config['websites']
    if website_filter:
        websites = [w for w in websites if w['name'].lower() == website_filter.lower()]
        if not websites:
            print(f"No website found with name: {website_filter}")
            return
    
    for website in websites:
        website_name = website['name']
        print(f"\nProcessing {website_name}...")
        
        # Get site handler
        site_handler = site_handlers.get_handler(website_name)
        if not site_handler:
            print(f"  No specific handler found for {website_name}")
        else:
            print(f"  Using handler: {site_handler.__class__.__name__}")
        
        # Filter countries
        countries = website['countries']
        if country_filter:
            if country_filter.lower() in [c.lower() for c in countries]:
                countries = [country_filter.lower()]
            else:
                print(f"  Website {website_name} doesn't have country: {country_filter}")
                continue
        
        for country in countries:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(logs_dir, f"{website_name.lower()}_{country}_{timestamp}.log")
            
            try:
                print(f"\n  Processing {country.upper()}...")
                
                # Determine proxy strategy based on site
                use_proxy = country.lower() != 'us'
                proxy_config = None
                proxy_validation = None
                
                if use_proxy:
                    print(f"    Getting proxy for {country.upper()}...")
                    
                    # Enhanced validation for geo-sensitive sites
                    if should_use_enhanced_proxy_validation(website_name):
                        print(f"    Using enhanced proxy validation for {website_name}")
                        proxy_url, proxy_validation = get_validated_proxy_for_country(country, max_proxy_attempts=2)
                        
                        if not proxy_url:
                            print(f"    ✗ Could not get validated proxy for {country} - skipping")
                            continue
                        
                        if not proxy_validation['geo_accurate']:
                            print(f"    ⚠️ Proxy geo-accuracy issue:")
                            print(f"      Expected: {country}")
                            print(f"      Detected: {proxy_validation['detected_country']}")
                            print(f"    Proceeding anyway...")
                    else:
                        # Standard proxy validation for compatible sites
                        print(f"    Using standard proxy validation for {website_name}")
                        proxy_url = get_proxy_url(country)
                        if not proxy_url or not verify_proxy(proxy_url, country):
                            print(f"    ✗ Standard proxy validation failed for {country} - skipping")
                            continue
                    
                    proxy_config = format_proxy_for_playwright(proxy_url)
                    print(f"    ✓ Using proxy: {proxy_config['server']}")
                else:
                    print(f"    Using direct connection for {country.upper()}")
                
                # Log setup
                with open(log_file, 'w') as log:
                    log.write(f"Processing {website_name} for {country.upper()} at {datetime.now().isoformat()}\n")
                    if proxy_config:
                        log.write(f"Proxy: {proxy_config['server']}\n")
                        if proxy_validation:
                            log.write(f"Enhanced validation: {proxy_validation}\n")
                    else:
                        log.write("Direct connection\n")
                    log.write("\n")
                
                # Launch browser with site-specific handling
                with sync_playwright() as p:
                    browser, context, browser_type = launch_browser_with_site_specific_handling(
                        p, proxy_config, site_handler, country, website_name
                    )
                    
                    if not browser or not context:
                        print(f"    ✗ Browser launch failed - skipping")
                        continue
                    
                    print(f"    Using {browser_type.upper()} browser")
                    
                    # Set language preferences
                    set_language_preferences(context, country)
                    
                    # Site-specific context preparation
                    if site_handler:
                        try:
                            site_handler.prepare_context(context, country)
                        except Exception as e:
                            print(f"    Error in context preparation: {e}")
                    
                    # Create page
                    page = context.new_page()
                    page.set_default_navigation_timeout(60000)
                    page.set_default_timeout(60000)
                    
                    # Get URL
                    if site_handler:
                        url = site_handler.get_url(country)
                    else:
                        url = website['url']
                        if '{country}' in url:
                            url = url.replace('{country}', country.lower())
                    
                    print(f"    Navigating to: {url}")
                    
                    try:
                        # Navigate
                        page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        
                        try:
                            page.wait_for_selector("body", timeout=30000)
                        except:
                            print(f"    Warning: Timeout waiting for body")
                        
                        # YouTube-specific geo-issue handling
                        if website_name.lower() == "youtube":
                            print(f"    Checking for YouTube geo-issues...")
                            geo_handled = handle_youtube_geo_issues(page, country)
                            if not geo_handled:
                                print(f"    ⚠️ Geo-issues detected but couldn't resolve completely")
                        
                        if not is_page_valid(page):
                            print(f"    ✗ Page became invalid after navigation")
                            continue
                        
                        print(f"    ✓ Page loaded successfully")
                        
                        # Cookie handling
                        if not safe_cookie_handling(page, site_handler):
                            print(f"    Cookie handling had issues, continuing...")
                        
                        if is_page_valid(page):
                            page.wait_for_timeout(2000)
                        
                        # Page interactions
                        if is_page_valid(page):
                            if not safe_page_interactions(page, site_handler):
                                print(f"    Page interactions had issues, continuing...")
                        
                        if is_page_valid(page):
                            page.wait_for_timeout(3000)
                        
                        # Extract data if page is valid
                        if is_page_valid(page):
                            # Screenshot
                            screenshot_path = os.path.join(
                                screenshots_dir,
                                f"{website_name.lower()}_{country}_{timestamp}.png"
                            )
                            
                            page.screenshot(path=screenshot_path, full_page=True)
                            print(f"    ✓ Screenshot saved")
                            
                            # HTML
                            html_path = None
                            if save_html:
                                try:
                                    html_content = page.content()
                                    html_path = os.path.join(html_dir, f"{website_name.lower()}_{country}_{timestamp}.html")
                                    with open(html_path, 'w', encoding='utf-8') as f:
                                        f.write(html_content)
                                    print(f"    ✓ HTML saved")
                                except Exception as e:
                                    print(f"    Error saving HTML: {e}")
                            
                            # Pricing extraction
                            extracted_pricing = None
                            if site_handler and is_page_valid(page):
                                try:
                                    extracted_pricing = site_handler.extract_pricing_data(page)
                                    print(f"    ✓ Pricing data extracted")
                                except Exception as e:
                                    print(f"    Error extracting pricing: {e}")
                            
                            # Save results
                            result = {
                                "website": website_name,
                                "country": country,
                                "timestamp": datetime.now().isoformat(),
                                "scrape_successful": True,
                                "target_url": url,
                                "final_url": page.url,
                                "pricing_data": extracted_pricing if extracted_pricing else {"error": "No pricing data extracted"},
                                "files": {
                                    "screenshot": screenshot_path,
                                    "html": html_path
                                },
                                "scrape_details": {
                                    "used_proxy": proxy_config is not None,
                                    "proxy_country": country if proxy_config else "direct",
                                    "enhanced_validation": proxy_validation is not None,
                                    "proxy_validation": proxy_validation,
                                    "handler_used": site_handler.__class__.__name__ if site_handler else "default",
                                    "browser_used": browser_type,
                                    "page_title": page.title() if is_page_valid(page) else "Page Invalid"
                                }
                            }
                            
                            result_path = os.path.join(
                                screenshots_dir,
                                f"{website_name.lower()}_{country}_{timestamp}_result.json"
                            )
                            
                            with open(result_path, 'w', encoding='utf-8') as f:
                                json.dump(result, f, indent=2)
                            
                            print(f"    ✓ Result saved")
                            
                            # Cleanup
                            if site_handler and is_page_valid(page):
                                try:
                                    site_handler.clean_up(page)
                                except Exception as e:
                                    print(f"    Error in cleanup: {e}")
                            
                            print(f"    ✓ Successfully completed {website_name} for {country}")
                        else:
                            print(f"    ✗ Page invalid - cannot extract data")
                    
                    except Exception as e:
                        print(f"    ✗ Error during scraping: {e}")
                        
                        try:
                            if is_page_valid(page):
                                error_screenshot = os.path.join(
                                    screenshots_dir,
                                    f"{website_name.lower()}_{country}_error_{timestamp}.png"
                                )
                                page.screenshot(path=error_screenshot)
                                print(f"    Error screenshot saved")
                        except:
                            pass
                    
                    # Always close browser
                    browser.close()
                    print(f"    Browser closed")
                
            except Exception as outer_e:
                print(f"  ✗ Fatal error: {outer_e}")
                with open(log_file, 'a') as log:
                    log.write(f"Fatal error: {outer_e}\n")
            
            # Wait between countries
            time.sleep(5)

def main():
    """Main entry point with backwards compatibility."""
    parser = argparse.ArgumentParser(description="Enhanced pricing scraper with backwards compatibility")
    parser.add_argument("--website", type=str, help="Filter to specific website")
    parser.add_argument("--country", type=str, help="Filter to specific country")
    parser.add_argument("--no-html", action="store_true", help="Skip HTML saving")
    
    args = parser.parse_args()
    
    print("Enhanced Pricing Scraper (Backwards Compatible)")
    print("=" * 50)
    print("Features:")
    print("- Enhanced YouTube geo-validation")
    print("- Netflix Firefox compatibility")
    print("- Spotify stealth mode preserved")
    print("- Backwards compatible with existing handlers")
    print()
    
    take_screenshots_enhanced_compatible(
        website_filter=args.website,
        country_filter=args.country,
        save_html=not args.no_html
    )

if __name__ == "__main__":
    main()
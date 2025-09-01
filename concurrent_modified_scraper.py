#!/usr/bin/env python3
"""
Enhanced Concurrent Pricing Scraper
Adds concurrent processing capabilities while maintaining backwards compatibility.
"""
import os
import json
import time
import argparse
import random
from datetime import datetime
from playwright.sync_api import sync_playwright
import concurrent.futures
import threading
from typing import List, Optional, Dict, Any

import site_handlers
from proxy_utils import get_proxy_url
from enhanced_proxy_utils import get_validated_proxy_for_country

# Thread-safe printing
print_lock = threading.Lock()

def thread_safe_print(*args, **kwargs):
    """Thread-safe printing function."""
    with print_lock:
        print(*args, **kwargs)

def should_use_enhanced_proxy_validation(website_name):
    """Determine if a website needs enhanced proxy validation."""
    geo_sensitive_sites = ['youtube', 'netflix', 'disney', 'hulu', 'prime']
    return website_name.lower() in geo_sensitive_sites

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
        
        thread_safe_print(f"  Verifying proxy connection for {country.upper()}...")
        response = requests.get('https://ipinfo.io/json', proxies=proxies, timeout=30)
        
        if response.status_code == 200:
            ip_data = response.json()
            thread_safe_print(f"  ✓ Proxy verified for {country.upper()}. IP: {ip_data.get('ip')} ({ip_data.get('country')})")
            return True
        else:
            thread_safe_print(f"  ✗ Proxy verification failed for {country.upper()}. Status: {response.status_code}")
            return False
    except Exception as e:
        thread_safe_print(f"  ✗ Proxy verification failed for {country.upper()}: {e}")
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
        thread_safe_print(f"  Using stealth browser args for {site_handler.site_name}")
        return stealth_args
    else:
        return default_args

def is_page_valid(page):
    """Check if page is still valid."""
    try:
        return page and not page.is_closed()
    except:
        return False

def safe_cookie_handling(page, site_handler):
    """Enhanced cookie handling with multiple strategies."""
    try:
        if not is_page_valid(page):
            return False
        
        # Wait a bit for any popups to appear
        page.wait_for_timeout(1500)
        
        if not is_page_valid(page):
            return False
        
        # Strategy 1: Check for common cookie consent patterns and handle them
        cookie_selectors = [
            'button:has-text("Accept")',
            'button:has-text("Allow all cookies")',
            'button:has-text("Accept all")',
            'button:has-text("OK")',
            '[data-testid="cookie-banner"] button',
            '.cookie-banner button',
            '#cookie-banner button',
            'button[id*="cookie"]',
            'button[class*="cookie"]'
        ]
        
        for selector in cookie_selectors:
            try:
                if page.locator(selector).count() > 0:
                    thread_safe_print(f"    Found cookie button: {selector}")
                    page.locator(selector).first.click(timeout=2000)
                    page.wait_for_timeout(1000)
                    thread_safe_print(f"    ✓ Clicked cookie consent button")
                    break
            except Exception as e:
                # Continue to next selector
                continue
        
        # Strategy 2: Use site handler if available
        if site_handler and hasattr(site_handler, 'handle_cookie_consent'):
            try:
                thread_safe_print(f"    Using site-specific cookie handling...")
                site_handler.handle_cookie_consent(page)
                if not is_page_valid(page):
                    thread_safe_print(f"    Page became invalid after site cookie handling")
                    return False
            except Exception as e:
                thread_safe_print(f"    Site cookie handling failed: {e}")
        
        # Strategy 3: Try to dismiss any remaining overlays by pressing Escape
        try:
            page.keyboard.press('Escape')
            page.wait_for_timeout(500)
        except:
            pass
        
        return True
        
    except Exception as e:
        thread_safe_print(f"    Error in enhanced cookie handling: {e}")
        return False

def safe_page_interactions(page, site_handler):
    """Enhanced page interactions with better error protection and timing."""
    try:
        if not is_page_valid(page):
            thread_safe_print("    Page invalid before interactions")
            return False
        
        # Add more wait time for page to fully stabilize
        page.wait_for_timeout(2000)
        
        if not is_page_valid(page):
            thread_safe_print("    Page became invalid during stabilization")
            return False
        
        # Check if page is still loading
        try:
            page.wait_for_load_state('networkidle', timeout=10000)
        except:
            # Continue anyway if networkidle times out
            pass
        
        if not is_page_valid(page):
            thread_safe_print("    Page became invalid after network idle")
            return False
        
        if site_handler and is_page_valid(page):
            try:
                thread_safe_print(f"    Performing {site_handler.site_name} site interactions...")
                
                # Add retry logic for site interactions
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        site_handler.perform_site_interactions(page)
                        thread_safe_print(f"    ✓ Site interactions completed successfully")
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            thread_safe_print(f"    Site interaction attempt {attempt + 1} failed, retrying: {e}")
                            page.wait_for_timeout(1000)
                            if not is_page_valid(page):
                                thread_safe_print("    Page became invalid during retry")
                                return False
                        else:
                            thread_safe_print(f"    All site interaction attempts failed: {e}")
                            # Don't return False - continue with screenshot even if interactions fail
                
                if not is_page_valid(page):
                    thread_safe_print("    Page became invalid after site interactions")
                    return False
                    
            except Exception as e:
                thread_safe_print(f"    Error in site-specific interactions: {e}")
                # Don't return False - continue anyway
        
        # Final stability check
        page.wait_for_timeout(1000)
        return is_page_valid(page)
        
    except Exception as e:
        thread_safe_print(f"    Error in safe page interactions: {e}")
        return False

def process_single_country(website_name: str, website_config: dict, country: str, 
                          site_handler, screenshots_dir: str, logs_dir: str, 
                          html_dir: str = None, save_html: bool = True) -> dict:
    """
    Process a single country for a website. This function runs in its own thread.
    
    Returns:
        dict: Result summary with success status and any error messages
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"{website_name.lower()}_{country}_{timestamp}.log")
    
    result = {
        "website": website_name,
        "country": country,
        "success": False,
        "error": None,
        "timestamp": timestamp,
        "files_created": []
    }
    
    try:
        thread_safe_print(f"\n  [THREAD] Processing {country.upper()} for {website_name}...")
        
        # Determine proxy strategy
        use_proxy = country.lower() != 'us'
        proxy_config = None

        if use_proxy:
            thread_safe_print(f"    Getting proxy for {country.upper()}...")
            
            # Enhanced validation for geo-sensitive sites like Adobe
            if should_use_enhanced_proxy_validation(website_name):
                thread_safe_print(f"    Using enhanced proxy validation for {website_name}")
                proxy_url, proxy_validation = get_validated_proxy_for_country(country, max_proxy_attempts=2)
                
                if not proxy_url:
                    result["error"] = f"Could not get validated proxy for {country}"
                    thread_safe_print(f"    ✗ {result['error']}")
                    return result
                
                if not proxy_validation['geo_accurate']:
                    thread_safe_print(f"    ⚠️ Proxy geo-accuracy issue:")
                    thread_safe_print(f"      Expected: {country}")
                    thread_safe_print(f"      Detected: {proxy_validation['detected_country']}")
                    thread_safe_print(f"    Proceeding anyway...")
            else:
                # Standard proxy validation for other sites
                thread_safe_print(f"    Using standard proxy validation for {website_name}")
                proxy_url = get_proxy_url(country)
                
                if not proxy_url:
                    result["error"] = f"No proxy available for {country}"
                    thread_safe_print(f"    ✗ {result['error']}")
                    return result
                
                if not verify_proxy(proxy_url, country):
                    result["error"] = f"Proxy verification failed for {country}"
                    thread_safe_print(f"    ✗ {result['error']}")
                    return result
            
            proxy_config = format_proxy_for_playwright(proxy_url)
            thread_safe_print(f"    ✓ Using proxy: {proxy_config['server']}")


        # Build URL - handle different URL patterns
        url = website_config['url']
        if '{country}' in url:
            # Explicit country placeholder in config
            url = url.format(country=country)
        elif country.lower() != 'us':
            # Check if this is a site that uses geo-IP detection instead of URL paths
            # Sites like Figma, Netflix, etc. use the same URL but detect location via IP
            geo_ip_sites = ['figma', 'netflix', 'disney', 'hulu', 'spotify', 'adobe']
            website_name_lower = website_name.lower()
            
            uses_geo_ip = any(site in website_name_lower for site in geo_ip_sites)
            
            if uses_geo_ip:
                # Keep the same URL, rely on proxy IP for geo-detection
                thread_safe_print(f"    Using geo-IP detection for {website_name} (same URL, different IP)")
                # url stays the same
            else:
                # Try common patterns for country-specific URLs
                base_url = url.rstrip('/')
                url = f"{base_url}/{country}/"
        
        thread_safe_print(f"    Navigating to: {url}")
        
        # Launch browser
        with sync_playwright() as p:
            try:
                # Get browser arguments
                default_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security"
                ]
                
                browser_args = get_browser_args_for_site(site_handler, default_args)
                
                # Launch browser with more conservative settings
                launch_args = browser_args.copy()
                
                # Add memory optimization flags for concurrent execution
                launch_args.extend([
                    "--memory-pressure-off",
                    "--max_old_space_size=512",  # Limit memory per browser
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows"
                ])
                use_firefox = website_name.lower() in ["netflix", "adobe"]

                if use_firefox:
                    thread_safe_print(f"    {website_name} detected - forcing Firefox browser...")
                    try:
                        # Get Firefox-specific args if site handler provides them
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
                        thread_safe_print(f"    ✓ Firefox launched successfully for {website_name}")
                        
                    except Exception as e:
                        result["error"] = f"Firefox launch failed for {website_name}: {e}"
                        thread_safe_print(f"    ✗ {result['error']}")
                        return result
                        
                else:
                    # Original Chromium launch logic
                    if proxy_config:
                        browser = p.chromium.launch(
                            headless=True,
                            proxy=proxy_config,
                            args=launch_args,
                            timeout=60000
                        )
                    else:
                        browser = p.chromium.launch(
                            headless=True,
                            args=launch_args,
                            timeout=60000
                        )
                    thread_safe_print(f"    ✓ Chromium launched successfully for {website_name}")
                
                # Create context with resource limits
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    java_script_enabled=True,
                    bypass_csp=True  # Help with some sites
                )
                
                # Add random delay between countries to reduce proxy contention
                import random
                startup_delay = random.uniform(0.5, 2.0)  # Random delay 0.5-2 seconds
                time.sleep(startup_delay)

                if site_handler and hasattr(site_handler, 'prepare_context'):
                    try:
                        site_handler.prepare_context(context, country)
                        thread_safe_print(f"    ✓ Site context prepared for {country.upper()}")
                    except Exception as e:
                        thread_safe_print(f"    Site context preparation failed: {e}")
                
                page = context.new_page()
                
                # Navigate to URL with retry logic
                max_nav_retries = 2
                navigation_success = False
                
                for nav_attempt in range(max_nav_retries):
                    try:
                        page.goto(url, wait_until='networkidle', timeout=45000)  # Reduced timeout
                        navigation_success = True
                        thread_safe_print(f"    ✓ Page loaded for {country.upper()}")
                        break
                    except Exception as nav_e:
                        if nav_attempt < max_nav_retries - 1:
                            thread_safe_print(f"    Navigation attempt {nav_attempt + 1} failed for {country.upper()}, retrying: {nav_e}")
                            page.wait_for_timeout(2000)
                        else:
                            thread_safe_print(f"    ✗ All navigation attempts failed for {country.upper()}: {nav_e}")
                
                if not navigation_success:
                    result["error"] = f"Failed to navigate to {url} for {country}"
                    return result
                
                # Enhanced cookie handling
                if not safe_cookie_handling(page, site_handler):
                    thread_safe_print(f"    Cookie handling had issues for {country.upper()}, continuing...")
                
                # Wait for page to stabilize after cookie handling
                if is_page_valid(page):
                    page.wait_for_timeout(3000)
                
                # Page interactions with enhanced error handling
                if is_page_valid(page):
                    if not safe_page_interactions(page, site_handler):
                        thread_safe_print(f"    Page interactions had issues for {country.upper()}, continuing...")
                
                # Final wait before screenshot
                if is_page_valid(page):
                    page.wait_for_timeout(2000)
                
                # Extract data if page is valid
                if is_page_valid(page):
                    # Screenshot
                    screenshot_path = os.path.join(
                        screenshots_dir,
                        f"{website_name.lower()}_{country}_{timestamp}.png"
                    )
                    
                    page.screenshot(path=screenshot_path, full_page=True)
                    result["files_created"].append(screenshot_path)
                    thread_safe_print(f"    ✓ Screenshot saved for {country.upper()}")
                    
                    # HTML output temporarily disabled to keep files clean
                    # TODO: Re-enable if HTML content becomes useful for analysis
                    # 
                    # if save_html and html_dir:
                    #     try:
                    #         html_content = page.content()
                    #         html_path = os.path.join(html_dir, f"{website_name.lower()}_{country}_{timestamp}.html")
                    #         with open(html_path, 'w', encoding='utf-8') as f:
                    #             f.write(html_content)
                    #         result["files_created"].append(html_path)
                    #         thread_safe_print(f"    ✓ HTML saved for {country.upper()}")
                    #     except Exception as e:
                    #         thread_safe_print(f"    Error saving HTML for {country.upper()}: {e}")
                    
                    # JSON output temporarily disabled to keep files clean
                    # TODO: Re-enable when pricing data extraction is standardized
                    # 
                    # # Extract pricing data using site handler
                    # pricing_data = None
                    # if site_handler and hasattr(site_handler, 'extract_pricing_data'):
                    #     try:
                    #         pricing_data = site_handler.extract_pricing_data(page)
                    #         thread_safe_print(f"    ✓ Pricing data extracted for {country.upper()}")
                    #     except Exception as e:
                    #         thread_safe_print(f"    Error extracting pricing data for {country.upper()}: {e}")
                    # 
                    # # Save result data
                    # extraction_result = {
                    #     "website": website_name,
                    #     "country": country,
                    #     "url": url,
                    #     "timestamp": timestamp,
                    #     "pricing_data": pricing_data,
                    #     "screenshot_path": screenshot_path,
                    #     "html_path": html_path if save_html and html_dir else None
                    # }
                    # 
                    # result_path = os.path.join(
                    #     screenshots_dir,
                    #     f"{website_name.lower()}_{country}_{timestamp}_result.json"
                    # )
                    # 
                    # with open(result_path, 'w', encoding='utf-8') as f:
                    #     json.dump(extraction_result, f, indent=2)
                    # 
                    # result["files_created"].append(result_path)
                    # thread_safe_print(f"    ✓ Result saved for {country.upper()}")
                    
                    # Cleanup
                    if site_handler and is_page_valid(page):
                        try:
                            site_handler.clean_up(page)
                        except Exception as e:
                            thread_safe_print(f"    Error in cleanup for {country.upper()}: {e}")
                    
                    result["success"] = True
                    thread_safe_print(f"    ✓ Successfully completed {website_name} for {country.upper()}")
                else:
                    result["error"] = f"Page invalid for {country} - cannot extract data"
                    thread_safe_print(f"    ✗ {result['error']}")
                
                browser.close()
                
            except Exception as e:
                result["error"] = f"Error during scraping for {country}: {e}"
                thread_safe_print(f"    ✗ {result['error']}")
                
                try:
                    if 'page' in locals() and is_page_valid(page):
                        error_screenshot = os.path.join(
                            screenshots_dir,
                            f"{website_name.lower()}_{country}_error_{timestamp}.png"
                        )
                        page.screenshot(path=error_screenshot)
                        result["files_created"].append(error_screenshot)
                        thread_safe_print(f"    Error screenshot saved for {country.upper()}")
                except:
                    pass
                
                if 'browser' in locals():
                    try:
                        browser.close()
                    except:
                        pass
                
    except Exception as outer_e:
        result["error"] = f"Fatal error for {country}: {outer_e}"
        thread_safe_print(f"  ✗ {result['error']}")
        with open(log_file, 'w') as log:
            log.write(f"Fatal error: {outer_e}\n")
    
    return result

def take_screenshots_concurrent(website_filter=None, country_filter=None, 
                               countries_list=None, save_html=False, max_workers=None):
    """
    Enhanced screenshot function with concurrent processing capabilities.
    
    Args:
        website_filter: Filter to specific website
        country_filter: Filter to specific country (overrides countries_list)
        countries_list: List of specific countries to process (e.g., ['br', 'nl', 'de'])
        save_html: Whether to save HTML content
        max_workers: Maximum number of concurrent threads (defaults to min(16GB RAM optimized, country count))
    """
    thread_safe_print(f"Starting concurrent scraper with filters: website='{website_filter}', country='{country_filter}', countries_list='{countries_list}'")
    
    config = load_config()
    
    # Create output directories
    screenshots_dir = os.path.join(config['output_dir'], datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(screenshots_dir, exist_ok=True)
    
    logs_dir = os.path.join(screenshots_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # HTML directory creation disabled since HTML output is commented out
    # html_dir = None
    # if save_html:
    #     html_dir = os.path.join(screenshots_dir, "html")
    #     os.makedirs(html_dir, exist_ok=True)
    
    # Filter websites
    websites = config['websites']
    if website_filter:
        websites = [w for w in websites if w['name'].lower() == website_filter.lower()]
        if not websites:
            thread_safe_print(f"No website found with name: {website_filter}")
            return
    
    total_results = []
    
    for website in websites:
        website_name = website['name']
        thread_safe_print(f"\nProcessing {website_name}...")
        
        # Get site handler
        site_handler = site_handlers.get_handler(website_name)
        if not site_handler:
            thread_safe_print(f"  No specific handler found for {website_name}")
        else:
            thread_safe_print(f"  Using handler: {site_handler.__class__.__name__}")
        
        # Determine countries to process
        countries = website['countries']
        
        # Apply country filtering logic
        if country_filter:
            # Single country filter takes precedence
            if country_filter.lower() in [c.lower() for c in countries]:
                countries = [country_filter.lower()]
            else:
                thread_safe_print(f"  Website {website_name} doesn't have country: {country_filter}")
                continue
        elif countries_list:
            # Filter to specific list of countries
            available_countries = [c.lower() for c in countries]
            requested_countries = [c.lower() for c in countries_list]
            countries = [c for c in requested_countries if c in available_countries]
            
            if not countries:
                thread_safe_print(f"  Website {website_name} doesn't have any of the requested countries: {countries_list}")
                continue
            else:
                thread_safe_print(f"  Processing countries: {countries}")
        
        # Determine optimal number of workers
        if max_workers is None:
            # More conservative for better reliability - reduce concurrent browsers
            # Based on your Mac Mini 16GB RAM and proxy stability
            optimal_workers = min(3, len(countries))  # Reduced from 6 to 3 for stability
        else:
            optimal_workers = min(max_workers, len(countries))
        
        thread_safe_print(f"  Using {optimal_workers} concurrent workers for {len(countries)} countries")
        
        # Process countries concurrently with staggered start times
        with concurrent.futures.ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            # Submit tasks with small delays to reduce startup contention
            future_to_country = {}
            for i, country in enumerate(countries):
                # Add small delay between thread starts to reduce resource contention
                if i > 0:
                    time.sleep(0.5)  # 500ms stagger between thread starts
                
                future = executor.submit(
                    process_single_country,
                    website_name, website, country, site_handler, 
                    screenshots_dir, logs_dir, None, False  # HTML disabled
                )
                future_to_country[future] = country
            
            # Collect results as they complete
            website_results = []
            for future in concurrent.futures.as_completed(future_to_country):
                country = future_to_country[future]
                try:
                    result = future.result()
                    website_results.append(result)
                    
                    if result["success"]:
                        thread_safe_print(f"  ✓ Completed {country.upper()} successfully")
                    else:
                        thread_safe_print(f"  ✗ Failed {country.upper()}: {result['error']}")
                        
                except Exception as exc:
                    error_result = {
                        "website": website_name,
                        "country": country,
                        "success": False,
                        "error": f"Thread execution failed: {exc}",
                        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                        "files_created": []
                    }
                    website_results.append(error_result)
                    thread_safe_print(f"  ✗ Thread failed for {country.upper()}: {exc}")
            
            total_results.extend(website_results)
        
        # Summary for this website
        successful = sum(1 for r in website_results if r["success"])
        total_countries = len(website_results)
        thread_safe_print(f"\n  {website_name} Summary: {successful}/{total_countries} countries completed successfully")
        
        # Brief pause between websites to be respectful
        if len(websites) > 1:
            thread_safe_print("  Waiting 5 seconds before next website...")
            time.sleep(5)
    
    # Final summary
    total_successful = sum(1 for r in total_results if r["success"])
    total_attempted = len(total_results)
    
    thread_safe_print(f"\n" + "="*50)
    thread_safe_print(f"CONCURRENT SCRAPING COMPLETED")
    thread_safe_print(f"Total: {total_successful}/{total_attempted} tasks completed successfully")
    
    if total_attempted > total_successful:
        thread_safe_print(f"\nFailed tasks:")
        for result in total_results:
            if not result["success"]:
                thread_safe_print(f"  - {result['website']} ({result['country']}): {result['error']}")
    
    thread_safe_print(f"\nResults saved to: {screenshots_dir}")
    
    return total_results

def main():
    """Main entry point with enhanced concurrent capabilities."""
    parser = argparse.ArgumentParser(description="Enhanced concurrent pricing scraper")
    parser.add_argument("--website", type=str, help="Filter to specific website")
    parser.add_argument("--country", type=str, help="Filter to specific country")
    parser.add_argument("--countries", type=str, help="Comma-separated list of specific countries (e.g., 'br,nl,de')")
    parser.add_argument("--no-html", action="store_true", help="Skip HTML saving")
    parser.add_argument("--max-workers", type=int, help="Maximum number of concurrent workers")
    parser.add_argument("--sequential", action="store_true", help="Force sequential processing (original behavior)")
    
    args = parser.parse_args()
    
    # Parse countries list if provided
    countries_list = None
    if args.countries:
        countries_list = [c.strip().lower() for c in args.countries.split(',')]
    
    print("Enhanced Concurrent Pricing Scraper")
    print("=" * 50)
    
    if args.sequential:
        print("Running in SEQUENTIAL mode (original behavior)")
        # Call original function - you'd need to implement this or import from the original file
        # For now, we'll call the concurrent version with max_workers=1
        take_screenshots_concurrent(
            website_filter=args.website,
            country_filter=args.country,
            countries_list=countries_list,
            save_html=False,  # HTML disabled
            max_workers=1
        )
    else:
        print("Running in CONCURRENT mode")
        print("Features:")
        print("- Concurrent country processing")
        print("- Optimized for 16GB RAM")
        print("- Thread-safe logging")
        print("- Backwards compatible with existing handlers")
        print()
        
        if args.countries:
            print(f"📍 Specific countries: {countries_list}")
        if args.max_workers:
            print(f"👥 Max workers: {args.max_workers}")
        else:
            print(f"👥 Max workers: Auto (optimized for 16GB RAM)")
        print()
        
        take_screenshots_concurrent(
            website_filter=args.website,
            country_filter=args.country,
            countries_list=countries_list,
            save_html=False,  # HTML disabled
            max_workers=args.max_workers
        )

if __name__ == "__main__":
    main()
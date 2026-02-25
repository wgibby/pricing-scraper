#!/usr/bin/env python3
"""
Simple test script for Canva pricing scraper.
Tests the Canva handler in isolation to debug issues.
"""
import time
from playwright.sync_api import sync_playwright
from site_handlers.canva import CanvaHandler

def test_canva():
    """Test Canva scraping with detailed debugging."""
    print("Starting Canva test...")

    handler = CanvaHandler()
    url = handler.get_url('us')

    print(f"URL: {url}")
    print(f"Detection level: {handler.detection_level}")

    with sync_playwright() as p:
        print("\nLaunching Firefox browser...")

        # Get Firefox args
        firefox_args = handler.get_firefox_args()
        print(f"Firefox args: {len(firefox_args)} arguments")

        try:
            browser = p.firefox.launch(
                headless=True,  # Run in headless mode for scraping
                args=firefox_args,
                timeout=60000
            )
            print("✓ Firefox browser launched")

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                java_script_enabled=True,
                bypass_csp=True
            )
            print("✓ Context created")

            # Prepare context with stealth
            handler.prepare_context(context, 'us')
            print("✓ Context prepared")

            page = context.new_page()
            print("✓ Page created")

            print(f"\nNavigating to {url}...")
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            print("✓ Navigation complete")

            # Wait to see the page
            print("\nWaiting 5 seconds to observe page...")
            time.sleep(5)

            # Check page title
            title = page.title()
            print(f"Page title: {title}")

            # Handle cookies
            print("\nHandling cookies...")
            handler.handle_cookie_consent(page)

            # Perform interactions
            print("\nPerforming site interactions...")
            handler.perform_site_interactions(page)

            # Extract pricing
            print("\nExtracting pricing data...")
            pricing_data = handler.extract_pricing_data(page)

            print("\n" + "="*50)
            print("PRICING DATA:")
            print("="*50)
            import json
            print(json.dumps(pricing_data, indent=2))

            # Take screenshot
            print("\nTaking screenshot...")
            page.screenshot(path="canva_test_screenshot.png", full_page=True)
            print("✓ Screenshot saved to canva_test_screenshot.png")

            # Keep browser open for observation
            print("\nKeeping browser open for 10 seconds for observation...")
            time.sleep(10)

            browser.close()
            print("\n✓ Test completed successfully")

        except Exception as e:
            print(f"\n✗ Error during test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_canva()

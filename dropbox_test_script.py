#!/usr/bin/env python3
"""
Test script for Dropbox handler.
Tests the Dropbox scraper with US market to verify functionality.
"""
import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

# Import the Dropbox handler
from site_handlers.dropbox import DropboxHandler

def test_dropbox_scraper():
    """Test the Dropbox scraper with US market."""
    print("\n" + "="*60)
    print("DROPBOX SCRAPER TEST")
    print("="*60 + "\n")

    # Create handler
    handler = DropboxHandler()
    print(f"✓ Created handler: {handler.__class__.__name__}")
    print(f"  Detection level: {handler.detection_level}")

    # Get URL
    url = handler.get_url('us')
    print(f"✓ URL: {url}")

    # Create output directory
    screenshots_dir = os.path.join("screenshots", datetime.now().strftime("%Y-%m-%d"), "test")
    os.makedirs(screenshots_dir, exist_ok=True)
    print(f"✓ Screenshots dir: {screenshots_dir}")

    # Launch browser and scrape
    print("\nLaunching browser...")
    with sync_playwright() as p:
        try:
            # Get browser args
            browser_args = handler.get_stealth_browser_args()
            print(f"  Browser args: {browser_args}")

            # Launch Chromium
            browser = p.chromium.launch(
                headless=True,
                args=browser_args
            )
            print("  ✓ Browser launched")

            # Create context
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            # Prepare context
            handler.prepare_context(context, 'us')

            # Create page
            page = context.new_page()
            print(f"  Navigating to: {url}")

            # Navigate
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            print("  ✓ Page loaded")

            # Handle cookie consent
            handler.handle_cookie_consent(page)

            # Perform site interactions
            handler.perform_site_interactions(page)

            # Take screenshot
            screenshot_path = os.path.join(screenshots_dir, f"dropbox_us_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"\n✓ Screenshot saved: {screenshot_path}")

            # Extract pricing data
            pricing_data = handler.extract_pricing_data(page)

            print("\n" + "="*60)
            print("RESULTS")
            print("="*60)
            print(f"\nSite: {pricing_data.get('site')}")
            print(f"URL: {pricing_data.get('url')}")
            print(f"\nPlans found: {len(pricing_data.get('plans', []))}")

            for plan in pricing_data.get('plans', []):
                print(f"\n--- {plan.get('name')} ---")
                if 'price' in plan:
                    print(f"  Price: {plan['price'].get('display')}")
                if 'period' in plan:
                    print(f"  Period: {plan.get('period')}")
                if 'per_user' in plan:
                    print(f"  Per user: {plan.get('per_user')}")
                if 'storage' in plan:
                    print(f"  Storage: {plan.get('storage')}")
                if 'features' in plan and plan['features']:
                    print(f"  Features: {len(plan['features'])} features")
                    for i, feature in enumerate(plan['features'][:3], 1):
                        print(f"    {i}. {feature[:80]}...")

            # Close browser
            browser.close()
            print("\n✓ Browser closed")
            print("\n" + "="*60)
            print("TEST COMPLETED SUCCESSFULLY")
            print("="*60 + "\n")

            return True

        except Exception as e:
            print(f"\n✗ Error during test: {e}")
            import traceback
            traceback.print_exc()

            if 'browser' in locals():
                browser.close()

            return False

if __name__ == "__main__":
    success = test_dropbox_scraper()
    sys.exit(0 if success else 1)

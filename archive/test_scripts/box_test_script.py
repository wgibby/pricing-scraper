#!/usr/bin/env python3
"""
Box handler test script - Debug pricing section detection
"""
import time
from playwright.sync_api import sync_playwright

def test_box_pricing():
    """Test Box pricing page structure and selectors."""

    with sync_playwright() as p:
        # Launch Firefox (Box uses Firefox)
        browser = p.firefox.launch(
            headless=False,  # Non-headless to see what's happening
            args=["--width=1920", "--height=1080"]
        )

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        page = context.new_page()

        print("Navigating to Box pricing page...")
        page.goto("https://www.box.com/plans/individual", wait_until='networkidle')

        print("Page loaded, waiting for content...")
        time.sleep(3)

        # Inspect page structure
        print("\n=== PAGE STRUCTURE ANALYSIS ===")

        # Check URL
        print(f"Current URL: {page.url}")

        # Check for pricing toggle
        print("\n--- Pricing Toggle Detection ---")
        toggle_info = page.evaluate("""() => {
            const results = [];

            // Check for toggle button
            const toggleBtn = document.querySelector('button.pricing-toggle-button');
            if (toggleBtn) {
                results.push('Found: button.pricing-toggle-button');
            }

            // Check for checkbox
            const checkbox = document.querySelector('#pricing-toggle-checkbox');
            if (checkbox) {
                results.push(`Found: #pricing-toggle-checkbox (checked: ${checkbox.checked})`);
            }

            // Check for Monthly/Annual text
            const buttons = Array.from(document.querySelectorAll('button'));
            const monthlyBtn = buttons.find(b => b.textContent.includes('Monthly'));
            const annualBtn = buttons.find(b => b.textContent.includes('Annual'));

            if (monthlyBtn) results.push(`Found Monthly button: ${monthlyBtn.className}`);
            if (annualBtn) results.push(`Found Annual button: ${annualBtn.className}`);

            return results;
        }""")

        for info in toggle_info:
            print(f"  {info}")

        # Check for pricing cards
        print("\n--- Pricing Cards Detection ---")
        cards_info = page.evaluate("""() => {
            const results = [];

            // Try various selectors for pricing cards
            const selectors = [
                '.pricing-card',
                '.pricing-cards',
                '.plan-card',
                '[class*="pricing"]',
                '[class*="plan"]',
                '[data-testid*="pricing"]',
                '[data-testid*="plan"]'
            ];

            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                if (elements.length > 0) {
                    results.push(`${selector}: Found ${elements.length} elements`);
                }
            }

            // Check for price text
            const pricePattern = /\$\d+/;
            const allText = document.body.innerText;
            const prices = allText.match(/\$\d+(?:\.\d{2})?/g);
            if (prices) {
                results.push(`Found ${prices.length} price indicators: ${prices.slice(0, 5).join(', ')}`);
            }

            return results;
        }""")

        for info in cards_info:
            print(f"  {info}")

        # Get page title and main headings
        print("\n--- Page Content ---")
        page_info = page.evaluate("""() => {
            const title = document.title;
            const h1s = Array.from(document.querySelectorAll('h1')).map(h => h.textContent.trim());
            const h2s = Array.from(document.querySelectorAll('h2')).map(h => h.textContent.trim()).slice(0, 5);

            return { title, h1s, h2s };
        }""")

        print(f"  Title: {page_info['title']}")
        print(f"  H1s: {page_info['h1s']}")
        print(f"  H2s: {page_info['h2s'][:3]}")

        # Scroll test
        print("\n--- Scroll Test ---")
        print("Scrolling down to find pricing...")

        for scroll_amount in [500, 1000, 1500, 2000]:
            page.evaluate(f"window.scrollTo(0, {scroll_amount})")
            time.sleep(1)

            pricing_visible = page.evaluate("""() => {
                const viewport = {
                    top: window.scrollY,
                    bottom: window.scrollY + window.innerHeight
                };

                // Check if pricing toggle is in viewport
                const toggle = document.querySelector('button.pricing-toggle-button') ||
                              document.querySelector('#pricing-toggle-checkbox');

                if (toggle) {
                    const rect = toggle.getBoundingClientRect();
                    const elemTop = rect.top + window.scrollY;
                    const isVisible = elemTop >= viewport.top && elemTop <= viewport.bottom;
                    return { found: true, visible: isVisible, scrollY: window.scrollY };
                }

                return { found: false, scrollY: window.scrollY };
            }""")

            if pricing_visible['found']:
                print(f"  Scroll {scroll_amount}px: Pricing toggle FOUND, Visible: {pricing_visible['visible']}")
                if pricing_visible['visible']:
                    print(f"  ✓ Pricing toggle is visible at scroll position {scroll_amount}px")
                    break
            else:
                print(f"  Scroll {scroll_amount}px: Pricing toggle not found yet")

        # Take a screenshot
        print("\n--- Taking Screenshot ---")
        screenshot_path = "./screenshots/2025-10-08/box_debug_test.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"  Screenshot saved: {screenshot_path}")

        # Keep browser open for manual inspection
        print("\nBrowser will stay open for 10 seconds for manual inspection...")
        time.sleep(10)

        browser.close()
        print("\n✓ Test completed")

if __name__ == "__main__":
    test_box_pricing()

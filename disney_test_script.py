#!/usr/bin/env python3
"""
Quick test script for Disney+ France and India issues.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import time
import json

def test_disney_country(country_code):
    """Test Disney+ access for a specific country."""
    print(f"\n🧪 TESTING DISNEY+ FOR {country_code.upper()}")
    print("=" * 50)
    
    # Country-specific settings
    settings = {
        'fr': {
            'urls': [
                "https://www.disneyplus.com/fr-fr/welcome",
                "https://aide.disneyplus.com/article/disneyplus-tarif", 
                "https://help.disneyplus.com/article/disneyplus-price"
            ],
            'language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'expected_text': ['disney', 'prix', 'abonnement', 'plan', '€']
        },
        'in': {
            'urls': [
                "https://www.hotstar.com/in/subscribe",
                "https://www.hotstar.com/in/my-account/subscription",
                "https://help.hotstar.com/in/articles/214207163006365"
            ],
            'language': 'hi-IN,en-IN;q=0.9,en;q=0.8',
            'expected_text': ['hotstar', 'subscription', 'plan', 'price', '₹']
        }
    }
    
    if country_code not in settings:
        print(f"❌ No test settings for {country_code}")
        return
    
    config = settings[country_code]
    
    with sync_playwright() as p:
        try:
            # Launch with stealth settings
            browser = p.chromium.launch(
                headless=False,  # Visible for debugging
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--exclude-switches=enable-automation",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-web-security",
                    "--window-size=1920,1080"
                ]
            )
            
            context = browser.new_context(
                locale=config['language'].split(',')[0],
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept-Language": config['language'],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                }
            )
            
            # Add stealth script
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['""" + config['language'].split(',')[0] + """', 'en']
                });
                
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """)
            
            page = context.new_page()
            
            # Test each URL
            for i, url in enumerate(config['urls']):
                print(f"\n📍 Testing URL {i+1}: {url}")
                
                try:
                    # Navigate with timeout
                    page.goto(url, timeout=30000, wait_until="networkidle")
                    time.sleep(3)
                    
                    # Get page info
                    current_url = page.url
                    title = page.title()
                    content = page.evaluate("() => document.body.textContent.toLowerCase()")
                    
                    print(f"   ✅ Page loaded: {title}")
                    print(f"   🔗 Final URL: {current_url}")
                    
                    # Check for expected content
                    found_indicators = []
                    for indicator in config['expected_text']:
                        if indicator in content:
                            found_indicators.append(indicator)
                    
                    print(f"   🔍 Found indicators: {found_indicators}")
                    
                    # Check for blocking indicators
                    blocking_indicators = ['unavailable', 'not available', 'blocked', 'restricted']
                    blocked = any(block in content for block in blocking_indicators)
                    
                    if blocked:
                        print(f"   ⚠️  Page appears blocked/unavailable")
                    
                    # Look for pricing
                    pricing_found = bool(content and (
                        '€' in content or '$' in content or '₹' in content or
                        'price' in content or 'prix' in content or 'plan' in content
                    ))
                    
                    print(f"   💰 Pricing content detected: {pricing_found}")
                    
                    # Save screenshot for analysis
                    screenshot_path = f"disney_test_{country_code}_{i+1}.png"
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f"   📸 Screenshot saved: {screenshot_path}")
                    
                    # If this URL works well, we're done
                    if found_indicators and not blocked and pricing_found:
                        print(f"   ✅ SUCCESS: This URL works well for {country_code}")
                        break
                    
                except Exception as e:
                    print(f"   ❌ Failed: {e}")
                    continue
            
            browser.close()
            
        except Exception as e:
            print(f"❌ Browser setup failed: {e}")

def main():
    """Run tests for both France and India."""
    print("🐭 DISNEY+ COUNTRY ACCESS TESTER")
    print("=" * 50)
    
    countries = ['fr', 'in']
    
    for country in countries:
        test_disney_country(country)
        time.sleep(2)  # Brief pause between tests
    
    print(f"\n✅ Testing complete! Check the generated screenshots.")
    print(f"📋 Summary:")
    print(f"   - Screenshots saved for analysis")
    print(f"   - Use the working URLs in your enhanced handler")
    print(f"   - Look for patterns in successful vs blocked pages")

if __name__ == "__main__":
    main()
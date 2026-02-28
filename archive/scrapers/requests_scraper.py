# requests_scraper.py - ENHANCED
import os
import json
import time
import requests
import argparse
import random
import asyncio
from pyppeteer import launch
import pyppeteer_stealth
from datetime import datetime
from proxy_utils import get_proxy_url
from bs4 import BeautifulSoup

def load_config():
    """Load the configuration file."""
    with open('config.json', 'r') as f:
        return json.load(f)

def get_content_with_proxy(url, country, max_retries=3):
    """
    Retrieve web content using proxy for a specific country.
    With enhanced content validation and encoding handling.
    """
    proxy_url = get_proxy_url(country)
    if not proxy_url:
        print(f"  No proxy available for {country}")
        return False, None, None, None
    
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    # Rotate between different user agents to avoid detection
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
    ]
    
    # Country-specific language headers
    lang_map = {
        'us': 'en-US,en;q=0.9',
        'uk': 'en-GB,en;q=0.9',
        'de': 'de-DE,de;q=0.9,en;q=0.8',
        'fr': 'fr-FR,fr;q=0.9,en;q=0.8',
        'jp': 'ja-JP,ja;q=0.9,en;q=0.8',
        'au': 'en-AU,en;q=0.9',
        'ca': 'en-CA,en;q=0.9',
        'br': 'pt-BR,pt;q=0.9,en;q=0.8',
        'in': 'en-IN,en;q=0.9,hi;q=0.8'
    }
    
    accept_language = lang_map.get(country, 'en-US,en;q=0.9')
    
    for attempt in range(max_retries):
        try:
            # Enhanced headers to appear more like a real browser
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': accept_language,
                'Accept-Encoding': 'gzip, deflate, br',  # Explicitly support compression
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'no-cache',  # Try to bypass caching
                'Pragma': 'no-cache',
                'DNT': '1'
            }
            
            print(f"  Fetching {url} via {country.upper()} proxy (attempt {attempt+1}/{max_retries})...")
            
            # Use a session to maintain cookies and other state
            session = requests.Session()
            
            # First make a HEAD request to check content type
            try:
                head_response = session.head(
                    url, 
                    proxies=proxies, 
                    headers=headers, 
                    timeout=30,
                    allow_redirects=True
                )
                print(f"  HEAD request status: {head_response.status_code}")
                
                # Check if we're getting an actual HTML page
                content_type = head_response.headers.get('Content-Type', '')
                if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                    print(f"  Warning: Content-Type is {content_type}, not HTML")
                    # But continue anyway, as the HEAD response might be misleading
            except Exception as head_err:
                print(f"  HEAD request failed: {head_err}")
                # Continue with GET request anyway
            
            # Now make the actual GET request
            response = session.get(
                url, 
                proxies=proxies, 
                headers=headers, 
                timeout=45,
                allow_redirects=True,
                stream=True  # Stream the response to handle large responses
            )
            
            # Get detailed response info
            content_type = response.headers.get('Content-Type', 'unknown')
            content_encoding = response.headers.get('Content-Encoding', 'none')
            
            print(f"  Response headers: Status={response.status_code}, Content-Type={content_type}, Encoding={content_encoding}")
            
            # Check if we got a proper response
            if response.status_code == 200:
                # Try to get the content
                try:
                    # Check the content-type and handle different types
                    if 'text/html' in content_type or 'application/xhtml+xml' in content_type:
                        # This is likely HTML content
                        if content_encoding.lower() == 'br':
                            # Explicitly handle Brotli compression
                            try:
                                import brotli
                                raw_content = response.content  # Get raw bytes
                                content = brotli.decompress(raw_content).decode('utf-8')
                                print("  Successfully decompressed Brotli content")
                            except ImportError:
                                print("  Brotli module not available, using response.text")
                                content = response.text
                            except Exception as e:
                                print(f"  Error decompressing Brotli content: {e}")
                                content = response.text
                        else:
                            content = response.text
                    elif 'application/json' in content_type:
                        # JSON response - might be API or error
                        content = response.text
                        print(f"  Got JSON response: {content[:100]}...")
                    else:
                        # For other content types, try to decode as text
                        content = response.text
                        print(f"  Warning: Unexpected content type, trying to decode as text")
                    
                    # Validate the content
                    if content and len(content) > 500:
                        # Check if content looks like HTML
                        if '<html' in content.lower() and '<body' in content.lower():
                            print(f"  Content appears to be valid HTML ({len(content)} bytes)")
                            # Check for common anti-bot challenges
                            if "captcha" in content.lower():
                                print(f"  ⚠️ Detected CAPTCHA challenge in response")
                                save_error_response(content, url, country, "captcha")
                                if attempt < max_retries - 1:
                                    wait_time = (attempt + 1) * 5
                                    print(f"  Waiting {wait_time} seconds before retrying...")
                                    time.sleep(wait_time)
                                    continue
                            elif "cloudflare" in content.lower() and "challenge" in content.lower():
                                print(f"  ⚠️ Detected Cloudflare challenge in response")
                                save_error_response(content, url, country, "cloudflare")
                                if attempt < max_retries - 1:
                                    wait_time = (attempt + 1) * 5
                                    print(f"  Waiting {wait_time} seconds before retrying...")
                                    time.sleep(wait_time)
                                    continue
                            elif "id=\"px-captcha\"" in content.lower() or "poweredbyperimeter" in content.lower():
                                print(f"  ⚠️ Detected PerimeterX/HUMAN challenge in response")
                                save_error_response(content, url, country, "perimeterx")
                                if attempt < max_retries - 1:
                                    wait_time = (attempt + 1) * 5
                                    print(f"  Waiting {wait_time} seconds before retrying...")
                                    time.sleep(wait_time)
                                    continue
                            # Check for non-ASCII content (could be binary/encoded)
                            elif not is_valid_text(content):
                                print(f"  ⚠️ Content appears to be encoded or binary data")
                                save_error_response(content, url, country, "binary")
                                if attempt < max_retries - 1:
                                    wait_time = (attempt + 1) * 3
                                    print(f"  Waiting {wait_time} seconds before retrying...")
                                    time.sleep(wait_time)
                                    continue
                            else:
                                print(f"  Valid HTML content retrieved!")
                                return True, content, response.status_code, response
                        else:
                            print(f"  Content doesn't appear to be valid HTML")
                            save_error_response(content, url, country, "not_html")
                    else:
                        print(f"  Empty or very short content received: {len(content) if content else 0} bytes")
                except Exception as content_err:
                    print(f"  Error processing response content: {content_err}")
            else:
                print(f"  Received error status code: {response.status_code}")
            
            # If we got here, the request failed in some way
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"  Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            
        except Exception as e:
            print(f"  Error fetching {url} (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"  Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
    
    return False, None, None, None

def is_valid_text(content, sample_size=1000):
    """
    Check if content appears to be valid text (not binary or encrypted).
    
    Args:
        content: The content to check
        sample_size: Number of characters to check
        
    Returns:
        bool: True if content appears to be valid text
    """
    # Check a sample of the content
    sample = content[:sample_size]
    
    # Count printable ASCII characters
    printable_count = sum(1 for c in sample if c.isprintable() and ord(c) < 128)
    
    # If more than 90% is printable ASCII, it's probably valid text
    return (printable_count / len(sample)) > 0.9 if sample else False

def save_error_response(content, url, country, error_type):
    """
    Save error responses for debugging.
    
    Args:
        content: The response content
        url: The URL that was accessed
        country: The country proxy used
        error_type: Type of error encountered
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"error_{country}_{error_type}_{timestamp}.txt"
    
    try:
        os.makedirs('errors', exist_ok=True)
        with open(f"errors/{filename}", 'w', encoding='utf-8', errors='ignore') as f:
            f.write(f"URL: {url}\n")
            f.write(f"Country: {country}\n")
            f.write(f"Error Type: {error_type}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n")
            f.write(content)
        print(f"  Saved error response to errors/{filename}")
    except Exception as e:
        print(f"  Error saving error response: {e}")

# This function handles sites that need stealth browsing
async def get_content_with_puppeteer_stealth_async(url, country):
    """
    Enhanced Puppeteer stealth function with challenge handling.
    """
    # Get proxy URL - same as before
    proxy_url = get_proxy_url(country)
    if not proxy_url:
        print(f"  No proxy available for {country}")
        return False, None, None
    
    # Parse proxy details - same as before
    proxy_parts = proxy_url.replace('http://', '').split('@')
    if len(proxy_parts) != 2:
        print(f"  Invalid proxy URL format: {proxy_url}")
        return False, None, None
    
    proxy_auth = proxy_parts[0].split(':')
    proxy_server = proxy_parts[1]
    
    if len(proxy_auth) != 2:
        print(f"  Invalid proxy authentication format: {proxy_parts[0]}")
        return False, None, None
    
    print(f"  Using enhanced Puppeteer stealth with proxy for {country.upper()}")
    
    try:
        # Launch browser with proxy - enhanced arguments
        browser = await launch({
            'headless': True,  # You can set to False to see what's happening
            'args': [
                f'--proxy-server=http://{proxy_server}',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--window-size=1920,1080',
                '--start-maximized'
            ]
        })
        
        # Create a browser context for better isolation
        context = await browser.createIncognitoBrowserContext()
        
        # Create page
        page = await context.newPage()
        
        # Set proxy authentication
        await page.authenticate({
            'username': proxy_auth[0],
            'password': proxy_auth[1]
        })
        
        # Apply stealth plugin with additional options
        await pyppeteer_stealth.stealth(page)
        
        # Set viewport and user agent - more realistic settings
        await page.setViewport({'width': 1920, 'height': 1080})
        
        # Use a more modern user agent
        await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36")
        
        # Set extra headers to look more like a browser
        await page.setExtraHTTPHeaders({
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1'
        })
        
        # Additional JavaScript to make detection harder
        await page.evaluateOnNewDocument('''() => {
            // Overwrite navigator properties to make detection harder
            const newProto = navigator.__proto__;
            delete newProto.webdriver;
            navigator.__proto__ = newProto;
            
            // Add languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-GB', 'en-US', 'en'],
            });
            
            // Add plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: 'application/pdf'},
                        description: 'Portable Document Format',
                        filename: 'internal-pdf-viewer',
                        length: 1,
                        name: 'Chrome PDF Plugin'
                    },
                    {
                        0: {type: 'application/pdf'},
                        description: 'Portable Document Format',
                        filename: 'internal-pdf-viewer',
                        length: 1,
                        name: 'Chrome PDF Viewer'
                    },
                    {
                        0: {type: 'application/x-shockwave-flash'},
                        description: 'Shockwave Flash',
                        filename: 'internal-flash-player',
                        length: 1,
                        name: 'Shockwave Flash'
                    }
                ],
            });
        }''')
        
        # First try visiting the homepage
        print(f"  First visiting the homepage...")
        await page.goto('https://www.canva.com/', {
            'waitUntil': 'networkidle0',
            'timeout': 60000
        })
        
        # Try to find and click the accept cookies button if it exists
        try:
            await page.waitForSelector('button[data-testid="cookie-accept-button"]', {'timeout': 5000})
            await page.click('button[data-testid="cookie-accept-button"]')
            print("  Accepted cookies")
            await asyncio.sleep(1)
        except:
            print("  No cookie dialog found or couldn't interact with it")
        
        # Simulate human-like behavior
        await asyncio.sleep(random.uniform(2, 4))
        
        # Perform random mouse movements (helps bypass bot detection)
        for _ in range(3):
            await page.mouse.move(
                random.randint(100, 800),
                random.randint(100, 600)
            )
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Scroll down a bit
        await page.evaluate("""
        () => {
            window.scrollBy({
                top: 400,
                behavior: 'smooth'
            });
        }
        """)
        await asyncio.sleep(random.uniform(1, 2))
        
        # Find pricing link on homepage
        try:
            pricing_links = await page.querySelectorAll('a[href*="pricing"]')
            if pricing_links:
                print("  Found pricing link on homepage, clicking it")
                await pricing_links[0].click()
                await page.waitForNavigation({'waitUntil': 'networkidle0', 'timeout': 30000})
            else:
                # Directly navigate to pricing page
                print(f"  Navigating directly to {url}...")
                await page.goto(url, {
                    'waitUntil': 'networkidle0',
                    'timeout': 60000
                })
        except Exception as e:
            print(f"  Error finding pricing link: {e}")
            # Directly navigate to pricing page as fallback
            print(f"  Navigating directly to {url}...")
            await page.goto(url, {
                'waitUntil': 'networkidle0',
                'timeout': 60000
            })
        
        # Check if we're on a challenge page and wait for it
        challenge_detected = False
        max_challenge_wait = 60  # Maximum seconds to wait for challenge
        
        for _ in range(max_challenge_wait):
            current_url = page.url
            current_content = await page.content()
            
            # Check for challenge indicators
            if "checking your connection" in current_content.lower() or "ray id" in current_content.lower():
                challenge_detected = True
                print(f"  Challenge page detected ({_ + 1}/{max_challenge_wait}s), waiting...")
                
                # Take screenshot every 10 seconds during challenge
                if _ % 10 == 0:
                    os.makedirs("screenshots", exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = f"screenshots/canva_challenge_{country}_{timestamp}.png"
                    await page.screenshot({'path': screenshot_path})
                    print(f"  Took challenge screenshot: {screenshot_path}")
                
                # Move mouse slightly to simulate human
                await page.mouse.move(
                    random.randint(100, 800),
                    random.randint(100, 600)
                )
                
                await asyncio.sleep(1)
            else:
                # If we were on a challenge page and now we're not, we've passed it
                if challenge_detected:
                    print("  Challenge appears to be completed!")
                break
        
        # Check if we still have a challenge page
        current_content = await page.content()
        if "checking your connection" in current_content.lower() or "ray id" in current_content.lower():
            print("  Still on challenge page after maximum wait time")
            
            # Try alternative approach - sometimes going back to homepage then to pricing works
            print("  Trying alternative approach - going back to homepage")
            await page.goto('https://www.canva.com/', {
                'waitUntil': 'networkidle0',
                'timeout': 30000
            })
            
            await asyncio.sleep(3)
            
            # Try to find pricing in top navigation
            try:
                # Try several selectors that might match the pricing link
                selectors = [
                    'a[href*="pricing"]',
                    '.navbar a[href*="pricing"]',
                    'a[data-testid*="pricing"]',
                    'a:has-text("Pricing")',
                    'a:has-text("pricing")'
                ]
                
                for selector in selectors:
                    pricing_links = await page.querySelectorAll(selector)
                    if pricing_links and len(pricing_links) > 0:
                        print(f"  Found pricing link with selector: {selector}, clicking it")
                        await pricing_links[0].click()
                        await page.waitForNavigation({'waitUntil': 'networkidle0', 'timeout': 30000})
                        break
            except Exception as e:
                print(f"  Error finding pricing link in navigation: {e}")
        
        # Final check and get content
        current_url = page.url
        content = await page.content()
        
        # Take a screenshot of the final page
        os.makedirs("screenshots", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshots/canva_final_{country}_{timestamp}.png"
        await page.screenshot({'path': screenshot_path, 'fullPage': True})
        print(f"  Took final screenshot: {screenshot_path}")
        
        # Close browser
        await browser.close()
        
        # Validate content
        if content and len(content) > 1000:
            # Check if we got to a proper page and not challenge page
            if "checking your connection" not in content.lower() and "ray id" not in content.lower():
                print(f"  Successfully retrieved content with enhanced Puppeteer stealth!")
                return True, current_url, content
            else:
                print(f"  Still on challenge page, couldn't bypass")
                return False, None, None
        else:
            print(f"  Retrieved empty or very short content")
            return False, None, None
            
    except Exception as e:
        print(f"  Error with enhanced Puppeteer stealth: {e}")
        try:
            if 'browser' in locals() and browser:
                await browser.close()
        except:
            pass
        return False, None, None

# Synchronous wrapper function to use in your existing code
def get_content_with_puppeteer_stealth(url, country):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(get_content_with_puppeteer_stealth_async(url, country))

def try_urls_with_fallback(website, country, max_total_attempts=10):
    """
    Try different URL patterns with fallbacks.
    
    Args:
        website: Website configuration dictionary
        country: Country code
        max_total_attempts: Maximum total URL attempts (to prevent infinite loops)
    
    Returns:
        tuple: (success, url_used, content)
    """
    url = website['url']
    total_attempts = 0  # Track total attempts across all URLs
    
    # Try the country-specific URL first
    if '{country}' in url and total_attempts < max_total_attempts:
        total_attempts += 1
        country_url = url.replace('{country}', country)
        print(f"  Trying country-specific URL: {country_url}")
        success, content, status, _ = get_content_with_proxy(country_url, country)
        if success and status == 200 and content and len(content) > 1000:
            if is_valid_text(content):
                print(f"  Successfully loaded country-specific URL")
                return True, country_url, content
    
    # Try without country code
    if total_attempts < max_total_attempts:
        total_attempts += 1
        if '{country}' in url:
            base_url = url.replace('/{country}', '').replace('{country}', '')
        else:
            base_url = url
        
        print(f"  Trying base URL: {base_url}")
        success, content, status, _ = get_content_with_proxy(base_url, country)
        if success and status == 200 and content and len(content) > 1000:
            if is_valid_text(content):
                print(f"  Successfully loaded base URL")
                return True, base_url, content
    
    # Try fallback URLs from config
    fallback_urls = website.get('fallback_urls', [])
    for fallback_url in fallback_urls:
        if total_attempts >= max_total_attempts:
            break
        
        total_attempts += 1
        print(f"  Trying fallback URL: {fallback_url}")
        success, content, status, _ = get_content_with_proxy(fallback_url, country)
        if success and status == 200 and content and len(content) > 1000:
            if is_valid_text(content):
                print(f"  Successfully loaded fallback URL")
                return True, fallback_url, content
    
    # Try with language code
    if '{country}' in url and total_attempts < max_total_attempts:
        total_attempts += 1
        lang_mapping = {
            "us": "en-us",
            "uk": "en-gb",
            "de": "de",
            "fr": "fr",
            "jp": "ja",
            "in": "en-in",
            "br": "pt-br",
            "ca": "en-ca",
            "au": "en-au"
        }
        
        if country in lang_mapping:
            lang_url = url.replace('{country}', lang_mapping[country])
            print(f"  Trying language-specific URL: {lang_url}")
            success, content, status, _ = get_content_with_proxy(lang_url, country)
            if success and status == 200 and content and len(content) > 1000:
                if is_valid_text(content):
                    print(f"  Successfully loaded language-specific URL")
                    return True, lang_url, content
    
    # Try common base URLs as a last resort
    website_name = website['name'].lower()
    common_urls = [
        f"https://www.{website_name}.com",
        f"https://{website_name}.com",
        f"https://www.{website_name}.io",
        f"https://{website_name}.io",
    ]
    
    common_paths = [
        "/pricing",
        "/plans",
        "/premium",
        "/subscription",
    ]
    
    # Try common combinations, but respect the maximum attempts limit
    for common_url in common_urls:
        if total_attempts >= max_total_attempts:
            break
            
        for path in common_paths:
            if total_attempts >= max_total_attempts:
                break
                
            total_attempts += 1
            full_url = f"{common_url}{path}"
            print(f"  Trying common URL: {full_url}")
            success, content, status, _ = get_content_with_proxy(full_url, country)
            if success and status == 200 and content and len(content) > 1000:
                if is_valid_text(content):
                    print(f"  Successfully loaded common URL")
                    return True, full_url, content
    
    print(f"  Reached maximum attempts ({total_attempts}/{max_total_attempts}), stopping URL fallback process")
    return False, None, None

def extract_pricing_content(html):
    """
    This function previously tried to extract pricing-specific content,
    but since the full HTML is more reliable, we'll just return it.
    
    Args:
        html: Full HTML content
        
    Returns:
        Full HTML content
    """
    # Simply return the full HTML since that's working reliably for your needs
    return html

def capture_pricing_data(website_filter=None, country_filter=None):
    """
    Capture pricing data using requests library.
    
    Args:
        website_filter: Optional name of single website to process
        country_filter: Optional country code to filter by
    """
    config = load_config()
    
    # Create output directories
    output_dir = config.get('output_dir', './screenshots')
    os.makedirs(output_dir, exist_ok=True)
    
    html_dir = os.path.join(output_dir, 'html')
    os.makedirs(html_dir, exist_ok=True)
    
    # List of sites known to have strong anti-bot protection
    stealth_sites = ["canva", "masterclass"]
    
    # Filter websites if specified
    websites = config['websites']
    if website_filter:
        websites = [w for w in websites if w['name'].lower() == website_filter.lower()]
        if not websites:
            print(f"No website found with name: {website_filter}")
            return
    
    for website in websites:
        website_name = website['name'].lower()
        print(f"Processing {website['name']}...")
        
        # Check if site needs stealth browser
        use_stealth = website_name in stealth_sites
        if use_stealth:
            print(f"  Using stealth browser approach for {website['name']}")
        
        # Filter countries if specified
        countries = website['countries']
        if country_filter:
            if country_filter.lower() in [c.lower() for c in countries]:
                countries = [country_filter.lower()]
            else:
                print(f"  Website {website['name']} doesn't have country: {country_filter}")
                continue
        
        for country in countries:
            try:
                # Verify proxy works
                proxy_url = get_proxy_url(country)
                if not proxy_url:
                    print(f"  Skipping {country} - no proxy available")
                    continue
                
                print(f"  Using proxy for {country.upper()}")
                
                # Verify proxy works
                try:
                    proxies = {'http': proxy_url, 'https': proxy_url}
                    print(f"  Verifying proxy connection...")
                    response = requests.get('https://ipinfo.io/json', proxies=proxies, timeout=20)
                    
                    if response.status_code == 200:
                        ip_data = response.json()
                        print(f"  ✓ Proxy verified. IP: {ip_data.get('ip')} ({ip_data.get('country')})")
                    else:
                        print(f"  ✗ Proxy verification failed. Status: {response.status_code}")
                        continue
                except Exception as e:
                    print(f"  ✗ Proxy verification failed: {e}")
                    continue
                
                # Create timestamp for filenames
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Choose approach based on site
                if use_stealth:
                    print(f"  Using Puppeteer stealth for {website['name']}")
                    url_to_try = website['url']
                    if '{country}' in url_to_try:
                        url_to_try = url_to_try.replace('{country}', country)
                    success, url_used, content = get_content_with_puppeteer_stealth(url_to_try, country)
                else:
                    # Use your existing requests approach
                    success, url_used, content = try_urls_with_fallback(website, country)
                
                # The rest of your function remains the same...
                if not success or not content:
                    print(f"  Failed to load website for {country}")
                    continue
                
                # Extract just the pricing section if possible
                pricing_html = extract_pricing_content(content)
                
                # Save the HTML content
                html_path = os.path.join(html_dir, f"{website['name'].lower()}_{country}_{timestamp}.html")
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(pricing_html)
                print(f"  Saved HTML content to {html_path}")
                
                # Save full HTML for reference
                full_html_path = os.path.join(html_dir, f"{website['name'].lower()}_{country}_{timestamp}_full.html")
                with open(full_html_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  Saved full HTML content to {full_html_path}")
                
                # Save metadata
                metadata_path = os.path.join(output_dir, f"{website['name'].lower()}_{country}_{timestamp}_metadata.json")
                metadata = {
                    "website": website['name'],
                    "country": country,
                    "original_url": website['url'],
                    "url_used": url_used,
                    "timestamp": datetime.now().isoformat(),
                    "proxy_used": True,
                    "proxy_country": country,
                    "html_path": html_path,
                    "full_html_path": full_html_path,
                    "method": "puppeteer_stealth" if use_stealth else "requests"
                }
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                print(f"  Successfully captured pricing data for {website['name']} in {country.upper()}")
                
            except Exception as e:
                print(f"Error processing {website['name']} for {country}: {e}")
            
            # Wait between requests
            wait_time = random.randint(5, 10)
            print(f"  Waiting {wait_time} seconds before next request...")
            time.sleep(wait_time)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture pricing data using requests")
    parser.add_argument("--website", type=str, help="Filter to process only this website")
    parser.add_argument("--country", type=str, help="Filter to process only this country")
    
    args = parser.parse_args()
    
    capture_pricing_data(website_filter=args.website, country_filter=args.country)
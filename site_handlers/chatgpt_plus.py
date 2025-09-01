"""
ChatGPT Plus specific handler with enhanced stealth capabilities.
"""
import json
import random
import time
from .base_handler import BaseSiteHandler

class ChatgptPlusHandler(BaseSiteHandler):
    """Handler for ChatGPT Plus (OpenAI) website with enhanced stealth."""
    
    def __init__(self, name="chatgpt_plus"):
        super().__init__(name)
    
    def get_url(self, country):
        """
        Get the URL for OpenAI pricing page.
        OpenAI doesn't have country-specific URLs.
        
        Args:
            country (str): Country code (ignored for OpenAI)
            
        Returns:
            str: URL for OpenAI pricing
        """
        return "https://openai.com/pricing"
    
    def get_firefox_args(self):
        """Get Firefox-specific arguments for enhanced stealth."""
        return [
            "--width=1920",
            "--height=1080",
            "--new-instance"
        ]
    
    def get_stealth_browser_args(self):
        """Get Firefox-specific arguments for enhanced stealth."""
        return [
            "--width=1920",
            "--height=1080",
            "--new-instance"
        ]
        """Get browser arguments for maximum stealth."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--exclude-switches=enable-automation",
            "--disable-extensions-except",
            "--disable-plugins-discovery",
            "--disable-default-apps",
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--window-size=1920,1080"
        ]
    
    def prepare_context(self, context, country):
        """
        Prepare the browser context with maximum stealth settings.
        
        Args:
            context (BrowserContext): Playwright browser context
            country (str): Country code
        """
        try:
            # Note: viewport is set during context creation, not here
            # context.set_viewport_size() doesn't exist - viewport is set in new_context()
            
            # Remove automation indicators
            context.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Deno.build.os === 'darwin' ? 'granted' : 'prompt' }) :
                        originalQuery(parameters)
                );
                
                // Mock chrome object
                window.chrome = {
                    runtime: {}
                };
                
                // Mock screen properties
                Object.defineProperty(screen, 'colorDepth', {
                    get: () => 24
                });
                
                // Hide automation traces
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """)
            
            # Set very realistic headers
            context.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "max-age=0",
                "Sec-Ch-Ua": '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
            })
            
            print("  Applied maximum stealth configuration for OpenAI")
        except Exception as e:
            print(f"  Error setting stealth configuration: {e}")
    
    def handle_cookie_consent(self, page):
        """
        Handle OpenAI's cookie consent with extreme caution and stealth.
        
        Args:
            page (Page): Playwright page object
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("  Using stealth cookie handling for OpenAI...")
            
            # Wait longer for page to fully load
            time.sleep(random.uniform(2, 4))
            
            # First, try to hide automation traces on the page itself
            try:
                page.evaluate("""
                    // Additional automation hiding
                    if (window.navigator.webdriver) {
                        delete window.navigator.webdriver;
                    }
                    
                    // Set realistic screen properties
                    Object.defineProperty(screen, 'availWidth', { value: 1920 });
                    Object.defineProperty(screen, 'availHeight', { value: 1080 });
                    
                    // Mock touch support
                    Object.defineProperty(navigator, 'maxTouchPoints', { value: 0 });
                """)
            except:
                pass
            
            # Human-like mouse movements before clicking
            try:
                # Move mouse to a random location first
                page.mouse.move(random.randint(100, 500), random.randint(100, 300))
                time.sleep(random.uniform(0.5, 1.0))
            except:
                pass
            
            # Look for cookie buttons with minimal DOM interaction
            cookie_selectors = [
                'button:has-text("Accept all")',
                'button:has-text("OK")',
                'button:has-text("Accept")',
                'button:has-text("I agree")',
                '[data-testid="accept-cookies"]',
                '.cookie-consent button'
            ]
            
            # Try each selector with human-like timing
            for i, selector in enumerate(cookie_selectors):
                try:
                    # Random delay between attempts
                    if i > 0:
                        time.sleep(random.uniform(0.5, 1.5))
                    
                    elements = page.locator(selector)
                    if elements.count() > 0:
                        print(f"  Found potential cookie button: {selector}")
                        
                        # Get the element position and move mouse to it naturally
                        try:
                            element = elements.first
                            box = element.bounding_box()
                            if box:
                                # Move to button center with slight randomization
                                target_x = box["x"] + box["width"] / 2 + random.randint(-5, 5)
                                target_y = box["y"] + box["height"] / 2 + random.randint(-2, 2)
                                
                                page.mouse.move(target_x, target_y)
                                time.sleep(random.uniform(0.1, 0.3))
                                
                                # Click with human-like timing
                                page.mouse.click(target_x, target_y)
                                print(f"  Clicked cookie button with mouse simulation")
                                
                                # Wait to see if the page stays alive
                                time.sleep(2)
                                
                                # Check if we're still alive
                                try:
                                    page.title()
                                    print("  ✓ Page survived cookie interaction")
                                    return True
                                except:
                                    print("  ✗ Page died after cookie click")
                                    return False
                        except Exception as e:
                            print(f"  Error with mouse simulation: {e}")
                            # Fall back to regular click
                            try:
                                element.click(timeout=3000)
                                time.sleep(1)
                                page.title()  # Test if alive
                                return True
                            except:
                                print(f"  Regular click also failed for {selector}")
                
                except Exception as e:
                    print(f"  Error with selector {selector}: {e}")
                    continue
            
            # If clicking failed, try setting cookies directly
            try:
                print("  Attempting to set consent cookies directly...")
                page.evaluate("""
                    // Set various consent cookies
                    const consentCookies = [
                        'cookieConsent=true',
                        'cookie_consent=accepted',
                        'gdpr_consent=true',
                        'privacy_consent=true',
                        'openai_consent=true'
                    ];
                    
                    consentCookies.forEach(cookie => {
                        document.cookie = cookie + '; path=/; domain=.openai.com; max-age=31536000';
                    });
                """)
                return True
            except Exception as e:
                print(f"  Error setting consent cookies: {e}")
            
            return False
            
        except Exception as e:
            print(f"  Error in stealth cookie handling: {e}")
            return False
    
    def perform_site_interactions(self, page):
        """
        Perform OpenAI-specific interactions with stealth timing.
        
        Args:
            page (Page): Playwright page object
        """
        try:
            # Check if page is still alive
            try:
                page.title()
            except Exception as e:
                print(f"  Page invalid before interactions: {e}")
                return
            
            # Human-like scrolling with pauses
            print("  Performing human-like page interactions...")
            
            # Scroll down slowly in stages
            scroll_steps = [0.1, 0.3, 0.5, 0.7]
            for step in scroll_steps:
                try:
                    page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {step})")
                    time.sleep(random.uniform(0.8, 1.5))
                    
                    # Check if page is still alive after each scroll
                    page.title()
                except Exception as e:
                    print(f"  Page became invalid during scrolling: {e}")
                    return
            
            # Look for pricing toggles with minimal interaction
            toggle_selectors = [
                'button:has-text("Monthly")',
                'button:has-text("Annual")',
                '[data-testid="billing-toggle"]'
            ]
            
            for selector in toggle_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Found pricing toggle: {selector}")
                        # Human-like hover before click
                        page.hover(selector)
                        time.sleep(random.uniform(0.3, 0.7))
                        page.click(selector, timeout=3000)
                        time.sleep(random.uniform(1.0, 2.0))
                        break
                except Exception as e:
                    pass
                    
        except Exception as e:
            print(f"  Error in stealth site interactions: {e}")
    
    def extract_pricing_data(self, page):
        """
        Extract OpenAI/ChatGPT Plus pricing with minimal DOM interaction.
        
        Args:
            page (Page): Playwright page object
            
        Returns:
            dict: Extracted pricing data
        """
        try:
            # Check if page is still valid
            try:
                page_title = page.title()
                print(f"  Extracting from page: {page_title}")
            except Exception as e:
                print(f"  Page invalid during extraction: {e}")
                return {
                    "site": "chatgpt_plus",
                    "url": "https://openai.com/pricing",
                    "error": "Page became invalid before extraction",
                    "plans": []
                }
            
            # Use minimal JavaScript to extract pricing
            pricing_data = page.evaluate("""() => {
                try {
                    // Look for pricing information with broad selectors
                    const possibleContainers = [
                        ...document.querySelectorAll('div'),
                        ...document.querySelectorAll('section'),
                        ...document.querySelectorAll('article')
                    ];
                    
                    const pricingElements = possibleContainers.filter(el => {
                        const text = el.textContent.toLowerCase();
                        return (text.includes('chatgpt') || text.includes('plus') || text.includes('pro')) && 
                               (text.includes('$') || text.includes('free') || text.includes('price'));
                    });
                    
                    if (pricingElements.length === 0) {
                        return [{ message: 'No pricing elements found on page' }];
                    }
                    
                    // Extract basic information from each element
                    return pricingElements.slice(0, 5).map((el, index) => {
                        const text = el.textContent;
                        
                        // Try to find plan name
                        const headings = el.querySelectorAll('h1, h2, h3, h4, h5, h6');
                        let planName = 'Unknown Plan';
                        for (const heading of headings) {
                            const headingText = heading.textContent.trim();
                            if (headingText.length > 0 && headingText.length < 50) {
                                planName = headingText;
                                break;
                            }
                        }
                        
                        // Look for price patterns
                        const priceMatch = text.match(/\$(\d+(?:\.\d{2})?)/);
                        const price = priceMatch ? priceMatch[0] : 'Price not found';
                        
                        // Extract some key phrases
                        const features = [];
                        if (text.includes('unlimited')) features.push('Unlimited usage');
                        if (text.includes('priority')) features.push('Priority access');
                        if (text.includes('faster')) features.push('Faster response times');
                        if (text.includes('advanced')) features.push('Advanced features');
                        
                        return {
                            name: planName,
                            price: price,
                            description: text.substring(0, 200) + '...',
                            features: features,
                            element_index: index
                        };
                    });
                } catch (error) {
                    return [{ error: 'JavaScript extraction failed: ' + error.message }];
                }
            }""")
            
            print("\n==== EXTRACTED OPENAI/CHATGPT PLUS PRICING ====")
            print(json.dumps(pricing_data, indent=2))
            print("===============================================\n")
            
            # Format the final result
            result = {
                "site": "chatgpt_plus",
                "url": page.url if hasattr(page, 'url') else "https://openai.com/pricing",
                "extraction_method": "stealth_minimal_dom",
                "plans": pricing_data
            }
            
            return result
        except Exception as e:
            print(f"  Error extracting OpenAI pricing: {e}")
            return {
                "site": "chatgpt_plus",
                "url": "https://openai.com/pricing",
                "error": str(e),
                "plans": []
            }
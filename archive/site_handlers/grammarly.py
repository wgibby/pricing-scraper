"""
Grammarly-specific handler for the pricing scraper.
"""
import json
from .base_handler import BaseSiteHandler

class GrammarlyHandler(BaseSiteHandler):
    """Handler for Grammarly website."""
    
    def __init__(self, name="grammarly"):
        super().__init__(name)
    
    def get_url(self, country):
        """
        Get the URL for Grammarly pricing page.
        Grammarly doesn't have country-specific URLs, so we use the main pricing URL.
        
        Args:
            country (str): Country code (ignored for Grammarly)
            
        Returns:
            str: URL for Grammarly pricing
        """
        return "https://www.grammarly.com/plans"
    
    def prepare_context(self, context, country):
        """
        Prepare the browser context with pre-acceptance cookies.
        
        Args:
            context (BrowserContext): Playwright browser context
            country (str): Country code
        """
        try:
            # Add cookies to bypass cookie consent
            context.add_cookies([
                {
                    "name": "OptanonAlertBoxClosed", 
                    "value": "2023-05-01T12:00:00.000Z", 
                    "domain": ".grammarly.com", 
                    "path": "/"
                },
                {
                    "name": "OptanonConsent", 
                    "value": "isGpcEnabled=0&datestamp=Wed+May+15+2023+12%3A00%3A00+GMT%2B0100+(BST)&version=202209.1.0&isIABGlobal=false&hosts=&consentId=12345&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&geolocation=GB%3BENG&AwaitingReconsent=false", 
                    "domain": ".grammarly.com", 
                    "path": "/"
                }
            ])
            print("  Added pre-acceptance cookies for Grammarly")
        except Exception as e:
            print(f"  Error setting pre-acceptance cookies: {e}")
    
    def handle_cookie_consent(self, page):
        """
        Handle Grammarly's specific cookie consent banner.
        
        Args:
            page (Page): Playwright page object
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("  Applying Grammarly-specific cookie handling...")
            
            # Try clicking the "Accept All Cookies" button
            accept_selectors = [
                'button:has-text("Accept All Cookies")',
                '.cookie-banner button:nth-child(2)',  # Usually the right-most button is Accept
                'button[data-qa="accept-all-cookies"]',
                '#onetrust-accept-btn-handler',
                'button.accept-all-cookies'
            ]
            
            for selector in accept_selectors:
                if page.locator(selector).count() > 0:
                    print(f"  Found Grammarly cookie button: {selector}")
                    page.click(selector)
                    page.wait_for_timeout(1000)
                    return True
            
            # Try direct JavaScript click - this looks for buttons with "Accept All" text
            result = page.evaluate("""() => {
                // Find buttons with Accept All text
                const buttons = Array.from(document.querySelectorAll('button'));
                const acceptButton = buttons.find(btn => 
                    btn.textContent.toLowerCase().includes('accept all')
                );
                
                if (acceptButton) {
                    acceptButton.click();
                    return true;
                }
                
                // Try finding the cookie banner and its buttons
                const cookieBanner = document.querySelector('.cookie-banner, #cookie-banner, [class*="cookie"]');
                if (cookieBanner) {
                    const bannerButtons = cookieBanner.querySelectorAll('button');
                    if (bannerButtons.length >= 2) {
                        // Usually the second button is "Accept All"
                        bannerButtons[1].click();
                        return true;
                    }
                }
                
                return false;
            }""")
            
            if result:
                print("  Clicked Grammarly cookie button via JavaScript")
                page.wait_for_timeout(1000)
                return True
            
            # If clicking fails, try removing the banner from DOM
            self._remove_cookie_banner(page)
            self._hide_cookie_banner_with_css(page)
                
            return False
        except Exception as e:
            print(f"  Error handling Grammarly cookies: {e}")
            return False
    
    def _remove_cookie_banner(self, page):
        """Remove Grammarly cookie banner from the DOM."""
        try:
            result = page.evaluate("""() => {
                // Find cookie banner elements
                const banners = [
                    document.querySelector('.cookie-banner'),
                    document.querySelector('#cookie-banner'),
                    document.querySelector('#onetrust-banner-sdk'),
                    document.querySelector('[role="alertdialog"]'),
                    document.querySelector('[class*="cookie"]')
                ].filter(Boolean);
                
                let removed = false;
                
                // Remove each banner found
                banners.forEach(banner => {
                    if (banner) {
                        banner.remove();
                        removed = true;
                    }
                });
                
                // Set cookie to prevent banner in future
                document.cookie = "OptanonAlertBoxClosed=2023-05-15T00:00:00.000Z; path=/; max-age=31536000";
                document.cookie = "OptanonConsent=isGpcEnabled=0; path=/; max-age=31536000";
                
                return removed;
            }""")
            
            if result:
                print("  Removed Grammarly cookie banner from DOM")
                return True
            return False
        except Exception as e:
            print(f"  Error removing Grammarly cookie banner: {e}")
            return False
    
    def _hide_cookie_banner_with_css(self, page):
        """Use CSS to hide Grammarly's cookie banner."""
        try:
            page.add_style_tag(content="""
                /* Hide Grammarly cookie banner */
                .cookie-banner, #cookie-banner, #onetrust-banner-sdk,
                [class*="cookie-banner"], [class*="cookie_banner"],
                [class*="cookieBanner"], div[role="alertdialog"] {
                    display: none !important;
                    visibility: hidden !important;
                    opacity: 0 !important;
                    pointer-events: none !important;
                    z-index: -9999 !important;
                }
                
                /* Ensure the body has normal padding */
                body {
                    padding-bottom: 0 !important;
                    margin-bottom: 0 !important;
                }
            """)
            print("  Applied CSS to hide Grammarly cookie banner")
            return True
        except Exception as e:
            print(f"  Error hiding Grammarly cookie banner with CSS: {e}")
            return False
    
    def perform_site_interactions(self, page):
        """
        Perform Grammarly-specific interactions needed to reveal pricing content.
        
        Args:
            page (Page): Playwright page object
        """
        try:
            # Scroll down to ensure all pricing features are visible
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
            page.wait_for_timeout(1000)
            
            # Force scroll to make pricing features fully visible
            page.evaluate("""() => {
                // Find all the pricing feature sections
                const featureSections = document.querySelectorAll('[class*="feature"], [class*="pricing"] li, [class*="plan"] li');
                
                // If found, scroll to ensure the bottom ones are visible
                if (featureSections.length > 0) {
                    const lastFeatures = featureSections[featureSections.length - 1];
                    lastFeatures.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    // Otherwise just scroll down enough to see past where a cookie banner might be
                    window.scrollTo(0, document.body.scrollHeight * 0.8);
                }
            }""")
            
            # Wait for scroll to complete
            page.wait_for_timeout(2000)
            
            # Try to click any monthly/yearly toggle
            toggle_selectors = [
                'button:has-text("Monthly")',
                'button:has-text("Annual")',
                '[data-qa="toggle-billing"]',
                '.billing-toggle',
                '[class*="billing-toggle"]'
            ]
            
            for selector in toggle_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Clicking billing toggle: {selector}")
                        page.click(selector)
                        page.wait_for_timeout(1000)
                except Exception as e:
                    pass
                    
        except Exception as e:
            print(f"  Error in Grammarly site interactions: {e}")
    
    def extract_pricing_data(self, page):
        """
        Extract Grammarly pricing details.
        
        Args:
            page (Page): Playwright page object
            
        Returns:
            dict: Extracted pricing data
        """
        try:
            pricing_data = page.evaluate("""() => {
                // Find pricing plan containers
                const plans = Array.from(document.querySelectorAll('[class*="plan"], [class*="pricing"] > div, [class*="card"]'));
                
                if (plans.length === 0) {
                    return [{message: 'No pricing plans found'}];
                }
                
                return plans.map(plan => {
                    // Get plan name
                    const nameElement = plan.querySelector('h2, h3, h4, [class*="title"], [class*="heading"]');
                    const name = nameElement ? nameElement.textContent.trim() : 'Unknown Plan';
                    
                    // Skip if not a pricing plan
                    if (!name || name.length < 2) return null;
                    
                    // Get price information
                    const priceElement = plan.querySelector('[class*="price"], [class*="amount"], span:has-text("£"), span:has-text("$")');
                    const priceText = priceElement ? priceElement.textContent.trim() : 'Price not found';
                    
                    // Extract numeric price and currency
                    let numericPrice = null;
                    let currency = null;
                    const priceMatch = priceText.match(/([£$€¥₹])\s*(\d+(\.\d+)?)/);
                    if (priceMatch) {
                        currency = priceMatch[1];
                        numericPrice = parseFloat(priceMatch[2]);
                    }
                    
                    // Get billing period
                    const periodElement = plan.querySelector('[class*="period"], [class*="billing"], [class*="month"]');
                    const period = periodElement ? periodElement.textContent.trim() : '';
                    
                    // Get features
                    const features = Array.from(plan.querySelectorAll('li, [class*="feature"]'))
                        .map(el => el.textContent.trim())
                        .filter(text => text.length > 0);
                    
                    return {
                        name,
                        price: {
                            display: priceText,
                            numeric: numericPrice,
                            currency
                        },
                        period,
                        features
                    };
                }).filter(Boolean); // Remove null entries
            }""")
            
            print("\n==== EXTRACTED GRAMMARLY PRICING ====")
            print(json.dumps(pricing_data, indent=2))
            print("=====================================\n")
            
            # Format the final result
            result = {
                "site": "grammarly",
                "url": page.url,
                "plans": pricing_data
            }
            
            return result
        except Exception as e:
            print(f"  Error extracting Grammarly pricing: {e}")
            return {
                "site": "grammarly",
                "url": page.url,
                "error": str(e),
                "plans": []
            }
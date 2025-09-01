"""
Template for creating new site handlers.
Copy this file and modify it to create a handler for a new site.
"""
import json
from .base_handler import BaseSiteHandler

class TemplateSiteHandler(BaseSiteHandler):
    """Template handler for a specific website."""
    
    def __init__(self, name="template"):
        super().__init__(name)
    
    def get_url(self, country):
        """
        Get the URL for the site for a specific country.
        
        Args:
            country (str): Country code (e.g., 'us', 'uk')
            
        Returns:
            str: URL for the site
        """
        # Modify this for your specific site
        # Example formats:
        # - "https://www.example.com/pricing"  # Same URL for all countries
        # - f"https://www.example.com/{country}/pricing"  # Country in path
        # - f"https://{country}.example.com/pricing"  # Country in subdomain
        return f"https://www.{self.name}.com/{country}/pricing"
    
    def prepare_context(self, context, country):
        """
        Prepare the browser context before navigating to the site.
        
        Args:
            context (BrowserContext): Playwright browser context
            country (str): Country code
        """
        # Optional: Set cookies to bypass consent dialogs
        # Example:
        # context.add_cookies([
        #     {
        #         "name": "cookieConsent", 
        #         "value": "true", 
        #         "domain": f".{self.name}.com", 
        #         "path": "/"
        #     }
        # ])
        pass
    
    def handle_cookie_consent(self, page):
        """
        Handle cookie consent dialogs.
        
        Args:
            page (Page): Playwright page object
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Add site-specific selectors for cookie consent buttons
        cookie_selectors = [
            'button:has-text("Accept all")',
            'button:has-text("Accept")',
            '#cookie-accept-button',
            '.cookie-banner button',
            # Add more selectors specific to this site
        ]
        
        for selector in cookie_selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"  Clicking cookie consent: {selector}")
                    page.click(selector)
                    page.wait_for_timeout(1000)
                    return True
            except Exception as e:
                print(f"  Error with cookie selector {selector}: {str(e)}")
                continue
        
        # Optional: Try direct DOM manipulation if clicking fails
        # page.evaluate("""() => {
        #     // Remove cookie banners by class or ID
        #     const banners = document.querySelectorAll('.cookie-banner, #cookie-notice');
        #     banners.forEach(banner => banner.remove());
        #     
        #     // Set cookies to prevent future banners
        #     document.cookie = "cookieConsent=true; path=/; max-age=31536000";
        # }""")
        
        return False
    
    def perform_site_interactions(self, page):
        """
        Perform site-specific interactions needed to reveal pricing content.
        
        Args:
            page (Page): Playwright page object
        """
        # Example: Click pricing toggle buttons, scroll to sections, etc.
        try:
            # Scroll to reveal pricing section
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
            page.wait_for_timeout(1000)
            
            # Example: Click a pricing option toggle (monthly/yearly)
            toggle_selectors = [
                'button:has-text("Monthly")',
                'button:has-text("Annual")',
                '.pricing-toggle',
                '#billing-toggle'
            ]
            
            for selector in toggle_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Clicking pricing option: {selector}")
                        page.click(selector)
                        page.wait_for_timeout(1000)
                except Exception as e:
                    pass
                    
            # Example: Find and click to reveal features
            # feature_selectors = [
            #     '.show-more-features',
            #     'button:has-text("See all features")'
            # ]
            # 
            # for selector in feature_selectors:
            #     try:
            #         if page.locator(selector).count() > 0:
            #             page.click(selector)
            #             page.wait_for_timeout(1000)
            #     except Exception as e:
            #         pass
                
        except Exception as e:
            print(f"  Error in site interactions: {e}")
    
    def extract_pricing_data(self, page):
        """
        Extract pricing data from the page.
        
        Args:
            page (Page): Playwright page object
            
        Returns:
            dict: Extracted pricing data
        """
        try:
            # This is where you implement the site-specific extraction logic
            # The example below shows a common pattern for pricing extraction
            
            pricing_data = page.evaluate("""() => {
                // Find pricing cards/options (modify selectors for your site)
                const cards = Array.from(document.querySelectorAll('.pricing-card, .plan-card, [class*="price-container"]'));
                
                if (cards.length === 0) {
                    return [{message: 'No pricing cards found'}];
                }
                
                return cards.map(card => {
                    // Get plan name
                    const nameElement = card.querySelector('h2, h3, h4, .title, [class*="heading"]');
                    const name = nameElement ? nameElement.textContent.trim() : 'Unknown Plan';
                    
                    // Get price information
                    const priceElement = card.querySelector('[class*="price"], [class*="amount"], span:has-text("$")');
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
                    const periodElement = card.querySelector('[class*="period"], [class*="billing"], [class*="month"]');
                    const period = periodElement ? periodElement.textContent.trim() : '';
                    
                    // Get features
                    const features = Array.from(card.querySelectorAll('li, [class*="feature"]'))
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
                });
            }""")
            
            print(f"\n==== EXTRACTED {self.name.upper()} PRICING ====")
            print(json.dumps(pricing_data, indent=2))
            print("======================================\n")
            
            # Format the final result
            result = {
                "site": self.name,
                "url": page.url,
                "plans": pricing_data
            }
            
            return result
        except Exception as e:
            print(f"  Error extracting {self.name} pricing: {e}")
            return {
                "site": self.name,
                "url": page.url,
                "error": str(e),
                "plans": []
            }
    
    def clean_up(self, page):
        """
        Perform any clean-up actions after scraping.
        
        Args:
            page (Page): Playwright page object
        """
        # Optional: Add any clean-up actions specific to this site
        # For example, logging out, closing modals, etc.
        pass
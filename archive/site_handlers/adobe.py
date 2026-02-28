"""
Enhanced Adobe site handler with geo-location popup handling.
"""
import json
import time
from .base_handler import BaseSiteHandler

class AdobeHandler(BaseSiteHandler):
    """Handler for Adobe Creative Cloud pricing pages with geo-popup handling."""
    
    def __init__(self, name="adobe"):
        super().__init__(name)
        self.site_domain = "adobe.com"
    
    def get_url(self, country):
        """Get the Adobe catalog URL - this shows all individual apps with pricing."""
        # Use the catalog page which shows all individual Adobe apps
        # Adobe handles geo-redirection automatically while preserving the catalog view
        return "https://www.adobe.com/products/catalog.html"
    
    def prepare_context(self, context, country):
        """Set cookies BEFORE page load to prevent dialogs entirely."""
        try:
            context.add_cookies([
                {
                    "name": "OptanonAlertBoxClosed",
                    "value": "2024-07-16T12:00:00.000Z",
                    "domain": f".{self.site_domain}",
                    "path": "/"
                },
                {
                    "name": "CookieConsent", 
                    "value": "true",
                    "domain": f".{self.site_domain}",
                    "path": "/"
                },
                {
                    "name": "privacy_accepted",
                    "value": "true", 
                    "domain": f".{self.site_domain}",
                    "path": "/"
                },
                # Adobe geo-preference cookie
                {
                    "name": "adobe_mc_geo",
                    "value": country.upper(),
                    "domain": f".{self.site_domain}",
                    "path": "/"
                },
                {
                    "name": "geo_preference_set",
                    "value": "true",
                    "domain": f".{self.site_domain}", 
                    "path": "/"
                }
            ])
            print(f"  Adobe cookies set for {country}")
        except Exception as e:
            print(f"  Adobe cookie prep failed: {e}")
    
    def handle_cookie_consent(self, page) -> bool:
        """Universal silent approach + geo-popup handling."""
        try:
            # First handle standard cookie consent
            page.evaluate("""() => {
                const domain = ".adobe.com";
                
                // Set consent cookies
                const cookies = [
                    `OptanonAlertBoxClosed=2024-07-16T12:00:00.000Z; path=/; domain=${domain}; max-age=31536000`,
                    `CookieConsent=true; path=/; domain=${domain}; max-age=31536000`,
                    `privacy_accepted=true; path=/; domain=${domain}; max-age=31536000`,
                    `geo_preference_set=true; path=/; domain=${domain}; max-age=31536000`
                ];
                
                cookies.forEach(cookie => document.cookie = cookie);
                
                // Hide all consent and geo dialogs with CSS
                const style = document.createElement('style');
                style.textContent = `
                    /* Standard consent dialogs */
                    #onetrust-consent-sdk,
                    #onetrust-banner-sdk,
                    #CybotCookiebotDialog,
                    
                    /* Adobe geo-location popups - multiple possible selectors */
                    [class*="geo-popup"],
                    [id*="geo-popup"],
                    [class*="location-popup"], 
                    [id*="location-popup"],
                    [class*="region-popup"],
                    [id*="region-popup"],
                    [aria-label*="location"],
                    [aria-label*="region"],
                    [aria-label*="wrong site"],
                    
                    /* Generic modal patterns */
                    .modal-backdrop,
                    .overlay,
                    [class*="dialog"],
                    [class*="modal"],
                    [role="dialog"][aria-modal="true"]
                    {
                        display: none !important;
                        visibility: hidden !important;
                        opacity: 0 !important;
                        pointer-events: none !important;
                        z-index: -9999 !important;
                    }
                    
                    body, html {
                        overflow: auto !important;
                        position: static !important;
                    }
                `;
                document.head.appendChild(style);
                
                console.log('Adobe universal consent + geo handling applied');
            }""")
            
            # Wait a moment for any dialogs to load
            page.wait_for_timeout(2000)
            
            # Now actively handle any geo-popups that might have appeared
            return self._handle_geo_popup(page)
            
        except Exception as e:
            print(f"Adobe silent handling failed: {e}")
            return False
    
    def _handle_geo_popup(self, page) -> bool:
        """Handle Adobe's geo-location popup specifically."""
        try:
            # Common selectors for "stay here" / "continue" buttons in geo popups
            stay_button_selectors = [
                # Text-based (works across languages for common words)
                "button:has-text('Stay')",
                "button:has-text('Continue')", 
                "button:has-text('Remain')",
                "a:has-text('Stay')",
                "a:has-text('Continue')",
                
                # Class/ID based (Adobe-specific patterns)
                "[class*='stay-button']",
                "[class*='continue-button']", 
                "[id*='stay-button']",
                "[id*='continue-button']",
                "[data-testid*='stay']",
                "[data-testid*='continue']",
                
                # Position-based (secondary button is usually "stay here")
                ".modal-footer button:nth-child(2)",
                ".dialog-footer button:nth-child(2)", 
                ".popup-footer button:nth-child(2)",
                
                # Generic "secondary" button patterns
                ".btn-secondary",
                ".button-secondary",
                "[class*='secondary-button']"
            ]
            
            for selector in stay_button_selectors:
                try:
                    if page.locator(selector).is_visible(timeout=1000):
                        print(f"  Found geo-popup 'stay' button with selector: {selector}")
                        page.locator(selector).click(timeout=5000)
                        page.wait_for_timeout(1000)
                        print("  Clicked 'stay here' button successfully")
                        return True
                except:
                    continue
            
            print("  No geo-popup detected or handled")
            return True
            
        except Exception as e:
            print(f"  Geo-popup handling failed: {e}")
            return False
    
    def perform_site_interactions(self, page):
        """Perform Adobe-specific interactions after handling popups."""
        try:
            # Wait for page to stabilize after popup handling
            page.wait_for_timeout(3000)
            
            # Handle any pricing toggles (monthly/yearly)
            try:
                yearly_toggle = page.locator("[data-testid='yearly-toggle'], .toggle-yearly, .billing-toggle")
                if yearly_toggle.is_visible(timeout=2000):
                    yearly_toggle.click()
                    page.wait_for_timeout(1000)
                    print("  Activated yearly pricing toggle")
            except:
                pass
            
            # Scroll to ensure all pricing content is loaded
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollTo(0, 0)")
            
            print("  Adobe site interactions completed")
            return True
            
        except Exception as e:
            print(f"  Adobe interactions failed: {e}")
            return False
    
    def extract_pricing_data(self, page):
        """Extract Adobe catalog pricing data - handles both individual apps and bundles."""
        try:
            # Wait for pricing content to be fully loaded
            page.wait_for_selector("[class*='pricing'], [class*='plan'], [data-testid*='plan'], .card", timeout=10000)
            
            pricing_data = page.evaluate("""() => {
                const plans = [];
                
                // Adobe catalog uses different selectors than the plans page
                const cardSelectors = [
                    '.card',  // Main catalog card selector
                    '[class*="pricing-card"]',
                    '[class*="plan-card"]', 
                    '[data-testid*="plan"]',
                    '.plan-container',
                    '.pricing-container'
                ];
                
                let cards = [];
                for (const selector of cardSelectors) {
                    cards = document.querySelectorAll(selector);
                    if (cards.length > 0) {
                        console.log(`Found ${cards.length} cards with selector: ${selector}`);
                        break;
                    }
                }
                
                cards.forEach((card, index) => {
                    try {
                        // Extract plan name - try multiple selectors
                        let name = 'Unknown Plan';
                        const nameSelectors = [
                            'h3', 'h4', '.card-title', '[class*="title"]', 
                            '[class*="plan-name"]', '.product-name'
                        ];
                        
                        for (const sel of nameSelectors) {
                            const nameEl = card.querySelector(sel);
                            if (nameEl && nameEl.textContent.trim()) {
                                name = nameEl.textContent.trim();
                                break;
                            }
                        }
                        
                        // Extract price - try multiple selectors
                        let price = 'Price not found';
                        const priceSelectors = [
                            '[class*="price"]', '.cost', '[data-testid*="price"]',
                            '.pricing', '.currency', '.amount'
                        ];
                        
                        for (const sel of priceSelectors) {
                            const priceEl = card.querySelector(sel);
                            if (priceEl && priceEl.textContent.trim()) {
                                price = priceEl.textContent.trim();
                                break;
                            }
                        }
                        
                        // Extract features/description
                        const featureSelectors = [
                            'li', '[class*="feature"]', '[class*="benefit"]',
                            '.description', '.details', 'p'
                        ];
                        
                        let features = [];
                        for (const sel of featureSelectors) {
                            const featureEls = card.querySelectorAll(sel);
                            if (featureEls.length > 0) {
                                features = Array.from(featureEls)
                                    .map(el => el.textContent.trim())
                                    .filter(f => f && f.length > 3); // Filter out empty/short text
                                break;
                            }
                        }
                        
                        // Only add plans that have meaningful data
                        if (name !== 'Unknown Plan' || price !== 'Price not found') {
                            plans.push({
                                name: name,
                                price: price,
                                features: features,
                                currency: (price.match(/[£$€¥]/)?.[0] || 'USD'),
                                card_index: index,
                                card_html: card.outerHTML.substring(0, 200) + '...' // Debug info
                            });
                        }
                    } catch (e) {
                        console.error(`Error extracting plan ${index}:`, e);
                    }
                });
                
                // If we didn't find many plans, log the page structure for debugging
                if (plans.length < 5) {
                    console.log('Found few plans, page structure debug:');
                    console.log('Page title:', document.title);
                    console.log('URL:', window.location.href);
                    console.log('Main containers:', document.querySelectorAll('[class*="container"], [class*="grid"], main').length);
                }
                
                return {
                    plans: plans,
                    site: 'adobe.com',
                    url: window.location.href,
                    timestamp: new Date().toISOString(),
                    total_plans: plans.length,
                    page_title: document.title
                };
            }""")
            
            print(f"  Extracted {len(pricing_data.get('plans', []))} Adobe plans from {pricing_data.get('url', 'unknown URL')}")
            return pricing_data
            
        except Exception as e:
            print(f"  Adobe pricing extraction failed: {e}")
            return {"plans": [], "site": "adobe.com", "error": str(e)}
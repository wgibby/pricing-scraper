"""
Zwift-specific handler for the pricing scraper.
"""
import json
from .base_handler import BaseSiteHandler

class ZwiftHandler(BaseSiteHandler):
    """Handler for Zwift website."""
    
    def __init__(self, name="zwift"):
        super().__init__(name)
    
    def get_url(self, country):
        """
        Get the URL for Zwift pricing page for a specific country.
        
        Args:
            country (str): Country code (e.g., 'us', 'uk')
            
        Returns:
            str: URL for Zwift pricing
        """
        return f"https://www.zwift.com/{country.lower()}/pricing"
    
    def handle_cookie_consent(self, page):
        """
        Handle Zwift's specific cookie banner.
        
        Args:
            page (Page): Playwright page object
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Try clicking the primary accept button
            accept_selectors = [
                'button:has-text("Accept all")',
                'button:has-text("ПРИЙНЯТИ УСЕ")',  # Ukrainian version
                'button:has-text("Accept")',
                '.manage-cookie-settings + button',  # Button next to "Manage Cookie Settings"
                'button.accept-cookies',
                '[data-testid="cookie-banner-accept"]'
            ]
            
            for selector in accept_selectors:
                if page.locator(selector).count() > 0:
                    page.click(selector)
                    page.wait_for_timeout(1000)
                    print("  Clicked Zwift cookie button")
                    return True
            
            # If no success with selectors, try direct DOM manipulation
            result = page.evaluate("""() => {
                // Look for buttons with text containing "accept" or "прийняти"
                const buttons = Array.from(document.querySelectorAll('button'));
                const acceptButton = buttons.find(btn => 
                    btn.textContent.toLowerCase().includes('accept') || 
                    btn.textContent.includes('прийняти')
                );
                
                if (acceptButton) {
                    acceptButton.click();
                    return true;
                }
                return false;
            }""")
            
            return result
        except Exception as e:
            print(f"  Error handling Zwift cookies: {e}")
            return False
    
    def perform_site_interactions(self, page):
        """
        Perform Zwift-specific interactions to reveal pricing content.
        
        Args:
            page (Page): Playwright page object
        """
        try:
            print("  Performing Zwift-specific interactions...")
            
            # First, wait for initial page load
            page.wait_for_timeout(3000)
            
            # Check if we're on the right page - look for pricing content
            has_pricing = page.evaluate("""() => {
                return document.body.textContent.toLowerCase().includes('membership') ||
                       document.body.textContent.toLowerCase().includes('subscribe') ||
                       document.querySelector('[class*="price"]') !== null;
            }""")
            
            if not has_pricing:
                print("  Page doesn't seem to have pricing content, may need to navigate to pricing page")
                # Try to find and click a pricing/membership link
                pricing_links = [
                    'a:has-text("Pricing")',
                    'a:has-text("Membership")',
                    'a:has-text("Subscribe")',
                    'a[href*="pricing"]',
                    'a[href*="membership"]'
                ]
                
                for link_selector in pricing_links:
                    try:
                        if page.locator(link_selector).count() > 0:
                            print(f"  Found pricing link: {link_selector}")
                            page.click(link_selector)
                            page.wait_for_timeout(3000)
                            break
                    except:
                        continue
            
            # Now look for pricing content more aggressively
            print("  Waiting for pricing content to load...")
            
            # Wait for pricing elements to appear
            pricing_indicators = [
                '[class*="price"]',
                '[data-price]',
                'text=/\\$\\d+/',
                'text=/membership/i',
                '[class*="plan"]',
                '[class*="subscription"]'
            ]
            
            for indicator in pricing_indicators:
                try:
                    page.wait_for_selector(indicator, timeout=5000)
                    print(f"  Found pricing indicator: {indicator}")
                    break
                except:
                    continue
            
            # Scroll through the page to trigger lazy loading
            print("  Scrolling to trigger content loading...")
            page.evaluate("""() => {
                // Scroll to different parts of the page to trigger lazy loading
                window.scrollTo(0, 0);
                setTimeout(() => window.scrollTo(0, document.body.scrollHeight * 0.3), 500);
                setTimeout(() => window.scrollTo(0, document.body.scrollHeight * 0.6), 1000);
                setTimeout(() => window.scrollTo(0, document.body.scrollHeight), 1500);
            }""")
            
            # Wait for scrolling to complete
            page.wait_for_timeout(3000)
            
            # Try to find and interact with pricing toggles
            toggle_selectors = [
                'button:has-text("Monthly")',
                'button:has-text("Annual")',
                'button:has-text("Yearly")',
                '[data-test*="toggle"]',
                '[data-testid*="toggle"]',
                '.toggle',
                '[class*="billing"]'
            ]
            
            for selector in toggle_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Clicking pricing toggle: {selector}")
                        page.click(selector)
                        page.wait_for_timeout(2000)
                except Exception as e:
                    pass
            
            # Final wait for any dynamic content
            page.wait_for_timeout(2000)
            
        except Exception as e:
            print(f"  Error in Zwift site interactions: {e}")
    
    def extract_pricing_data(self, page):
        """
        Extract Zwift pricing details.
        
        Args:
            page (Page): Playwright page object
            
        Returns:
            dict: Extracted pricing data
        """
        try:
            print("  Extracting Zwift pricing data...")
            
            # First, let's see what's actually on the page
            page_info = page.evaluate("""() => {
                return {
                    title: document.title,
                    url: window.location.href,
                    hasText: {
                        membership: document.body.textContent.toLowerCase().includes('membership'),
                        pricing: document.body.textContent.toLowerCase().includes('pricing'),
                        subscribe: document.body.textContent.toLowerCase().includes('subscribe'),
                        dollar: document.body.textContent.includes('
)
                    }
                };
            }""")
            
            print(f"  Page info: {page_info}")
            
            pricing_data = page.evaluate("""() => {
                // Multiple strategies to find pricing information
                
                // Strategy 1: Look for explicit pricing containers
                let cards = Array.from(document.querySelectorAll('.membership-card, [data-option], .pricing-card, .plan-card'));
                
                // Strategy 2: Look for any element containing dollar signs
                if (cards.length === 0) {
                    const dollarElements = Array.from(document.querySelectorAll('*')).filter(el => 
                        el.textContent && el.textContent.includes('
) && el.children.length < 3
                    );
                    
                    // Find their parent containers that might be pricing cards
                    cards = dollarElements.map(el => {
                        let parent = el.parentElement;
                        while (parent && parent !== document.body) {
                            if (parent.classList.length > 0 || parent.id) {
                                return parent;
                            }
                            parent = parent.parentElement;
                        }
                        return el;
                    }).filter((card, index, self) => self.indexOf(card) === index); // Remove duplicates
                }
                
                // Strategy 3: Look for common pricing-related class patterns
                if (cards.length === 0) {
                    const selectors = [
                        '[class*="price"]',
                        '[class*="plan"]',
                        '[class*="tier"]',
                        '[class*="subscription"]',
                        '[class*="membership"]',
                        '[id*="price"]',
                        '[id*="plan"]'
                    ];
                    
                    for (const selector of selectors) {
                        cards = Array.from(document.querySelectorAll(selector));
                        if (cards.length > 0) break;
                    }
                }
                
                // Strategy 4: Find any structured content that might contain pricing
                if (cards.length === 0) {
                    // Look for divs or sections with multiple children that might be pricing tiers
                    const containers = Array.from(document.querySelectorAll('div, section')).filter(el => 
                        el.children.length >= 2 && el.children.length <= 10 &&
                        el.textContent.toLowerCase().includes('month')
                    );
                    cards = containers;
                }
                
                if (cards.length === 0) {
                    // Last resort: return page content for manual analysis
                    return [{
                        message: 'No pricing cards found',
                        pageTitle: document.title,
                        pageUrl: window.location.href,
                        bodyText: document.body.textContent.substring(0, 1000),
                        allText: Array.from(document.querySelectorAll('*')).map(el => el.textContent).filter(text => 
                            text && text.includes('
)
                        ).slice(0, 10)
                    }];
                }
                
                return cards.map((card, index) => {
                    // Get all text content from the card
                    const cardText = card.textContent || '';
                    
                    // Extract plan name - look for headers or emphasized text
                    let name = 'Unknown Plan';
                    const nameSelectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', '.title', '[class*="heading"]', '[class*="name"]'];
                    for (const selector of nameSelectors) {
                        const nameEl = card.querySelector(selector);
                        if (nameEl && nameEl.textContent.trim()) {
                            name = nameEl.textContent.trim();
                            break;
                        }
                    }
                    
                    // If no name found, use position or try to infer from content
                    if (name === 'Unknown Plan') {
                        if (cardText.toLowerCase().includes('free')) name = 'Free';
                        else if (cardText.toLowerCase().includes('basic')) name = 'Basic';
                        else if (cardText.toLowerCase().includes('premium')) name = 'Premium';
                        else if (cardText.toLowerCase().includes('pro')) name = 'Pro';
                        else name = `Plan ${index + 1}`;
                    }
                    
                    // Extract price information - multiple approaches
                    let priceText = 'Price not found';
                    let numericPrice = null;
                    let currency = null;
                    
                    // Look for price elements
                    const priceSelectors = ['[class*="price"]', '[data-price]', '.amount', '.cost'];
                    for (const selector of priceSelectors) {
                        const priceEl = card.querySelector(selector);
                        if (priceEl) {
                            priceText = priceEl.textContent.trim();
                            break;
                        }
                    }
                    
                    // If no specific price element, extract from all text
                    if (priceText === 'Price not found') {
                        const priceMatches = cardText.match(/\\$\\d+(?:\\.\\d+)?/g);
                        if (priceMatches && priceMatches.length > 0) {
                            priceText = priceMatches[0];
                        }
                    }
                    
                    // Extract numeric price and currency
                    const priceMatch = priceText.match(/([£$€¥₹])\\s*(\\d+(?:\\.\\d+)?)/);
                    if (priceMatch) {
                        currency = priceMatch[1];
                        numericPrice = parseFloat(priceMatch[2]);
                    }
                    
                    // Get billing period
                    let period = '';
                    if (cardText.toLowerCase().includes('/month') || cardText.toLowerCase().includes('monthly')) {
                        period = 'monthly';
                    } else if (cardText.toLowerCase().includes('/year') || cardText.toLowerCase().includes('yearly') || cardText.toLowerCase().includes('annual')) {
                        period = 'yearly';
                    }
                    
                    // Extract features
                    const features = [];
                    const featureElements = card.querySelectorAll('li, p, [class*="feature"]');
                    featureElements.forEach(el => {
                        const text = el.textContent.trim();
                        if (text && text.length > 0 && text.length < 200 && !text.includes('
)) {
                            features.push(text);
                        }
                    });
                    
                    return {
                        name,
                        price: {
                            display: priceText,
                            numeric: numericPrice,
                            currency
                        },
                        period,
                        features,
                        rawContent: cardText.substring(0, 500), // For debugging
                        cardHtml: card.outerHTML.substring(0, 1000) // For debugging
                    };
                });
            }""")
            
            print("\n==== EXTRACTED ZWIFT PRICING ====")
            print(json.dumps(pricing_data, indent=2))
            print("=================================\n")
            
            # Format the final result
            result = {
                "site": "zwift",
                "url": page.url,
                "plans": pricing_data
            }
            
            return result
        except Exception as e:
            print(f"  Error extracting Zwift pricing: {e}")
            return {
                "site": "zwift",
                "url": page.url,
                "error": str(e),
                "plans": []
            }
"""
Dropbox-specific handler for the pricing scraper.
Handles monthly/yearly billing via URL parameters (?billing=monthly).
"""
import json
import time
from .base_handler import BaseSiteHandler

class DropboxHandler(BaseSiteHandler):
    """Handler for Dropbox website."""

    def __init__(self, name="dropbox"):
        super().__init__(name)
        self.detection_level = "MEDIUM"

    def get_stealth_browser_args(self):
        """Get browser arguments to avoid detection."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox"
        ]

    def get_url(self, country):
        """
        Get the URL for Dropbox pricing page with monthly billing parameter.
        Dropbox uses a global pricing page with URL params for billing period.

        Args:
            country (str): Country code (used for geo-targeting but URL is same)

        Returns:
            str: URL for Dropbox monthly pricing
        """
        return "https://www.dropbox.com/plans?billing=monthly"

    def prepare_context(self, context, country):
        """
        Prepare the browser context.

        Args:
            context (BrowserContext): Playwright browser context
            country (str): Country code
        """
        try:
            print("  Preparing Dropbox context...")
            print("  ✓ Dropbox context prepared")

        except Exception as e:
            print(f"  Error preparing Dropbox context: {e}")

    def handle_cookie_consent(self, page):
        """
        Handle Dropbox's cookie consent banner.

        Args:
            page (Page): Playwright page object

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("  Handling Dropbox cookie consent...")

            # Wait for page to load
            page.wait_for_timeout(2000)

            # Dropbox-specific cookie consent selectors
            cookie_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                'button:has-text("Accept all cookies")',
                'button:has-text("Got it")',
                'button:has-text("OK")',
                '[data-testid="cookie-accept"]',
                '[aria-label="Accept cookies"]',
                'button[class*="accept"]',
                'button[class*="cookie"]'
            ]

            consent_handled = False

            for selector in cookie_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Found cookie consent: {selector}")
                        page.click(selector, timeout=3000)
                        page.wait_for_timeout(1000)
                        consent_handled = True
                        break
                except Exception as e:
                    continue

            # Hide cookie banners with CSS if they persist
            page.evaluate("""() => {
                try {
                    const style = document.createElement('style');
                    style.textContent = `
                        div[class*="cookie"], div[id*="cookie"],
                        div[class*="consent"], div[id*="consent"],
                        div[class*="banner"], div[id*="banner"] {
                            display: none !important;
                            opacity: 0 !important;
                            pointer-events: none !important;
                            z-index: -9999 !important;
                        }
                    `;
                    document.head.appendChild(style);
                } catch(e) {
                    console.log('CSS hiding failed:', e);
                }
            }""")

            if consent_handled:
                print("  ✓ Cookie consent handled")
            else:
                print("  No cookie consent found")

            return True

        except Exception as e:
            print(f"  Error handling cookie consent: {e}")
            return True  # Don't fail the scrape

    def perform_site_interactions(self, page):
        """
        Perform Dropbox-specific interactions.
        Since we use ?billing=monthly in the URL, minimal interaction needed.

        Args:
            page (Page): Playwright page object
        """
        try:
            print("  Performing Dropbox site interactions...")

            # Wait for page to stabilize and all content to load
            page.wait_for_timeout(3000)

            # Scroll to the very top first
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)

            # Hide sticky header/nav to prevent overlap
            page.evaluate("""() => {
                try {
                    // Find and hide only the top navigation bar
                    const headers = document.querySelectorAll('header');
                    headers.forEach(header => {
                        const style = window.getComputedStyle(header);
                        if (style.position === 'fixed' || style.position === 'sticky') {
                            header.style.display = 'none';
                        }
                    });

                    // Also try to find nav elements that are fixed/sticky
                    const navs = document.querySelectorAll('nav');
                    navs.forEach(nav => {
                        const style = window.getComputedStyle(nav);
                        if (style.position === 'fixed' || style.position === 'sticky') {
                            nav.style.display = 'none';
                        }
                    });
                } catch(e) {
                    console.log('Header hiding failed:', e);
                }
            }""")
            page.wait_for_timeout(1000)

            # Scroll to the absolute top to show all pricing cards
            # This should show all 5 plans (Basic, Plus, Professional, Standard, Advanced)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1500)

            # Verify monthly pricing is displayed
            try:
                pricing_verification = page.evaluate("""() => {
                    const pageText = document.body.textContent || '';

                    const monthlyIndicators = [
                        '/ month', '/month', 'per month', 'monthly', '/mo'
                    ];

                    const annualIndicators = [
                        '/ year', '/year', 'per year', 'annually', '/yr', 'billed yearly'
                    ];

                    const hasMonthly = monthlyIndicators.some(indicator =>
                        pageText.toLowerCase().includes(indicator.toLowerCase())
                    );

                    const hasAnnual = annualIndicators.some(indicator =>
                        pageText.toLowerCase().includes(indicator.toLowerCase())
                    );

                    return { hasMonthly, hasAnnual };
                }""")

                if pricing_verification['hasMonthly']:
                    print("  ✓ Confirmed Monthly pricing is displayed")
                elif pricing_verification['hasAnnual']:
                    print("  ⚠ Warning: Showing Annual pricing indicators")
                else:
                    print("  ? Unable to determine pricing period")

            except Exception as e:
                print(f"  Could not verify pricing period: {e}")

            # Scroll to ensure all plans are visible
            page.evaluate("window.scrollTo(0, 600)")
            page.wait_for_timeout(1500)

            print("  ✓ Site interactions completed")

        except Exception as e:
            print(f"  Error in Dropbox site interactions: {e}")

    def extract_pricing_data(self, page):
        """
        Extract Dropbox pricing details.

        Args:
            page (Page): Playwright page object

        Returns:
            dict: Extracted pricing data
        """
        try:
            print("  Extracting Dropbox pricing data...")

            # Wait for content to be ready
            page.wait_for_timeout(2000)

            pricing_data = page.evaluate("""() => {
                const pageText = document.body.textContent || '';

                // Check if we have Dropbox pricing content
                const hasDropboxPricing = (
                    (pageText.includes('Basic') || pageText.includes('Plus') ||
                     pageText.includes('Professional') || pageText.includes('Standard') ||
                     pageText.includes('Advanced') || pageText.includes('Enterprise')) &&
                    (pageText.includes('$') || pageText.includes('€') || pageText.includes('£'))
                );

                if (!hasDropboxPricing) {
                    return [{
                        message: 'No Dropbox pricing content detected',
                        page_url: window.location.href,
                        page_title: document.title
                    }];
                }

                // Strategy: Look for plan cards by finding elements with plan names
                const planData = [];

                // Dropbox plans in order
                const planNames = [
                    'Basic',
                    'Plus',
                    'Professional',
                    'Standard',
                    'Advanced',
                    'Enterprise'
                ];

                planNames.forEach(planName => {
                    // Find all elements that contain this plan name
                    const allElements = Array.from(document.querySelectorAll('*'));
                    const planElements = allElements.filter(el => {
                        const text = el.textContent?.trim() || '';
                        const tagName = el.tagName.toLowerCase();

                        // Look for heading-like elements with the plan name
                        const className = el.className || '';
                        const classStr = typeof className === 'string' ? className.toLowerCase() : '';
                        const isHeading = tagName.match(/h[1-6]/) ||
                                        el.getAttribute('role') === 'heading' ||
                                        classStr.includes('heading') ||
                                        classStr.includes('title');

                        const hasExactName = text === planName ||
                                           text === `Dropbox ${planName}` ||
                                           (text.startsWith(planName) && text.length < planName.length + 50);

                        return (isHeading && hasExactName && el.offsetHeight > 0);
                    });

                    if (planElements.length === 0) return;

                    // Get the first matching element and traverse up to find the card container
                    let cardContainer = planElements[0];

                    // Traverse up to find a larger container (the pricing card)
                    for (let i = 0; i < 12; i++) {
                        if (!cardContainer.parentElement) break;
                        cardContainer = cardContainer.parentElement;

                        const containerText = cardContainer.textContent || '';
                        const hasPrice = containerText.match(/\\$|€|£/) ||
                                       containerText.match(/free|contact/i);
                        const hasFeatures = containerText.length > 150;

                        if (hasPrice && hasFeatures && containerText.length < 4000) {
                            break;
                        }
                    }

                    const cardText = cardContainer.textContent || '';

                    // Extract price
                    let priceInfo = {
                        display: 'Price not found',
                        numeric: null,
                        currency: null
                    };

                    // Special handling for Free/Basic
                    if (planName === 'Basic' || cardText.match(/free|\\$0/i)) {
                        priceInfo = {
                            display: 'Free',
                            numeric: 0,
                            currency: '$'
                        };
                    }
                    // Special handling for Enterprise
                    else if (planName === 'Enterprise') {
                        if (cardText.match(/contact|custom|talk to sales/i)) {
                            priceInfo = {
                                display: 'Contact for pricing',
                                numeric: null,
                                currency: null
                            };
                        }
                    }
                    // Extract numeric pricing
                    else {
                        // Look for pricing patterns
                        const dollarPattern = /\\$\\s*(\\d+(?:\\.\\d+)?)/;
                        const euroPattern = /€\\s*(\\d+(?:[.,]\\d+)?)/;
                        const poundPattern = /£\\s*(\\d+(?:\\.\\d+)?)/;

                        let match = cardText.match(dollarPattern);
                        let currency = '$';

                        if (!match) {
                            match = cardText.match(euroPattern);
                            currency = '€';
                        }
                        if (!match) {
                            match = cardText.match(poundPattern);
                            currency = '£';
                        }

                        if (match) {
                            const price = parseFloat(match[1].replace(',', '.'));
                            priceInfo = {
                                display: `${currency}${price}`,
                                numeric: price,
                                currency: currency
                            };
                        }
                    }

                    // Extract billing period and user basis
                    let period = '';
                    let perUser = false;

                    if (cardText.match(/\\/\\s*month|per month|monthly/i)) period = 'monthly';
                    else if (cardText.match(/\\/\\s*year|per year|yearly|annually/i)) period = 'yearly';

                    if (cardText.match(/\\/\\s*user|per user/i)) perUser = true;

                    // Extract storage info
                    let storage = '';
                    const storageMatch = cardText.match(/(\\d+)\\s*(GB|TB)/i);
                    if (storageMatch) {
                        storage = `${storageMatch[1]} ${storageMatch[2].toUpperCase()}`;
                    }

                    // Extract features - look for list items
                    const features = [];
                    const listItems = cardContainer.querySelectorAll('li');
                    listItems.forEach(li => {
                        const text = li.textContent?.trim();
                        if (text && text.length > 5 && text.length < 300) {
                            const cleanText = text.replace(/\\n/g, ' ').replace(/\\s+/g, ' ').trim();
                            // Filter out price-related text and CTA buttons
                            if (!cleanText.match(/\\$|€|£/) &&
                                !cleanText.match(/buy now|get started|try free/i)) {
                                features.push(cleanText);
                            }
                        }
                    });

                    planData.push({
                        name: planName,
                        price: priceInfo,
                        period: period,
                        per_user: perUser,
                        storage: storage,
                        features: features.slice(0, 15)
                    });
                });

                if (planData.length === 0) {
                    return [{
                        message: 'Could not locate Dropbox pricing cards',
                        page_url: window.location.href,
                        debug_info: {
                            has_dollar_sign: pageText.includes('$'),
                            has_plan_names: pageText.match(/Basic|Plus|Professional|Standard/i) !== null
                        }
                    }];
                }

                return planData;
            }""")

            print("\n==== EXTRACTED DROPBOX PRICING ====")
            print(json.dumps(pricing_data, indent=2))
            print("====================================\n")

            return {
                "site": "dropbox",
                "url": page.url,
                "plans": pricing_data
            }

        except Exception as e:
            print(f"  Error extracting Dropbox pricing: {e}")
            return {
                "site": "dropbox",
                "url": page.url if hasattr(page, 'url') else "unknown",
                "error": str(e),
                "plans": []
            }

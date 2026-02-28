"""
Canva-specific handler for the pricing scraper.
Handles monthly/yearly toggle and extracts pricing data for all plans.
Uses Firefox for better compatibility with Canva's bot detection.
"""
import json
import time
from .base_handler import BaseSiteHandler

class CanvaHandler(BaseSiteHandler):
    """Handler for Canva website."""

    def __init__(self, name="canva"):
        super().__init__(name)
        self.detection_level = "HIGH"  # Canva has strong bot detection

    def get_firefox_args(self):
        """Get Firefox-specific arguments for better compatibility."""
        return [
            "--width=1920",
            "--height=1080",
            "--new-instance"
        ]

    def get_stealth_browser_args(self):
        """Get browser arguments to avoid detection (simplified for stability)."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox"
        ]

    def get_url(self, country):
        """
        Get the URL for Canva pricing page.
        Canva uses a global pricing page, not country-specific.

        Args:
            country (str): Country code (used for geo-targeting but URL is same)

        Returns:
            str: URL for Canva pricing
        """
        return "https://www.canva.com/pricing/"

    def prepare_context(self, context, country):
        """
        Prepare the browser context.

        Args:
            context (BrowserContext): Playwright browser context
            country (str): Country code
        """
        try:
            print("  Preparing Canva context...")
            # Note: add_init_script causes Chromium crashes on some systems
            # Relying on browser args and Firefox for stealth instead
            print("  ✓ Canva context prepared")

        except Exception as e:
            print(f"  Error preparing Canva context: {e}")

    def handle_cookie_consent(self, page):
        """
        Handle Canva's cookie consent banner.

        Args:
            page (Page): Playwright page object

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("  Handling Canva cookie consent...")

            # Wait for page to load
            page.wait_for_timeout(2000)

            # Canva-specific cookie consent selectors
            canva_cookie_selectors = [
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

            for selector in canva_cookie_selectors:
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
        Perform Canva-specific interactions to reveal pricing and toggle to Monthly.

        Args:
            page (Page): Playwright page object
        """
        try:
            print("  Performing Canva site interactions...")

            # Wait for page to stabilize
            page.wait_for_timeout(2000)

            # Scroll to pricing section
            page.evaluate("window.scrollTo(0, 400)")
            page.wait_for_timeout(1000)

            # Toggle to Monthly pricing
            print("  Looking for Monthly/Yearly toggle...")

            monthly_toggled = False

            # Strategy 1: Look for specific billing toggle buttons/tabs
            toggle_selectors = [
                'button:has-text("Monthly")',
                'button:has-text("Pay monthly")',
                '[role="tab"]:has-text("Monthly")',
                '[data-testid*="monthly"]',
                'input[type="radio"][value*="month"]',
                'input[name*="billing"][value*="month"]'
            ]

            for selector in toggle_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Found monthly toggle: {selector}")
                        page.click(selector, timeout=3000)
                        page.wait_for_timeout(1500)  # Wait for prices to update
                        print("  ✓ Clicked Monthly toggle")
                        monthly_toggled = True
                        break
                except Exception as e:
                    continue

            # Strategy 2: JavaScript approach for toggle groups
            if not monthly_toggled:
                print("  Trying JavaScript approach for toggle...")
                try:
                    monthly_toggled = page.evaluate("""() => {
                        // Look for Monthly/Yearly keywords
                        const monthlyKeywords = [
                            'monthly', 'month', 'mensuel', 'monatlich', 'mensual', 'mensal'
                        ];

                        // Find all buttons and tabs
                        const buttons = Array.from(document.querySelectorAll('button, [role="button"], [role="tab"]'));

                        // Try to find explicit monthly button
                        for (const keyword of monthlyKeywords) {
                            const monthlyButton = buttons.find(btn => {
                                const text = (btn.textContent || '').toLowerCase();
                                return text.includes(keyword) && !text.includes('annual') && !text.includes('year');
                            });

                            if (monthlyButton) {
                                console.log('Found Monthly button:', monthlyButton.textContent);
                                monthlyButton.click();
                                return true;
                            }
                        }

                        // Look for radio inputs with monthly values
                        const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
                        const monthlyRadio = radios.find(radio => {
                            const value = (radio.value || '').toLowerCase();
                            const name = (radio.name || '').toLowerCase();
                            return monthlyKeywords.some(k => value.includes(k) || name.includes(k));
                        });

                        if (monthlyRadio) {
                            console.log('Found Monthly radio button');
                            monthlyRadio.click();
                            return true;
                        }

                        // Look for toggle containers with 2 options (monthly typically first)
                        const toggleContainers = Array.from(document.querySelectorAll('[role="tablist"], [role="radiogroup"]'));
                        for (const container of toggleContainers) {
                            const options = container.querySelectorAll('button, [role="tab"]');
                            if (options.length === 2) {
                                console.log('Found toggle container, clicking first option (likely Monthly)');
                                options[0].click();
                                return true;
                            }
                        }

                        return false;
                    }""")

                    if monthly_toggled:
                        print("  ✓ Successfully toggled to Monthly via JavaScript")
                        page.wait_for_timeout(1500)
                    else:
                        print("  ⚠ Could not find Monthly toggle - may already be on Monthly")

                except Exception as e:
                    print(f"  JavaScript toggle failed: {e}")

            # Verify we're showing monthly pricing
            page.wait_for_timeout(1000)
            try:
                pricing_verification = page.evaluate("""() => {
                    const pageText = document.body.textContent || '';

                    const monthlyIndicators = [
                        '/ month', '/month', 'per month', 'monthly', '/mo'
                    ];

                    const annualIndicators = [
                        '/ year', '/year', 'per year', 'annually', '/yr'
                    ];

                    const hasMonthly = monthlyIndicators.some(indicator =>
                        pageText.toLowerCase().includes(indicator.toLowerCase())
                    );

                    const hasAnnual = annualIndicators.some(indicator =>
                        pageText.toLowerCase().includes(indicator.toLowerCase())
                    );

                    return { hasMonthly, hasAnnual };
                }""")

                if pricing_verification['hasMonthly'] and not pricing_verification['hasAnnual']:
                    print("  ✓ Confirmed Monthly pricing is displayed")
                elif pricing_verification['hasAnnual'] and not pricing_verification['hasMonthly']:
                    print("  ⚠ Warning: Showing Annual pricing")
                elif pricing_verification['hasMonthly'] and pricing_verification['hasAnnual']:
                    print("  ✓ Both Monthly and Annual pricing visible")
                else:
                    print("  ? Unable to determine pricing period")

            except Exception as e:
                print(f"  Could not verify pricing period: {e}")

            # Scroll to ensure all plans are visible
            page.evaluate("window.scrollTo(0, 600)")
            page.wait_for_timeout(1500)

            print("  ✓ Site interactions completed")

        except Exception as e:
            print(f"  Error in Canva site interactions: {e}")

    def extract_pricing_data(self, page):
        """
        Extract Canva pricing details.

        Args:
            page (Page): Playwright page object

        Returns:
            dict: Extracted pricing data
        """
        try:
            print("  Extracting Canva pricing data...")

            # Wait for content to be ready
            page.wait_for_timeout(2000)

            pricing_data = page.evaluate("""() => {
                const pageText = document.body.textContent || '';

                // Check if we have Canva pricing content
                const hasCanvaPricing = (
                    (pageText.includes('Free') || pageText.includes('Pro') || pageText.includes('Teams') || pageText.includes('Enterprise')) &&
                    (pageText.includes('US$') || pageText.includes('$') || pageText.includes('€') || pageText.includes('£'))
                );

                if (!hasCanvaPricing) {
                    return [{
                        message: 'No Canva pricing content detected',
                        page_url: window.location.href,
                        page_title: document.title
                    }];
                }

                // Strategy: Look for the specific plan cards by finding elements with plan names
                const planData = [];
                const planNames = ['Canva Free', 'Canva Pro', 'Canva Teams', 'Canva Enterprise'];

                planNames.forEach(planName => {
                    // Find all elements that contain this exact plan name
                    const allElements = Array.from(document.querySelectorAll('*'));
                    const planElements = allElements.filter(el => {
                        const text = el.textContent?.trim() || '';
                        const hasExactName = text === planName ||
                                           (text.startsWith(planName) && text.length < planName.length + 50);
                        return hasExactName && el.offsetHeight > 0;
                    });

                    if (planElements.length === 0) return;

                    // Get the first matching element and traverse up to find the card container
                    let cardContainer = planElements[0];

                    // Traverse up to find a larger container (the pricing card)
                    for (let i = 0; i < 10; i++) {
                        if (!cardContainer.parentElement) break;
                        cardContainer = cardContainer.parentElement;

                        const containerText = cardContainer.textContent || '';
                        const hasPrice = containerText.match(/US\\$|\\$|€|£/) || containerText.includes('talk');
                        const hasFeatures = containerText.length > 200;

                        if (hasPrice && hasFeatures && containerText.length < 3000) {
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

                    // Special handling for Enterprise
                    if (planName.includes('Enterprise')) {
                        if (cardText.match(/let'?s talk|contact|custom/i)) {
                            priceInfo = {
                                display: 'Contact for pricing',
                                numeric: null,
                                currency: null
                            };
                        }
                    } else {
                        // Look for US$ pattern (Canva uses this format)
                        const usPattern = /US\\$\\s*(\\d+(?:\\.\\d+)?)/;
                        const dollarPattern = /\\$\\s*(\\d+(?:\\.\\d+)?)/;
                        const euroPattern = /€\\s*(\\d+(?:[.,]\\d+)?)/;
                        const poundPattern = /£\\s*(\\d+(?:\\.\\d+)?)/;

                        let match = cardText.match(usPattern) || cardText.match(dollarPattern);
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
                        } else if (planName.includes('Free')) {
                            priceInfo = {
                                display: 'Free',
                                numeric: 0,
                                currency: '$'
                            };
                        }
                    }

                    // Extract billing period
                    let period = '';
                    if (cardText.match(/\\/month|per month|monthly/i)) period = 'monthly';
                    else if (cardText.match(/\\/year|per year|yearly|annually/i)) period = 'yearly';

                    // Extract features - look for list items
                    const features = [];
                    const listItems = cardContainer.querySelectorAll('li');
                    listItems.forEach(li => {
                        const text = li.textContent?.trim();
                        if (text && text.length > 5 && text.length < 250) {
                            const cleanText = text.replace(/\\n/g, ' ').replace(/\\s+/g, ' ').trim();
                            if (!cleanText.includes('US$') && !cleanText.includes('Get started')) {
                                features.push(cleanText);
                            }
                        }
                    });

                    planData.push({
                        name: planName,
                        price: priceInfo,
                        period: period,
                        features: features.slice(0, 12)
                    });
                });

                if (planData.length === 0) {
                    return [{
                        message: 'Could not locate Canva pricing cards',
                        page_url: window.location.href,
                        debug_info: {
                            has_dollar_sign: pageText.includes('$'),
                            has_plan_names: pageText.match(/Canva Free|Canva Pro|Canva Teams/i) !== null
                        }
                    }];
                }

                return planData;
            }""")

            print("\n==== EXTRACTED CANVA PRICING ====")
            print(json.dumps(pricing_data, indent=2))
            print("==================================\n")

            return {
                "site": "canva",
                "url": page.url,
                "plans": pricing_data
            }

        except Exception as e:
            print(f"  Error extracting Canva pricing: {e}")
            return {
                "site": "canva",
                "url": page.url if hasattr(page, 'url') else "unknown",
                "error": str(e),
                "plans": []
            }

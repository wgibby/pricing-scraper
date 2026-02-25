"""
Evernote-specific handler for clean screenshot capture of pricing pages.
Focuses on getting clean screenshots with dismissed pop-ups and banners.
"""
import json
import random
import time
from .base_handler import BaseSiteHandler

class EvernoteHandler(BaseSiteHandler):
    """Handler for Evernote website with focus on clean screenshots."""

    def __init__(self, name="evernote"):
        super().__init__(name)
        self.detection_level = "LOW"  # Evernote has minimal bot detection

    def get_url(self, country):
        """Get the URL for Evernote pricing page."""
        # Evernote uses the same URL for all countries
        return "https://evernote.com/compare-plans"

    def prepare_context(self, context, country):
        """Prepare context with standard headers."""
        try:
            print("  Preparing Evernote context...")

            # Set standard headers
            context.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "max-age=0",
                "Sec-Ch-Ua": '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
            })

            print("  ✓ Evernote context prepared")

        except Exception as e:
            print(f"  Error preparing Evernote context: {e}")

    def handle_cookie_consent(self, page):
        """Handle cookie consent and privacy banners on Evernote."""
        try:
            print("  Handling Evernote cookie consent...")

            # Wait for page to load
            time.sleep(2)

            # Evernote-specific cookie consent selectors
            evernote_cookie_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                'button:has-text("Accept Cookies")',
                'button:has-text("I Accept")',
                'button:has-text("Got it")',
                'button:has-text("OK")',
                'button:has-text("Continue")',
                '[data-testid="accept-cookies"]',
                '[data-testid="cookie-accept"]',
                '[aria-label="Accept cookies"]',
                '[aria-label="Accept"]',
                '.cookie-banner button',
                '.cookie-consent button',
                '#cookie-banner button',
                'button[class*="accept"]',
                'button[class*="cookie"]',
                'button[id*="accept"]',
                'button[id*="cookie"]'
            ]

            consent_handled = False

            for selector in evernote_cookie_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Found cookie consent button: {selector}")
                        page.click(selector, timeout=3000)
                        page.wait_for_timeout(1000)
                        consent_handled = True
                        break
                except Exception as e:
                    continue

            # Also try to dismiss any overlay modals or pop-ups
            overlay_selectors = [
                'button:has-text("Close")',
                'button:has-text("×")',
                'button:has-text("Dismiss")',
                'button:has-text("No thanks")',
                '[aria-label="Close"]',
                '[aria-label="Dismiss"]',
                '.modal button',
                '.overlay button',
                '.popup button',
                'button[class*="close"]',
                'button[class*="dismiss"]'
            ]

            for selector in overlay_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Dismissing overlay: {selector}")
                        page.click(selector, timeout=2000)
                        page.wait_for_timeout(500)
                        break
                except Exception as e:
                    continue

            # Hide any remaining cookie banners with CSS
            page.evaluate("""() => {
                try {
                    const style = document.createElement('style');
                    style.textContent = `
                        div[class*="cookie"], div[id*="cookie"],
                        div[class*="consent"], div[id*="consent"],
                        div[class*="banner"], div[id*="banner"],
                        div[class*="modal"], div[id*="modal"],
                        div[class*="overlay"], div[id*="overlay"],
                        div[class*="popup"], div[id*="popup"],
                        [data-testid*="cookie"], [data-testid*="consent"],
                        [data-testid*="banner"], [data-testid*="modal"] {
                            display: none !important;
                            opacity: 0 !important;
                            pointer-events: none !important;
                            z-index: -9999 !important;
                        }
                    `;
                    document.head.appendChild(style);
                    console.log('Evernote overlay hiding CSS applied');
                } catch(e) {
                    console.log('CSS overlay hiding failed:', e);
                }
            }""")

            if consent_handled:
                print("  ✓ Cookie consent handled")
            else:
                print("  No cookie consent found (may already be dismissed)")

            return True

        except Exception as e:
            print(f"  Error handling cookie consent: {e}")
            return True  # Don't fail the scrape

    def perform_site_interactions(self, page):
        """Perform interactions to ensure clean pricing content is visible and toggle to Monthly pricing."""
        try:
            print("  Performing Evernote site interactions...")

            # Wait for page to stabilize
            time.sleep(2)

            # Scroll to ensure pricing content is loaded
            page.evaluate("window.scrollTo(0, 300)")
            time.sleep(1)

            # Scroll down to pricing comparison table
            page.evaluate("window.scrollTo(0, 600)")
            time.sleep(1)

            # Toggle to Monthly pricing - this is the key interaction!
            print("  Looking for Monthly/Annual toggle (language-agnostic)...")

            # Language-agnostic approach: look for the first button in toggle groups
            # Since Monthly is typically on the left and Annual on the right
            monthly_toggled = False

            # Strategy 1: Look for common toggle patterns (first button in toggle groups)
            toggle_group_selectors = [
                'div[role="radiogroup"] button:first-child',
                'div[role="tablist"] button:first-child',
                'div[class*="toggle"] button:first-child',
                'div[class*="switch"] button:first-child',
                '[data-testid*="pricing"] button:first-child',
                '[data-testid*="toggle"] button:first-child'
            ]

            for selector in toggle_group_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Found toggle group, clicking first button: {selector}")
                        element = page.locator(selector).first
                        element.click(timeout=3000)
                        page.wait_for_timeout(1500)  # Wait for pricing to update
                        print("  ✓ Clicked first toggle button (should be Monthly)")
                        monthly_toggled = True
                        break
                except Exception as e:
                    print(f"  Failed to click {selector}: {e}")
                    continue

            # Strategy 2: Language-aware JavaScript approach if Strategy 1 fails
            if not monthly_toggled:
                print("  Trying language-aware JavaScript approach...")
                try:
                    monthly_toggled = page.evaluate("""() => {
                        // Multi-language Monthly keywords
                        const monthlyKeywords = [
                            'monthly', 'month', 'mensuel', 'monatlich', 'mensual', 'mensal',
                            'mês', 'meese', 'måned', '月', '월', 'maand', 'महीना', 'bulan',
                            'mėnuo', 'mese', 'miesiąc', 'mesiac', 'měsíc', 'hónap'
                        ];

                        // Multi-language Annual keywords (to avoid clicking these)
                        const annualKeywords = [
                            'annual', 'year', 'yearly', 'annuel', 'jährlich', 'anual', 'anual',
                            'ano', 'année', 'år', '年', '년', 'jaar', 'साल', 'tahun',
                            'metai', 'anno', 'rok', 'rok', 'rok', 'év'
                        ];

                        // Look for buttons in potential toggle areas
                        const buttons = Array.from(document.querySelectorAll('button, div[role="button"], [role="tab"]'));

                        // First, try to find explicit monthly buttons
                        for (const keyword of monthlyKeywords) {
                            const monthlyButton = buttons.find(btn => {
                                const text = (btn.textContent || '').toLowerCase();
                                return text.includes(keyword) && !annualKeywords.some(ak => text.includes(ak));
                            });

                            if (monthlyButton) {
                                console.log(`Found Monthly button with keyword "${keyword}":`, monthlyButton.textContent);
                                monthlyButton.click();
                                return true;
                            }
                        }

                        // Strategy 3: Look for toggle patterns and click the left/first option
                        // Find toggle containers with exactly 2 buttons
                        const toggleContainers = Array.from(document.querySelectorAll('div'));
                        for (const container of toggleContainers) {
                            const containerButtons = container.querySelectorAll(':scope > button');
                            if (containerButtons.length === 2) {
                                // Check if this looks like a pricing toggle
                                const containerText = container.textContent.toLowerCase();
                                const hasPricingIndicators = monthlyKeywords.concat(annualKeywords).some(keyword =>
                                    containerText.includes(keyword)
                                );

                                if (hasPricingIndicators) {
                                    console.log('Found 2-button toggle container, clicking first button:', containerButtons[0].textContent);
                                    containerButtons[0].click();
                                    return true;
                                }
                            }
                        }

                        // Strategy 4: Look for radio inputs with month-related values
                        const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
                        const monthlyRadio = radios.find(radio => {
                            const value = (radio.value || '').toLowerCase();
                            return monthlyKeywords.some(keyword => value.includes(keyword));
                        });

                        if (monthlyRadio) {
                            console.log('Found Monthly radio via value:', monthlyRadio.value);
                            monthlyRadio.click();
                            return true;
                        }

                        console.log('No Monthly toggle found via JavaScript');
                        return false;
                    }""")

                    if monthly_toggled:
                        print("  ✓ Successfully toggled to Monthly via language-aware JavaScript")
                        page.wait_for_timeout(1500)  # Wait for pricing to update
                    else:
                        print("  ⚠ Could not find Monthly toggle - may already be on Monthly or toggle not available")

                except Exception as e:
                    print(f"  JavaScript toggle attempt failed: {e}")

            # Try to expand any collapsed pricing sections
            expand_selectors = [
                'button:has-text("Show more")',
                'button:has-text("View all features")',
                'button:has-text("Compare")',
                '[aria-expanded="false"]',
                'button[class*="expand"]',
                'button[class*="show"]'
            ]

            for selector in expand_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Expanding content: {selector}")
                        page.click(selector, timeout=2000)
                        page.wait_for_timeout(1000)
                        break
                except Exception as e:
                    continue

            # Final scroll to center the pricing content
            page.evaluate("window.scrollTo(0, 400)")
            time.sleep(1)

            # Verify we're showing monthly pricing
            try:
                pricing_verification = page.evaluate("""() => {
                    const pageText = document.body.textContent || '';

                    // Look for monthly indicators (multi-language)
                    const monthlyIndicators = [
                        '/ month', '/month', 'per month', 'monthly', '/mo', 'mês', '/mês',
                        'mensuel', 'monatlich', 'mensual', 'mensal', 'måned', 'maand',
                        '$10.83', '$14.16', '€', '£'  // Expected monthly prices and currencies
                    ];

                    // Look for annual indicators (multi-language)
                    const annualIndicators = [
                        '/ year', '/year', 'per year', 'annually', '/yr', 'ano', '/ano',
                        'annuel', 'jährlich', 'anual', 'år', 'jaar',
                        '$129.99', '$169.99'  // Expected annual prices
                    ];

                    const hasMonthly = monthlyIndicators.some(indicator =>
                        pageText.toLowerCase().includes(indicator.toLowerCase())
                    );

                    const hasAnnual = annualIndicators.some(indicator =>
                        pageText.toLowerCase().includes(indicator.toLowerCase())
                    );

                    // Check which toggle is active
                    const monthlyButton = Array.from(document.querySelectorAll('button')).find(b =>
                        b.textContent && b.textContent.toLowerCase().includes('monthly')
                    );

                    const isMonthlySelected = monthlyButton ?
                        monthlyButton.getAttribute('aria-selected') === 'true' ||
                        monthlyButton.classList.contains('selected') ||
                        monthlyButton.classList.contains('active') ||
                        monthlyButton.hasAttribute('data-selected') : false;

                    return {
                        hasMonthly,
                        hasAnnual,
                        isMonthlySelected,
                        monthlyButtonFound: !!monthlyButton,
                        pageTextSample: pageText.substring(0, 500)
                    };
                }""")

                if pricing_verification['hasMonthly'] and not pricing_verification['hasAnnual']:
                    print("  ✓ Confirmed Monthly pricing is displayed")
                elif pricing_verification['hasAnnual'] and not pricing_verification['hasMonthly']:
                    print("  ⚠ Warning: Still showing Annual pricing")
                elif pricing_verification['hasMonthly'] and pricing_verification['hasAnnual']:
                    print("  ✓ Both Monthly and Annual pricing visible (toggle working)")
                else:
                    print(f"  ? Unable to determine pricing period clearly")
                    print(f"    Monthly button found: {pricing_verification['monthlyButtonFound']}")
                    print(f"    Is selected: {pricing_verification['isMonthlySelected']}")

            except Exception as e:
                print(f"  Could not verify pricing period: {e}")

            print("  ✓ Site interactions completed")

        except Exception as e:
            print(f"  Error in site interactions: {e}")

    def extract_pricing_data(self, page):
        """Extract Evernote pricing data."""
        try:
            print("  Extracting Evernote pricing data...")

            # Wait for content to be ready
            time.sleep(2)

            pricing_data = page.evaluate("""() => {
                const pageText = document.body.textContent || '';

                // Check if we have Evernote pricing content
                const hasEvernotePricing = (
                    (pageText.includes('Personal') || pageText.includes('Professional') || pageText.includes('Enterprise')) &&
                    (pageText.includes('Free') || pageText.includes('$') || pageText.includes('€') || pageText.includes('£')) &&
                    (pageText.includes('month') || pageText.includes('/mo') || pageText.includes('per month'))
                );

                if (!hasEvernotePricing) {
                    return [{
                        message: 'No Evernote pricing content detected',
                        page_url: window.location.href,
                        page_title: document.title,
                        content_sample: pageText.substring(0, 300)
                    }];
                }

                // Look for Evernote plan elements
                const planSelectors = [
                    '[data-testid*="plan"]',
                    '[data-testid*="pricing"]',
                    'div:has-text("Personal"):has-text(/[€$£]/)',
                    'div:has-text("Professional"):has-text(/[€$£]/)',
                    'div:has-text("Enterprise"):has-text(/[€$£]/)',
                    'div:has-text("Free")',
                    '.pricing-card',
                    '.plan-card',
                    '[class*="plan"]',
                    '[class*="pricing"]'
                ];

                let plans = [];

                for (const selector of planSelectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            plans = Array.from(elements);
                            console.log(`Found ${plans.length} plans with: ${selector}`);
                            break;
                        }
                    } catch(e) {
                        continue;
                    }
                }

                // Fallback: look for elements containing plan names
                if (plans.length === 0) {
                    const allElements = Array.from(document.querySelectorAll('*'));
                    const planElements = allElements.filter(el => {
                        const text = el.textContent || '';
                        return (text.includes('Personal') || text.includes('Professional') || text.includes('Enterprise') || text.includes('Free')) &&
                               text.length < 1000 &&
                               el.offsetHeight > 20;
                    });

                    if (planElements.length > 0) {
                        plans = planElements.slice(0, 6);
                    }
                }

                if (plans.length === 0) {
                    return [{
                        message: 'Could not locate Evernote pricing elements',
                        page_url: window.location.href,
                        debug_info: {
                            page_title: document.title,
                            has_plan_text: pageText.includes('Personal') || pageText.includes('Professional'),
                            has_currency: pageText.includes('€') || pageText.includes('$'),
                            page_length: pageText.length
                        }
                    }];
                }

                // Extract plan information
                return plans.map((plan, index) => {
                    const planText = plan.textContent || '';

                    // Extract plan name
                    let name = '';
                    if (planText.match(/free/i)) name = 'Free';
                    else if (planText.match(/personal/i)) name = 'Personal';
                    else if (planText.match(/professional/i)) name = 'Professional';
                    else if (planText.match(/enterprise/i)) name = 'Enterprise';
                    else name = `Plan ${index + 1}`;

                    // Extract price information
                    let priceInfo = {
                        display: 'Free',
                        numeric: 0,
                        currency: null
                    };

                    if (!planText.match(/free/i)) {
                        // Try different currency patterns
                        let priceMatch = planText.match(/€\\s*(\\d+[,.]\\d+)/);
                        if (priceMatch) {
                            const price = parseFloat(priceMatch[1].replace(',', '.'));
                            priceInfo = {
                                display: `€${price}`,
                                numeric: price,
                                currency: '€'
                            };
                        } else {
                            priceMatch = planText.match(/\\$\\s*(\\d+[.]\\d+)/);
                            if (priceMatch) {
                                const price = parseFloat(priceMatch[1]);
                                priceInfo = {
                                    display: `$${price}`,
                                    numeric: price,
                                    currency: '$'
                                };
                            } else {
                                priceMatch = planText.match(/£\\s*(\\d+[.]\\d+)/);
                                if (priceMatch) {
                                    const price = parseFloat(priceMatch[1]);
                                    priceInfo = {
                                        display: `£${price}`,
                                        numeric: price,
                                        currency: '£'
                                    };
                                }
                            }
                        }
                    }

                    // Extract features
                    const features = [];

                    // Look for common Evernote features
                    if (planText.match(/\\d+\\s*notes?/i)) {
                        const notesMatch = planText.match(/(\\d+[,.]?\\d*)\\s*notes?/i);
                        if (notesMatch) features.push(`${notesMatch[1]} notes`);
                    }
                    if (planText.match(/\\d+\\s*notebooks?/i)) {
                        const notebooksMatch = planText.match(/(\\d+[,.]?\\d*)\\s*notebooks?/i);
                        if (notebooksMatch) features.push(`${notebooksMatch[1]} notebooks`);
                    }
                    if (planText.match(/\\d+\\s*(mb|gb)/i)) {
                        const uploadMatch = planText.match(/(\\d+\\s*(?:mb|gb))/i);
                        if (uploadMatch) features.push(`${uploadMatch[1]} monthly upload`);
                    }
                    if (planText.match(/sync/i)) features.push('Device sync');
                    if (planText.match(/offline/i)) features.push('Offline access');
                    if (planText.match(/pdf/i)) features.push('PDF annotation');
                    if (planText.match(/search/i)) features.push('Search in documents');

                    return {
                        name,
                        price: priceInfo,
                        features: [...new Set(features)].slice(0, 6)
                    };
                });
            }""")

            print(f"\n==== EXTRACTED EVERNOTE PRICING ====")
            print(json.dumps(pricing_data, indent=2))
            print("====================================\n")

            return {
                "site": "evernote",
                "url": page.url,
                "plans": pricing_data
            }

        except Exception as e:
            print(f"  Error extracting Evernote pricing: {e}")
            return {
                "site": "evernote",
                "url": page.url if hasattr(page, 'url') else "unknown",
                "error": str(e),
                "plans": []
            }
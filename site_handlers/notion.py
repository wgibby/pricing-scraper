"""
Notion-specific handler for the pricing scraper.
"""
import json
from .base_handler import BaseSiteHandler

class NotionHandler(BaseSiteHandler):
    """Handler for Notion website."""

    def __init__(self, name="notion"):
        super().__init__(name)

    def get_url(self, country):
        """
        Get the URL for Notion pricing page.
        Notion doesn't have country-specific URLs, so we use the main pricing URL.

        Args:
            country (str): Country code (ignored for Notion)

        Returns:
            str: URL for Notion pricing
        """
        return "https://www.notion.com/pricing"

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
                    "domain": ".notion.com",
                    "path": "/"
                },
                {
                    "name": "OptanonConsent",
                    "value": "isGpcEnabled=0&datestamp=Wed+May+15+2023+12%3A00%3A00+GMT%2B0100+(BST)&version=202209.1.0&isIABGlobal=false&hosts=&consentId=12345&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&geolocation=GB%3BENG&AwaitingReconsent=false",
                    "domain": ".notion.com",
                    "path": "/"
                },
                {
                    "name": "cookieConsent",
                    "value": "true",
                    "domain": ".notion.com",
                    "path": "/"
                }
            ])
            print("  Added pre-acceptance cookies for Notion")
        except Exception as e:
            print(f"  Error setting pre-acceptance cookies: {e}")

    def handle_cookie_consent(self, page):
        """
        Handle Notion's specific cookie consent banner.

        Args:
            page (Page): Playwright page object

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("  Applying Notion-specific cookie handling...")

            # Try clicking common cookie consent buttons
            accept_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                'button:has-text("Accept All Cookies")',
                'button:has-text("Got it")',
                'button:has-text("I understand")',
                '[data-testid="cookie-consent-accept"]',
                '.cookie-banner button:nth-child(2)',
                '#onetrust-accept-btn-handler',
                'button.accept-all-cookies'
            ]

            for selector in accept_selectors:
                if page.locator(selector).count() > 0:
                    print(f"  Found Notion cookie button: {selector}")
                    page.click(selector)
                    page.wait_for_timeout(1000)
                    return True

            # Try direct JavaScript approach
            result = page.evaluate("""() => {
                // Find buttons with Accept or similar text
                const buttons = Array.from(document.querySelectorAll('button'));
                const acceptButton = buttons.find(btn =>
                    btn.textContent.toLowerCase().match(/accept|got it|i understand|allow/)
                );

                if (acceptButton) {
                    acceptButton.click();
                    return true;
                }

                // Try finding the cookie banner and its buttons
                const cookieBanner = document.querySelector('.cookie-banner, #cookie-banner, [class*="cookie"], [role="banner"]');
                if (cookieBanner) {
                    const bannerButtons = cookieBanner.querySelectorAll('button');
                    if (bannerButtons.length >= 1) {
                        // Click the last button (usually Accept)
                        bannerButtons[bannerButtons.length - 1].click();
                        return true;
                    }
                }

                return false;
            }""")

            if result:
                print("  Clicked Notion cookie button via JavaScript")
                page.wait_for_timeout(1000)
                return True

            # If clicking fails, try removing the banner from DOM
            self._remove_cookie_banner(page)
            self._hide_cookie_banner_with_css(page)

            return False
        except Exception as e:
            print(f"  Error handling Notion cookies: {e}")
            return False

    def _remove_cookie_banner(self, page):
        """Remove Notion cookie banner from the DOM."""
        try:
            result = page.evaluate("""() => {
                // Find cookie banner elements
                const banners = [
                    document.querySelector('.cookie-banner'),
                    document.querySelector('#cookie-banner'),
                    document.querySelector('#onetrust-banner-sdk'),
                    document.querySelector('[role="alertdialog"]'),
                    document.querySelector('[class*="cookie"]'),
                    document.querySelector('[class*="banner"]')
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
                document.cookie = "cookieConsent=true; path=/; max-age=31536000";

                return removed;
            }""")

            if result:
                print("  Removed Notion cookie banner from DOM")
                return True
            return False
        except Exception as e:
            print(f"  Error removing Notion cookie banner: {e}")
            return False

    def _hide_cookie_banner_with_css(self, page):
        """Use CSS to hide Notion's cookie banner."""
        try:
            page.add_style_tag(content="""
                /* Hide Notion cookie banner */
                .cookie-banner, #cookie-banner, #onetrust-banner-sdk,
                [class*="cookie-banner"], [class*="cookie_banner"],
                [class*="cookieBanner"], div[role="alertdialog"],
                [class*="banner"][class*="cookie"] {
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
            print("  Applied CSS to hide Notion cookie banner")
            return True
        except Exception as e:
            print(f"  Error hiding Notion cookie banner with CSS: {e}")
            return False

    def perform_site_interactions(self, page):
        """
        Perform Notion-specific interactions needed to reveal pricing content.

        Args:
            page (Page): Playwright page object
        """
        try:
            # Wait a moment for page to stabilize
            page.wait_for_timeout(2000)

            # Scroll down to ensure all pricing content is visible
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
            page.wait_for_timeout(1000)

            # Toggle to Monthly pricing using specific selector
            print("  Looking for Monthly pricing toggle...")

            monthly_toggled = False

            # Strategy 1: Use the specific selector for Notion's billing interval radio button
            specific_selector = 'input[name="billingInterval"][value="month"]'

            try:
                # Wait for the billing interval radio buttons to be available
                print(f"  Waiting for billing interval selector: {specific_selector}")
                page.wait_for_selector('input[name="billingInterval"]', timeout=5000)

                if page.locator(specific_selector).count() > 0:
                    print(f"  Found monthly billing radio button: {specific_selector}")
                    # Click the monthly radio button
                    page.click(specific_selector)
                    page.wait_for_timeout(1000)  # Wait for prices to update
                    print("  ✓ Clicked monthly billing radio button")
                    monthly_toggled = True
                else:
                    print(f"  Monthly radio button not found with selector: {specific_selector}")

            except Exception as e:
                print(f"  Failed to click specific monthly selector: {e}")

            # Strategy 2: Fallback to clicking the label or parent element
            if not monthly_toggled:
                print("  Trying to click monthly option via label...")
                try:
                    # Try clicking the label for the monthly radio button
                    label_selector = 'label[for=":r0:"]'
                    if page.locator(label_selector).count() > 0:
                        print(f"  Found monthly label: {label_selector}")
                        page.click(label_selector)
                        page.wait_for_timeout(1000)
                        print("  ✓ Clicked monthly billing label")
                        monthly_toggled = True
                    else:
                        # Try finding by text content
                        monthly_text_selector = 'text="Pay monthly"'
                        if page.locator(monthly_text_selector).count() > 0:
                            print(f"  Found monthly text: {monthly_text_selector}")
                            page.click(monthly_text_selector)
                            page.wait_for_timeout(1000)
                            print("  ✓ Clicked monthly billing text")
                            monthly_toggled = True
                        else:
                            print("  No monthly label or text found")

                except Exception as e:
                    print(f"  Failed to click monthly label/text: {e}")

            # Strategy 3: JavaScript approach to find and click the monthly radio button
            if not monthly_toggled:
                print("  Trying JavaScript approach to click monthly radio button...")
                try:
                    monthly_toggled = page.evaluate("""() => {
                        // Look for the specific radio button first
                        const monthlyRadio = document.querySelector('input[name="billingInterval"][value="month"]');
                        if (monthlyRadio) {
                            console.log('Found monthly radio button, clicking...');
                            monthlyRadio.click();
                            return true;
                        }

                        // Look for any radio button related to billing interval
                        const billingRadios = document.querySelectorAll('input[name="billingInterval"]');
                        if (billingRadios.length >= 2) {
                            // Assume first one is monthly, second is yearly
                            console.log('Found billing radio buttons, clicking first one (monthly)...');
                            billingRadios[0].click();
                            return true;
                        }

                        // Look for text content approach
                        const allInputs = document.querySelectorAll('input[type="radio"]');
                        for (const input of allInputs) {
                            const label = document.querySelector(`label[for="${input.id}"]`);
                            if (label && label.textContent.toLowerCase().includes('month')) {
                                console.log('Found monthly radio via label text, clicking...');
                                input.click();
                                return true;
                            }
                        }

                        console.log('No monthly radio button found via JavaScript');
                        return false;
                    }""")

                    if monthly_toggled:
                        print("  ✓ Successfully clicked monthly radio button via JavaScript")
                        page.wait_for_timeout(1000)  # Wait for pricing to update
                    else:
                        print("  ⚠ Could not find monthly radio button via JavaScript")

                except Exception as e:
                    print(f"  JavaScript radio button click failed: {e}")

            # Strategy 4: Legacy fallback approach (from original code)
            if not monthly_toggled:
                print("  Trying legacy fallback approach...")
                try:
                    monthly_toggled = page.evaluate("""() => {
                        // Multi-language Monthly keywords
                        const monthlyKeywords = [
                            'monthly', 'month', 'mensuel', 'monatlich', 'mensual', 'mensal',
                            'mês', 'meese', 'måned', '月', '월', 'maand', 'महीना', 'bulan'
                        ];

                        // Look for buttons in potential toggle areas
                        const buttons = Array.from(document.querySelectorAll('button, div[role="button"], [role="tab"]'));

                        // Try to find explicit monthly buttons
                        for (const keyword of monthlyKeywords) {
                            const monthlyButton = buttons.find(btn => {
                                const text = (btn.textContent || '').toLowerCase();
                                return text.includes(keyword);
                            });

                            if (monthlyButton) {
                                console.log(`Found Monthly button with keyword "${keyword}":`, monthlyButton.textContent);
                                monthlyButton.click();
                                return true;
                            }
                        }

                        console.log('No Monthly toggle found via legacy approach');
                        return false;
                    }""")

                    if monthly_toggled:
                        print("  ✓ Successfully toggled to Monthly via legacy approach")
                        page.wait_for_timeout(1500)  # Wait for pricing to update

                except Exception as e:
                    print(f"  Legacy approach failed: {e}")

            # Final check: verify we're on monthly pricing
            if not monthly_toggled:
                print("  ⚠ All monthly toggle attempts failed - proceeding with current pricing display")

            # Verify we're showing monthly pricing and check radio button state
            page.wait_for_timeout(1000)
            try:
                pricing_verification = page.evaluate("""() => {
                    const pageText = document.body.textContent || '';

                    // Check radio button state
                    const monthlyRadio = document.querySelector('input[name="billingInterval"][value="month"]');
                    const yearlyRadio = document.querySelector('input[name="billingInterval"][value="year"]');

                    const radioButtonInfo = {
                        monthlyFound: !!monthlyRadio,
                        yearlyFound: !!yearlyRadio,
                        monthlyChecked: monthlyRadio ? monthlyRadio.checked : false,
                        yearlyChecked: yearlyRadio ? yearlyRadio.checked : false
                    };

                    // Look for monthly indicators (multi-language)
                    const monthlyIndicators = [
                        '/ month', '/month', 'per month', 'monthly', '/mo', 'mês', '/mês',
                        'mensuel', 'monatlich', 'mensual', 'mensal', 'måned', 'maand'
                    ];

                    // Look for annual indicators (multi-language)
                    const annualIndicators = [
                        '/ year', '/year', 'per year', 'annually', '/yr', 'ano', '/ano',
                        'annuel', 'jährlich', 'anual', 'år', 'jaar'
                    ];

                    const hasMonthly = monthlyIndicators.some(indicator =>
                        pageText.toLowerCase().includes(indicator.toLowerCase())
                    );

                    const hasAnnual = annualIndicators.some(indicator =>
                        pageText.toLowerCase().includes(indicator.toLowerCase())
                    );

                    return {
                        hasMonthly,
                        hasAnnual,
                        radioButtonInfo,
                        pageTextSample: pageText.substring(0, 500)
                    };
                }""")

                radio_info = pricing_verification['radioButtonInfo']

                print(f"  Radio button status:")
                print(f"    Monthly radio found: {radio_info['monthlyFound']}")
                print(f"    Yearly radio found: {radio_info['yearlyFound']}")
                print(f"    Monthly checked: {radio_info['monthlyChecked']}")
                print(f"    Yearly checked: {radio_info['yearlyChecked']}")

                if radio_info['monthlyChecked']:
                    print("  ✓ Confirmed Monthly radio button is selected")
                elif radio_info['yearlyChecked']:
                    print("  ⚠ Warning: Yearly radio button is selected")
                else:
                    print("  ? Could not determine radio button selection state")

                if pricing_verification['hasMonthly'] and not pricing_verification['hasAnnual']:
                    print("  ✓ Confirmed Monthly pricing is displayed in content")
                elif pricing_verification['hasAnnual'] and not pricing_verification['hasMonthly']:
                    print("  ⚠ Warning: Still showing Annual pricing in content")
                elif pricing_verification['hasMonthly'] and pricing_verification['hasAnnual']:
                    print("  ✓ Both Monthly and Annual pricing visible in content")
                else:
                    print(f"  ? Unable to determine pricing period from content")

            except Exception as e:
                print(f"  Could not verify pricing period: {e}")

            # Scroll to make sure all plan features are visible
            page.evaluate("""() => {
                // Find pricing plan sections
                const planSections = document.querySelectorAll('[class*="plan"], [class*="pricing"], [class*="card"]');

                if (planSections.length > 0) {
                    // Scroll to the middle of the pricing section
                    const lastPlan = planSections[planSections.length - 1];
                    lastPlan.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    // Fallback scroll
                    window.scrollTo(0, document.body.scrollHeight * 0.7);
                }
            }""")

            # Wait for scroll and any dynamic content loading
            page.wait_for_timeout(2000)

        except Exception as e:
            print(f"  Error in Notion site interactions: {e}")

    def extract_pricing_data(self, page):
        """
        Extract Notion pricing details.

        Args:
            page (Page): Playwright page object

        Returns:
            dict: Extracted pricing data
        """
        try:
            pricing_data = page.evaluate("""() => {
                // Find pricing plan containers - Notion uses various class names
                const planSelectors = [
                    '[class*="plan"]',
                    '[class*="pricing"]',
                    '[class*="card"]',
                    '[data-testid*="plan"]',
                    'div:has-text("Free"):has-text("$"):not(nav)',
                    'div:has-text("Plus"):has-text("$"):not(nav)',
                    'div:has-text("Business"):has-text("$"):not(nav)',
                    'div:has-text("Enterprise"):has-text("$"):not(nav)'
                ];

                let plans = [];

                // Try each selector until we find plans
                for (const selector of planSelectors) {
                    try {
                        const elements = Array.from(document.querySelectorAll(selector));
                        if (elements.length > 0) {
                            // Filter to likely pricing plans
                            plans = elements.filter(el => {
                                const text = el.textContent || '';
                                return text.includes('$') || text.includes('Free') || text.includes('Plus') || text.includes('Business') || text.includes('Enterprise');
                            });

                            if (plans.length > 0) {
                                console.log(`Found ${plans.length} plans with selector: ${selector}`);
                                break;
                            }
                        }
                    } catch(e) {
                        continue;
                    }
                }

                // If no plans found with specific selectors, try a broader approach
                if (plans.length === 0) {
                    console.log('No plans found with specific selectors, trying broader search...');

                    // Look for elements that contain Notion plan names and pricing
                    const allElements = Array.from(document.querySelectorAll('*'));
                    const priceElements = allElements.filter(el => {
                        const text = el.textContent || '';
                        const hasPrice = text.match(/\$\s*\d+/) || text.includes('Free');
                        const isPlan = text.match(/Free|Plus|Business|Enterprise/i);
                        const isReasonableSize = text.length < 1000 && el.offsetHeight > 50;
                        return hasPrice && isPlan && isReasonableSize;
                    });

                    if (priceElements.length > 0) {
                        plans = priceElements.slice(0, 6); // Limit to 6 plans max
                        console.log(`Found ${plans.length} plans with broader search`);
                    }
                }

                if (plans.length === 0) {
                    return [{
                        message: 'No Notion pricing plans found',
                        debug_info: {
                            page_title: document.title,
                            page_url: window.location.href,
                            has_dollar_sign: document.body.textContent.includes('$'),
                            has_plan_names: document.body.textContent.match(/Free|Plus|Business|Enterprise/i) !== null
                        }
                    }];
                }

                // Extract data from each plan
                return plans.map((plan, index) => {
                    const planText = plan.textContent || '';

                    // Extract plan name
                    let name = 'Unknown Plan';
                    if (planText.match(/free/i)) name = 'Free';
                    else if (planText.match(/plus/i)) name = 'Plus';
                    else if (planText.match(/business/i)) name = 'Business';
                    else if (planText.match(/enterprise/i)) name = 'Enterprise';
                    else if (planText.match(/personal/i)) name = 'Personal';
                    else if (planText.match(/team/i)) name = 'Team';

                    // If still unknown, try to find heading elements
                    if (name === 'Unknown Plan') {
                        const heading = plan.querySelector('h1, h2, h3, h4, h5, h6, [class*="title"], [class*="heading"]');
                        if (heading && heading.textContent) {
                            name = heading.textContent.trim().split(' ')[0]; // Take first word
                        } else {
                            name = `Plan ${index + 1}`;
                        }
                    }

                    // Extract price information
                    let priceInfo = {
                        display: 'Price not found',
                        numeric: null,
                        currency: '$'
                    };

                    // Look for price patterns
                    const priceMatch = planText.match(/\$\s*(\d+(?:\.\d+)?)/);
                    if (priceMatch) {
                        const price = parseFloat(priceMatch[1]);
                        priceInfo = {
                            display: `$${price}`,
                            numeric: price,
                            currency: '$'
                        };
                    } else if (planText.match(/free/i)) {
                        priceInfo = {
                            display: 'Free',
                            numeric: 0,
                            currency: '$'
                        };
                    }

                    // Extract billing period
                    let period = '';
                    if (planText.match(/month|monthly|\/mo/i)) period = 'monthly';
                    else if (planText.match(/year|yearly|annual|\/yr/i)) period = 'yearly';
                    else if (planText.match(/per user/i)) period = 'per user';

                    // Extract features
                    const features = [];

                    // Look for feature lists within the plan element
                    const featureElements = plan.querySelectorAll('li, [class*="feature"], [class*="benefit"]');
                    featureElements.forEach(el => {
                        const text = el.textContent?.trim();
                        if (text && text.length > 5 && text.length < 200 && !text.includes('$')) {
                            features.push(text);
                        }
                    });

                    // If no specific feature elements, look for common Notion features in the text
                    if (features.length === 0) {
                        const commonFeatures = [
                            'Unlimited pages',
                            'Unlimited blocks',
                            'Share with guests',
                            'Sync across devices',
                            'Version history',
                            'Unlimited team members',
                            'Collaboration workspace',
                            'Admin tools',
                            'Advanced permissions',
                            'Bulk PDF export',
                            'Advanced security',
                            'Audit log',
                            'SAML SSO',
                            'Custom contracts'
                        ];

                        commonFeatures.forEach(feature => {
                            if (planText.toLowerCase().includes(feature.toLowerCase())) {
                                features.push(feature);
                            }
                        });
                    }

                    return {
                        name,
                        price: priceInfo,
                        period,
                        features: features.slice(0, 10) // Limit to 10 features
                    };
                });
            }""")

            print("\n==== EXTRACTED NOTION PRICING ====")
            print(json.dumps(pricing_data, indent=2))
            print("===================================\n")

            # Format the final result
            result = {
                "site": "notion",
                "url": page.url,
                "plans": pricing_data
            }

            return result
        except Exception as e:
            print(f"  Error extracting Notion pricing: {e}")
            return {
                "site": "notion",
                "url": page.url,
                "error": str(e),
                "plans": []
            }
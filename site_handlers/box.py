"""
Box-specific handler for the pricing scraper.
Handles monthly/yearly toggle (defaults to annual, needs to switch to monthly).
"""
from .base_handler import BaseSiteHandler

class BoxHandler(BaseSiteHandler):
    """Handler for Box website."""

    def __init__(self, name="box"):
        super().__init__(name)
        self.detection_level = "HIGH"  # Box has strong bot detection - use Firefox
        self.use_headless = False  # Run with visible browser to bypass Cloudflare

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
        Get the URL for Box pricing page (individual plans only).
        Box uses a global pricing page.

        Args:
            country (str): Country code (used for geo-targeting but URL is same)

        Returns:
            str: URL for Box individual pricing
        """
        # Try the pricing page directly - Box has strong bot detection
        return "https://www.box.com/pricing/individual"

    def prepare_context(self, context, country):
        """
        Prepare the browser context with additional stealth measures.
        Box has strong Cloudflare protection that shows CAPTCHA challenge.

        Args:
            context (BrowserContext): Playwright browser context
            country (str): Country code
        """
        try:
            print("  Preparing Box context with enhanced anti-Cloudflare measures...")

            # Set additional headers to look more like a real browser
            context.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            })

            # Add stealth scripts to mask automation
            context.add_init_script("""
                // Overwrite the navigator.webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Overwrite Chrome runtime
                window.chrome = {
                    runtime: {}
                };

                // Overwrite permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // Add plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Add languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)

            print("  ✓ Box context prepared with enhanced anti-detection")

        except Exception as e:
            print(f"  Error preparing Box context: {e}")

    def verify_pricing_page_loaded(self, page):
        """
        Verify that we're actually on the pricing page and not on Cloudflare challenge.
        Box has Cloudflare protection that shows CAPTCHA challenge.

        Args:
            page (Page): Playwright page object

        Returns:
            bool: True if on pricing page, False if blocked/challenged
        """
        try:
            current_url = page.url
            print(f"  Current URL after navigation: {current_url}")

            # Check if we got redirected to homepage
            if current_url == "https://www.box.com/" or "/pricing" not in current_url:
                print(f"  ⚠️ WARNING: Redirected away from pricing page to: {current_url}")
                return False

            # Check for Cloudflare challenge page
            print("  Checking for Cloudflare challenge...")
            is_cloudflare = page.evaluate("""() => {
                const bodyText = document.body.textContent || '';
                const pageHtml = document.documentElement.outerHTML || '';

                // Check for Cloudflare indicators
                if (bodyText.includes('Verify you are human') ||
                    bodyText.includes('verify you are human') ||
                    pageHtml.includes('cloudflare') ||
                    document.querySelector('[name="cf-turnstile-response"]') ||
                    document.querySelector('.cf-browser-verification') ||
                    document.querySelector('#challenge-form')) {
                    return true;
                }
                return false;
            }""")

            if is_cloudflare:
                print("  ⚠️ Cloudflare challenge detected - waiting up to 60 seconds...")

                # Wait and check periodically for challenge to clear
                max_wait = 60  # seconds
                check_interval = 3  # seconds
                checks = max_wait // check_interval

                for i in range(checks):
                    page.wait_for_timeout(check_interval * 1000)

                    # Check if challenge is still present
                    challenge_cleared = page.evaluate("""() => {
                        const bodyText = document.body.textContent || '';

                        // If we still see challenge text, not cleared
                        if (bodyText.includes('Verify you are human') ||
                            bodyText.includes('verify you are human')) {
                            return false;
                        }

                        // Check for pricing indicators
                        const indicators = [
                            'button.pricing-toggle-button',
                            '#pricing-toggle-checkbox',
                            '.pricing-card'
                        ];

                        for (const selector of indicators) {
                            if (document.querySelector(selector)) {
                                return true;
                            }
                        }

                        // Check for price text
                        return bodyText.match(/\$\d+/) !== null;
                    }""")

                    if challenge_cleared:
                        print(f"  ✓ Cloudflare challenge cleared after {(i+1) * check_interval}s")
                        return True
                    else:
                        print(f"  Still waiting for challenge ({(i+1) * check_interval}/{max_wait}s)...")

                print("  ✗ Cloudflare challenge not cleared within timeout")
                return False

            # Wait for pricing-specific content to load
            print("  Waiting for pricing content to load...")

            # Try to find pricing indicators
            pricing_loaded = page.evaluate("""() => {
                // Look for various pricing indicators
                const indicators = [
                    'button.pricing-toggle-button',
                    '#pricing-toggle-checkbox',
                    '.pricing-card',
                    '.plan-card',
                    '[class*="pricing"]'
                ];

                for (const selector of indicators) {
                    if (document.querySelector(selector)) {
                        console.log('Found pricing indicator:', selector);
                        return true;
                    }
                }

                // Check for price text in the page
                const bodyText = document.body.innerText || '';
                if (bodyText.match(/\$\d+/)) {
                    console.log('Found price indicators in text');
                    return true;
                }

                return false;
            }""")

            if pricing_loaded:
                print("  ✓ Pricing content detected on page")
                return True
            else:
                print("  ⚠️ No pricing content detected - may need longer wait")
                # Give it more time
                page.wait_for_timeout(3000)

                # Try again
                pricing_loaded_retry = page.evaluate("""() => {
                    const bodyText = document.body.innerText || '';
                    return bodyText.match(/\$\d+/) !== null;
                }""")

                if pricing_loaded_retry:
                    print("  ✓ Pricing content detected after retry")
                    return True
                else:
                    print("  ✗ Still no pricing content found")
                    return False

        except Exception as e:
            print(f"  Error verifying pricing page: {e}")
            return False

    def handle_cookie_consent(self, page):
        """
        Handle Box's cookie consent banner.

        Args:
            page (Page): Playwright page object

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("  Handling Box cookie consent...")

            # Wait for page to load
            page.wait_for_timeout(2000)

            # Box-specific cookie consent selectors
            cookie_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                'button:has-text("Accept all cookies")',
                'button:has-text("Got it")',
                'button:has-text("OK")',
                'button:has-text("Allow")',
                '[data-testid="cookie-accept"]',
                '[aria-label="Accept cookies"]',
                'button[class*="accept"]',
                'button[class*="cookie"]',
                '#onetrust-accept-btn-handler'
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
                        div[class*="banner"], div[id*="banner"],
                        #onetrust-banner-sdk, #onetrust-consent-sdk {
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
        Perform Box-specific interactions to toggle to Monthly pricing.
        The page defaults to Annual, so we need to click the Monthly button.

        Args:
            page (Page): Playwright page object
        """
        try:
            print("  Performing Box site interactions...")

            # Wait for page to stabilize
            page.wait_for_timeout(3000)

            # Scroll to the pricing cards section - they're further down the page
            # Look for the pricing container and scroll to it
            print("  Scrolling to pricing section...")
            pricing_scrolled = page.evaluate("""() => {
                // Try to find the pricing container
                const pricingSelectors = [
                    '.pricing-cards',
                    '.plans-container',
                    '[class*="pricing"]',
                    '[class*="plans"]',
                    'button.pricing-toggle-button'
                ];

                for (const selector of pricingSelectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        console.log('Found pricing section via:', selector);
                        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        return true;
                    }
                }

                // If we can't find pricing section, scroll to a known position
                console.log('Could not find pricing section, scrolling to estimated position');
                window.scrollTo(0, 800);
                return false;
            }""")

            if pricing_scrolled:
                print("  ✓ Scrolled to pricing section")
            else:
                print("  ⚠ Using fallback scroll position")

            page.wait_for_timeout(2000)

            # Toggle to Monthly pricing
            print("  Looking for Monthly/Annual toggle...")

            monthly_toggled = False

            # Strategy 1: Click the specific Monthly button using the class
            try:
                monthly_button_selector = 'button.pricing-toggle-button.pricing-toggle-button__before'
                if page.locator(monthly_button_selector).count() > 0:
                    print(f"  Found monthly button: {monthly_button_selector}")
                    page.click(monthly_button_selector, timeout=3000)
                    page.wait_for_timeout(1500)  # Wait for prices to update
                    print("  ✓ Clicked Monthly button")
                    monthly_toggled = True
            except Exception as e:
                print(f"  Failed to click monthly button: {e}")

            # Strategy 2: Click the checkbox to toggle (unchecking moves from Annual to Monthly)
            if not monthly_toggled:
                print("  Trying to uncheck the pricing toggle checkbox...")
                try:
                    checkbox_selector = 'input#pricing-toggle-checkbox'
                    if page.locator(checkbox_selector).count() > 0:
                        # Check if it's checked (Annual)
                        is_checked = page.is_checked(checkbox_selector)
                        print(f"  Checkbox is {'checked' if is_checked else 'unchecked'} (Annual={is_checked})")

                        if is_checked:
                            # Uncheck to switch to Monthly
                            page.click(checkbox_selector, timeout=3000)
                            page.wait_for_timeout(1500)
                            print("  ✓ Toggled checkbox to Monthly")
                            monthly_toggled = True
                        else:
                            print("  ✓ Already on Monthly pricing")
                            monthly_toggled = True
                except Exception as e:
                    print(f"  Failed to toggle checkbox: {e}")

            # Strategy 3: JavaScript approach to find and click the monthly button
            if not monthly_toggled:
                print("  Trying JavaScript approach to click Monthly button...")
                try:
                    monthly_toggled = page.evaluate("""() => {
                        // Look for the specific monthly button
                        const monthlyButton = document.querySelector('button.pricing-toggle-button__before');
                        if (monthlyButton) {
                            console.log('Found monthly button via class, clicking...');
                            monthlyButton.click();
                            return true;
                        }

                        // Look for button with "Monthly" text
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const monthlyBtn = buttons.find(btn =>
                            btn.textContent.trim() === 'Monthly'
                        );

                        if (monthlyBtn) {
                            console.log('Found Monthly button via text, clicking...');
                            monthlyBtn.click();
                            return true;
                        }

                        // Try the checkbox approach
                        const checkbox = document.querySelector('#pricing-toggle-checkbox');
                        if (checkbox && checkbox.checked) {
                            console.log('Found checked checkbox (Annual), unchecking to switch to Monthly...');
                            checkbox.click();
                            return true;
                        }

                        console.log('No monthly toggle found via JavaScript');
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

                    // Check checkbox state
                    const checkbox = document.querySelector('#pricing-toggle-checkbox');
                    const isAnnual = checkbox ? checkbox.checked : null;

                    const monthlyIndicators = [
                        '/month', 'per month', 'monthly', '/mo'
                    ];

                    const annualIndicators = [
                        '/year', 'per year', 'annually', '/yr', 'billed yearly', 'Save 25%'
                    ];

                    const hasMonthly = monthlyIndicators.some(indicator =>
                        pageText.toLowerCase().includes(indicator.toLowerCase())
                    );

                    const hasAnnual = annualIndicators.some(indicator =>
                        pageText.toLowerCase().includes(indicator.toLowerCase())
                    );

                    return { hasMonthly, hasAnnual, isAnnual };
                }""")

                print(f"  Checkbox state: {'Annual' if pricing_verification['isAnnual'] else 'Monthly'}")

                if pricing_verification['hasMonthly'] and not pricing_verification['isAnnual']:
                    print("  ✓ Confirmed Monthly pricing is displayed")
                elif pricing_verification['isAnnual']:
                    print("  ⚠ Warning: Still on Annual pricing")
                else:
                    print("  ? Unable to determine pricing period")

            except Exception as e:
                print(f"  Could not verify pricing period: {e}")

            # Scroll to ensure all pricing plans are visible and centered for screenshot
            print("  Final positioning for screenshot...")
            page.evaluate("""() => {
                // Try to find pricing cards and center them in view
                const pricingContainer = document.querySelector('.pricing-cards') ||
                                        document.querySelector('[class*="pricing"]') ||
                                        document.querySelector('button.pricing-toggle-button')?.closest('section');

                if (pricingContainer) {
                    console.log('Centering pricing cards in view');
                    pricingContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    // Scroll up a bit to show the toggle
                    window.scrollBy(0, -150);
                } else {
                    console.log('Using fallback positioning');
                    window.scrollTo(0, 600);
                }
            }""")
            page.wait_for_timeout(2000)

            print("  ✓ Site interactions completed")

        except Exception as e:
            print(f"  Error in Box site interactions: {e}")

    def extract_pricing_data(self, page):
        """
        Extract Box pricing details.

        NOTE: JSON extraction disabled per user request - focusing on clean screenshots.
        This method is kept for compatibility but returns minimal data.

        Args:
            page (Page): Playwright page object

        Returns:
            dict: Minimal pricing data (screenshots are the primary output)
        """
        try:
            print("  Box pricing extraction (screenshot-focused mode)")

            return {
                "site": "box",
                "url": page.url,
                "note": "Screenshot-based extraction - JSON disabled per user preference",
                "plans": []
            }

        except Exception as e:
            print(f"  Error in Box pricing data method: {e}")
            return {
                "site": "box",
                "url": page.url if hasattr(page, 'url') else "unknown",
                "error": str(e),
                "plans": []
            }

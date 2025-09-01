import time
from typing import Dict, List, Optional, Any
from .base_handler import BaseSiteHandler

class FigmaHandler(BaseSiteHandler):
    """Handler for Figma pricing pages with proven silent cookie approach."""
    
    def __init__(self, name="figma"):
        super().__init__(name)
        self.base_url = "https://www.figma.com"
        
        # Currency patterns that work (copied from Netflix handler approach)
        self.currency_patterns = {
            "us": {"currencies": ["$"], "locale": "en-US"},
            "uk": {"currencies": ["£"], "locale": "en-GB"},
            "de": {"currencies": ["€"], "locale": "de-DE"},
            "fr": {"currencies": ["€"], "locale": "fr-FR"},
            "es": {"currencies": ["€"], "locale": "es-ES"},
            "it": {"currencies": ["€"], "locale": "it-IT"},
            "nl": {"currencies": ["€"], "locale": "nl-NL"},
            "jp": {"currencies": ["¥", "￥"], "locale": "ja-JP"},
            "ca": {"currencies": ["$"], "locale": "en-CA"},
            "au": {"currencies": ["$"], "locale": "en-AU"},
            "in": {"currencies": ["$"], "locale": "en-IN"},
        }
        
        # Figma-specific selectors
        self.selectors = {
            "pricing_cards": [
                '[data-testid="pricing-card"]',
                '.pricing-card',
                '[class*="pricing-tier"]',
                '[class*="plan-card"]',
                'div[class*="plan"]'
            ],
            "plan_names": [
                'h3[class*="plan"]',
                'h2[class*="plan"]',
                '.plan-name',
                '[data-testid="plan-name"]'
            ],
            "prices": [
                '[data-testid="price"]',
                '.price',
                '[class*="price-amount"]',
                '[class*="cost"]'
            ],
            "features": [
                'li',
                '[class*="feature"]',
                '[class*="benefit"]'
            ],
            "billing_toggle": [
                '[class*="toggle"]',
                '[data-testid="billing-toggle"]',
                'button:has-text("Monthly")',
                'button:has-text("Annual")'
            ]
        }

    def get_stealth_browser_args(self):
        """Get browser arguments that handle detection well."""
        return [
            "--disable-extensions",
            "--disable-gpu",
            "--no-sandbox", 
            "--disable-dev-shm-usage",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-back-forward-cache",
            "--disable-component-update",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--allow-pre-commit-input",
            "--disable-hang-monitor",
            "--disable-ipc-flooding-protection",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--disable-renderer-backgrounding",
            "--force-color-profile=srgb",
            "--metrics-recording-only",
            "--no-first-run",
            "--enable-automation",
            "--password-store=basic",
            "--use-mock-keychain",
            "--no-service-autorun",
            "--headless",
            "--hide-scrollbars",
            "--mute-audio"
        ]

    def prepare_context(self, context, country):
        """Prepare context with SILENT cookie setting like Netflix/Spotify."""
        print(f"  Preparing Figma context for {country.upper()} with silent cookies...")
        
        country_config = self.currency_patterns.get(country.lower(), self.currency_patterns["us"])
        locale = country_config["locale"]
        
        # Set headers
        try:
            context.set_extra_http_headers({
                "Accept-Language": f"{locale},{locale[:2]};q=0.9,en;q=0.8",
                "CF-IPCountry": country.upper(),
                "sec-ch-ua": '"Chromium";v="112", "Google Chrome";v="112"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1"
            })
            print(f"  Set locale to {locale}")
        except Exception as e:
            print(f"  Warning: Could not set headers: {e}")

        # Set comprehensive cookies BEFORE page load (like successful handlers)
        try:
            context.add_cookies([
                # Figma-specific preference cookies
                {
                    "name": "preferred_locale",
                    "value": locale,
                    "domain": ".figma.com",
                    "path": "/"
                },
                {
                    "name": "country_code", 
                    "value": country.upper(),
                    "domain": ".figma.com",
                    "path": "/"
                },
                # Comprehensive consent cookies (covering all major systems)
                {
                    "name": "OptanonAlertBoxClosed",
                    "value": "2024-07-13T12:00:00.000Z",
                    "domain": ".figma.com",
                    "path": "/"
                },
                {
                    "name": "OptanonConsent", 
                    "value": "isGpcEnabled=0&datestamp=Sat+Jul+13+2024+12%3A00%3A00+GMT%2B0000+(UTC)&version=202407.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=12345&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1%2CC0005%3A1&geolocation=%3B&AwaitingReconsent=false",
                    "domain": ".figma.com",
                    "path": "/"
                },
                {
                    "name": "CookieConsent",
                    "value": "true",
                    "domain": ".figma.com",
                    "path": "/"
                },
                {
                    "name": "cookieConsent",
                    "value": "true", 
                    "domain": ".figma.com",
                    "path": "/"
                },
                # CybotCookiebot specific (seen in screenshots)
                {
                    "name": "CybotCookiebotDialogClosed",
                    "value": "true",
                    "domain": ".figma.com", 
                    "path": "/"
                },
                # GDPR compliance
                {
                    "name": "euconsent-v2",
                    "value": "accepted",
                    "domain": ".figma.com",
                    "path": "/"
                }
            ])
            print("  ✓ Set comprehensive consent cookies pre-page-load")
        except Exception as e:
            print(f"  Warning: Could not set preference cookies: {e}")

    def get_url(self, country):
        """Get the pricing URL for a specific country with proper localization paths."""
        country = country.lower()
        
        # Based on debug results - use actual working URL patterns
        localized_urls = {
            'fr': 'https://www.figma.com/fr/pricing/',
            'de': 'https://www.figma.com/de/pricing/',
            # IT and IN don't have localized pages - use main USD page
            'it': 'https://www.figma.com/pricing/',
            'in': 'https://www.figma.com/pricing/',
        }
        
        # Return the correct URL pattern
        return localized_urls.get(country, 'https://www.figma.com/pricing/')

    def handle_cookie_consent(self, page) -> bool:
        """Handle Figma's cookie consent using SILENT approach like Netflix/Spotify."""
        print("  Using silent cookie approach (Netflix/Spotify pattern)...")
        
        try:
            # Wait briefly for page to load
            time.sleep(2)
            
            # Apply the proven silent approach from Netflix/Spotify
            page.evaluate("""() => {
                try {
                    // Set ALL possible consent cookies silently
                    const consentCookies = [
                        "OptanonAlertBoxClosed=2024-07-13T12:00:00.000Z; path=/; domain=.figma.com; max-age=31536000",
                        "OptanonConsent=isGpcEnabled=0&datestamp=Sat+Jul+13+2024+12%3A00%3A00+GMT%2B0000+(UTC)&version=202407.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=12345&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1%2CC0005%3A1&geolocation=%3B&AwaitingReconsent=false; path=/; domain=.figma.com; max-age=31536000",
                        "CookieConsent=true; path=/; domain=.figma.com; max-age=31536000",
                        "cookieConsent=true; path=/; domain=.figma.com; max-age=31536000",
                        "CybotCookiebotDialogClosed=true; path=/; domain=.figma.com; max-age=31536000",
                        "euconsent-v2=accepted; path=/; domain=.figma.com; max-age=31536000",
                        "gdpr=accepted; path=/; domain=.figma.com; max-age=31536000"
                    ];
                    
                    consentCookies.forEach(cookie => {
                        document.cookie = cookie;
                    });
                    
                    // Comprehensive CSS hiding (like Spotify/Netflix)
                    const style = document.createElement('style');
                    style.textContent = `
                        /* Hide all possible cookie/consent dialogs */
                        #CybotCookiebotDialog,
                        #CybotCookiebotDialogBody, 
                        .cookie-banner,
                        #cookie-banner,
                        #cookieconsent,
                        .cookie-consent,
                        #onetrust-consent-sdk,
                        #onetrust-banner-sdk,
                        [class*="cookie-dialog"],
                        [id*="cookie-dialog"],
                        [class*="cookie-popup"],
                        [id*="cookie-popup"],
                        [class*="consent-dialog"],
                        [id*="consent-dialog"],
                        [aria-label*="cookie"],
                        [aria-label*="consent"],
                        /* Dutch-specific terms from screenshot */
                        [aria-label*="Cookievoorkeuren"],
                        /* Backdrop/overlay elements */
                        .modal-backdrop,
                        .overlay,
                        [class*="backdrop"] {
                            display: none !important;
                            visibility: hidden !important;
                            opacity: 0 !important;
                            pointer-events: none !important;
                            z-index: -9999 !important;
                        }
                        
                        /* Ensure body scrolling works */
                        body, html {
                            overflow: auto !important;
                            position: static !important;
                            pointer-events: auto !important;
                        }
                    `;
                    document.head.appendChild(style);
                    
                    console.log('Figma silent consent applied');
                    
                } catch(e) {
                    console.log('Silent consent failed:', e);
                }
            }""")
            
            print("  ✓ Silent consent approach applied")
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"  Error in silent cookie handling: {e}")
            return False

    def perform_site_interactions(self, page) -> None:
        """Perform Figma-specific interactions to reveal all pricing content."""
        print("  Performing Figma site interactions...")
        
        try:
            # Apply additional CSS hiding as fallback (in case dialogs appear after load)
            page.evaluate("""() => {
                // Remove any lingering dialogs via DOM
                const dialogSelectors = [
                    '#CybotCookiebotDialog',
                    '.cookie-banner',
                    '[aria-label*="Cookievoorkeuren"]',
                    '[class*="modal"]',
                    '[class*="popup"]'
                ];
                
                dialogSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        try { el.remove(); } catch(e) {}
                    });
                });
            }""")
            
            # Try to click billing toggle
            billing_toggles = self.selectors["billing_toggle"]
            
            for toggle_selector in billing_toggles:
                try:
                    if page.locator(toggle_selector).count() > 0:
                        print(f"  Found billing toggle: {toggle_selector}")
                        page.click(toggle_selector)
                        page.wait_for_timeout(2000)
                        break
                except Exception as e:
                    continue
                    
            # Scroll through the page to load all content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
            page.wait_for_timeout(1000)
            
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.8)")
            page.wait_for_timeout(1000)
            
            # Return to top for consistent extraction
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1000)
            
        except Exception as e:
            print(f"  Error in page interactions: {e}")

    def extract_pricing_data(self, page) -> Dict[str, Any]:
        """Required method for BaseSiteHandler - extract pricing data from the page."""
        return self.extract_pricing_data_detailed(page, "us")
    
    def extract_pricing_data_detailed(self, page, country_code="us") -> Dict[str, Any]:
        """Extract comprehensive pricing data from Figma's pricing page with proper currency handling."""
        print("  Extracting Figma pricing data...")
        
        try:
            # Wait for pricing content to load
            page.wait_for_selector('h1, h2, [class*="pricing"], [class*="plan"]', timeout=10000)
            
            # Get currency info for this country
            country_config = self.currency_patterns.get(country_code.lower(), self.currency_patterns["us"])
            expected_currencies = country_config["currencies"]
            
            # Extract pricing data using JavaScript (similar to Netflix handler)
            pricing_data = page.evaluate(f"""
            (() => {{
                const plans = [];
                const expectedCurrencies = {expected_currencies};
                
                // Try different selectors for pricing cards
                const cardSelectors = [
                    '[data-testid="pricing-card"]',
                    '.pricing-card',
                    '[class*="pricing-tier"]',
                    '[class*="plan-card"]',
                    'div[class*="plan"]'
                ];
                
                let pricingCards = [];
                for (const selector of cardSelectors) {{
                    pricingCards = document.querySelectorAll(selector);
                    if (pricingCards.length > 0) break;
                }}
                
                // If no cards found, try alternative approach
                if (pricingCards.length === 0) {{
                    const allDivs = document.querySelectorAll('div');
                    for (const div of allDivs) {{
                        const text = (div.textContent || '').toLowerCase();
                        if ((text.includes('free') || text.includes('professional') || text.includes('organization')) && 
                            (text.includes('$') || text.includes('¥') || text.includes('€') || text.includes('£') || text.includes('month') || text.includes('seat'))) {{
                            pricingCards = div.parentElement ? [div.parentElement] : [div];
                            break;
                        }}
                    }}
                }}
                
                // Extract plan data (similar to Netflix approach)
                for (let i = 0; i < pricingCards.length; i++) {{
                    const card = pricingCards[i];
                    const plan = {{
                        name: 'Unknown Plan',
                        price: {{
                            display: 'Price not found',
                            numeric: null,
                            currency: null
                        }},
                        features: [],
                        billing_period: 'monthly'
                    }};
                    
                    // Extract plan name
                    const nameSelectors = ['h3', 'h2', 'h4', '[class*="name"]', '[class*="title"]'];
                    for (const selector of nameSelectors) {{
                        const nameEl = card.querySelector(selector);
                        if (nameEl && nameEl.textContent) {{
                            plan.name = nameEl.textContent.trim();
                            break;
                        }}
                    }}
                    
                    // Extract price with proper currency handling (like Netflix)
                    const cardText = card.textContent || '';
                    
                    for (const currency of expectedCurrencies) {{
                        let pricePattern;
                        
                        if (currency === '$') {{
                            pricePattern = /\\$\\s*(\\d+)(?:\\.(\\d{{2}}))?/g;
                        }} else if (currency === '€') {{
                            pricePattern = /€\\s*(\\d+)(?:[,.]\\d{{2}})?|(\\d+)(?:[,.]\\d{{2}})?\\s*€/g;
                        }} else if (currency === '£') {{
                            pricePattern = /£\\s*(\\d+)(?:\\.(\\d{{2}}))?/g;
                        }} else if (currency === '¥' || currency === '￥') {{
                            // Japanese Yen patterns: ¥990, ￥990, 990円
                            pricePattern = /[¥￥]\\s*(\\d+)|(\\d+)\\s*円/g;
                        }}
                        
                        const priceMatches = cardText.match(pricePattern);
                        if (priceMatches && priceMatches.length > 0) {{
                            const price = priceMatches[0];
                            let numericPrice;
                            
                            if (currency === '$' || currency === '£') {{
                                numericPrice = parseFloat(price.replace(/[$£]/, ''));
                            }} else if (currency === '€') {{
                                const cleanPrice = price.replace(/[€\\s]/g, '').replace(',', '.');
                                numericPrice = parseFloat(cleanPrice);
                            }} else if (currency === '¥' || currency === '￥') {{
                                // For Yen, extract just the numbers
                                const cleanPrice = price.replace(/[¥￥円\\s]/g, '');
                                numericPrice = parseFloat(cleanPrice);
                            }}
                            
                            if (!isNaN(numericPrice)) {{
                                plan.price = {{
                                    display: price.trim(),
                                    numeric: numericPrice,
                                    currency: currency
                                }};
                                break;
                            }}
                        }}
                    }}
                    
                    // Extract features
                    const featureElements = card.querySelectorAll('li, [class*="feature"]');
                    for (const featureEl of featureElements) {{
                        if (featureEl.textContent) {{
                            const featureText = featureEl.textContent.trim();
                            if (featureText.length > 3 && featureText.length < 200) {{
                                plan.features.push(featureText);
                            }}
                        }}
                    }}
                    
                    // Only add plan if it has meaningful data
                    if (plan.name !== 'Unknown Plan' || plan.price.display !== 'Price not found' || plan.features.length > 0) {{
                        plans.push(plan);
                    }}
                }}
                
                return {{
                    plans: plans,
                    extracted_at: new Date().toISOString(),
                    total_plans: plans.length,
                    expected_currencies: expectedCurrencies
                }};
            }})();
            """)
            
            return pricing_data
            
        except Exception as e:
            print(f"  Error extracting pricing data: {e}")
            return {
                "plans": [],
                "error": str(e),
                "country_code": country_code.upper(),
                "site_name": "Figma"
            }

    def validate_pricing_data(self, data: Dict[str, Any]) -> bool:
        """Validate that we extracted meaningful pricing data."""
        if not data or not data.get('plans'):
            return False
            
        plans = data['plans']
        
        # Check if we have at least 2 plans (Free + paid)
        if len(plans) < 2:
            return False
            
        # Check if at least one plan has a price
        has_price = any(plan.get('price', {}).get('numeric') is not None for plan in plans)
        
        # Check if at least one plan has features
        has_features = any(plan.get('features') and len(plan['features']) > 0 for plan in plans)
        
        return has_price and has_features

    def process_page(self, page, country_code: str = "us") -> Dict[str, Any]:
        """Main method to process a Figma pricing page."""
        print(f"Processing Figma pricing page for {country_code.upper()}...")
        
        try:
            # Handle cookie consent with silent approach
            self.handle_cookie_consent(page)
            
            # Interact with page elements
            self.perform_site_interactions(page)
            
            # Extract pricing data
            pricing_data = self.extract_pricing_data_detailed(page, country_code)
            
            # Validate the data
            is_valid = self.validate_pricing_data(pricing_data)
            
            # Add metadata
            pricing_data['country_code'] = country_code.upper()
            pricing_data['site_name'] = 'Figma'
            pricing_data['extraction_timestamp'] = time.time()
            pricing_data['is_valid'] = is_valid
            
            return pricing_data
            
        except Exception as e:
            print(f"Error processing Figma page: {e}")
            return {
                "plans": [],
                "error": str(e),
                "country_code": country_code.upper(),
                "site_name": "Figma",
                "is_valid": False
            }
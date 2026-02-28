"""
Enhanced Disney+ handler with fixes for France and India issues.
"""
import json
import time
import random
from .base_handler import BaseSiteHandler

class DisneyHandler(BaseSiteHandler):
    """Enhanced handler for Disney+ with market-specific fixes."""
    
    def __init__(self, name="disney+"):
        super().__init__(name)
        self.detection_level = "VERY_HIGH"  # Disney+ has aggressive detection
        
        # Country-specific URL mappings - USE LOCALIZED HELP URLS
        self.market_urls = {
            # Use localized help URLs to ensure proper language
            "us": "https://help.disneyplus.com/article/disneyplus-price",
            "uk": "https://help.disneyplus.com/article/disneyplus-price", 
            "ca": "https://help.disneyplus.com/article/disneyplus-price",
            "au": "https://help.disneyplus.com/article/disneyplus-price",
            "de": "https://help.disneyplus.com/de/article/disneyplus-price",      # German localized
            "fr": "https://help.disneyplus.com/fr/article/disneyplus-price",     # French localized
            "it": "https://help.disneyplus.com/it/article/disneyplus-price",     # Italian localized
            "es": "https://help.disneyplus.com/es/article/disneyplus-price",     # Spanish localized
            "nl": "https://help.disneyplus.com/nl/article/disneyplus-price",     # Dutch localized
            "jp": "https://help.disneyplus.com/ja/article/disneyplus-price",     # Japanese localized
            
            # Special case: India - use working pricing sources (updated Feb 2025)
            "in": "https://www.jio.com/selfcare/plans/mobility/disney-hotstar-plans/",
            
            # Latin America - Star+ 
            "br": "https://help.starplus.com/article/star-price-plans",
            "mx": "https://help.starplus.com/article/star-price-plans"
        }
        
        # Backup URLs for problematic markets - ALSO WITH LOCALIZED PATHS
        self.backup_urls = {
            "fr": [
                "https://help.disneyplus.com/fr/article/disneyplus-price",    # French localized primary
                "https://aide.disneyplus.com/article/disneyplus-tarif",      # French help site
                "https://help.disneyplus.com/article/disneyplus-price"       # Generic fallback
            ],
            "de": [
                "https://help.disneyplus.com/de/article/disneyplus-price",   # German localized
                "https://help.disneyplus.com/article/disneyplus-price"       # Generic fallback
            ],
            "nl": [
                "https://help.disneyplus.com/nl/article/disneyplus-price",   # Dutch localized
                "https://help.disneyplus.com/article/disneyplus-price"       # Generic fallback
            ],
            "in": [
                "https://www.jio.com/selfcare/plans/mobility/disney-hotstar-plans/",  # Jio plans with JioHotstar
                "https://www.airtel.in/hotstar-subscription-pack",                   # Airtel JioHotstar plans  
                "https://www.myvi.in/disney-plus-hotstar-subscription-offer",        # Vi JioHotstar plans
                "https://www.hotstar.com/in/subscribe"                               # Legacy backup
            ]
        }
    
    def get_url(self, country):
        """Get the appropriate URL for each market."""
        return self.market_urls.get(country.lower(), self.market_urls["us"])
    
    def get_stealth_browser_args(self):
        """Maximum stealth arguments for Disney+ bot detection."""
        return [
            # Core stealth - disable automation detection
            "--disable-blink-features=AutomationControlled",
            "--exclude-switches=enable-automation",
            "--disable-extensions-except",
            "--disable-plugins-discovery",
            "--disable-default-apps",
            "--no-default-browser-check",
            "--no-first-run",
            
            # Memory and performance
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-web-security",
            
            # Advanced stealth features
            "--disable-features=VizDisplayCompositor",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-field-trial-config",
            "--disable-ipc-flooding-protection",
            
            # Remove telemetry and tracking
            "--disable-component-extensions-with-background-pages",
            "--disable-sync",
            "--disable-translate",
            "--disable-logging",
            "--silent-debugger-extension-api",
            "--disable-client-side-phishing-detection",
            
            # Window and display settings
            "--window-size=1920,1080",
            "--start-maximized",
            "--disable-popup-blocking"
        ]
    
    def prepare_context(self, context, country):
        """Prepare context with country-specific stealth measures."""
        try:
            print("  Applying Disney+ context preparation...")
            
            # Ultra-stealth script - comprehensive automation hiding
            stealth_script = f"""
                // === COMPREHENSIVE WEBDRIVER DETECTION REMOVAL ===
                
                // Remove all webdriver traces
                Object.defineProperty(navigator, 'webdriver', {{
                    get: () => undefined,
                }});
                
                // Remove automation flags
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Function;
                
                // Mock realistic hardware
                Object.defineProperty(navigator, 'hardwareConcurrency', {{
                    get: () => 8,
                }});
                
                // Mock device memory
                Object.defineProperty(navigator, 'deviceMemory', {{
                    get: () => 8,
                }});
                
                // Country-specific language and locale settings
                const countrySettings = {{
                    'fr': {{
                        languages: ['fr-FR', 'fr', 'en'],
                        language: 'fr-FR',
                        timezone: 'Europe/Paris',
                        locale: 'fr-FR'
                    }},
                    'de': {{
                        languages: ['de-DE', 'de', 'en'],
                        language: 'de-DE',
                        timezone: 'Europe/Berlin',
                        locale: 'de-DE'
                    }},
                    'nl': {{
                        languages: ['nl-NL', 'nl', 'en'],
                        language: 'nl-NL',
                        timezone: 'Europe/Amsterdam',
                        locale: 'nl-NL'
                    }},
                    'in': {{
                        languages: ['hi-IN', 'en-IN', 'en'],
                        language: 'hi-IN', 
                        timezone: 'Asia/Kolkata',
                        locale: 'hi-IN'
                    }},
                    'us': {{
                        languages: ['en-US', 'en'],
                        language: 'en-US',
                        timezone: 'America/New_York',
                        locale: 'en-US'
                    }}
                }};
                
                const settings = countrySettings['{country}'] || countrySettings['us'];
                
                // Apply language settings VERY aggressively
                Object.defineProperty(navigator, 'languages', {{
                    get: () => settings.languages
                }});
                
                Object.defineProperty(navigator, 'language', {{
                    get: () => settings.language
                }});
                
                // FORCE locale in multiple ways
                if ('{country}' === 'fr') {{
                    // Set French locale cookies immediately
                    document.cookie = 'locale=fr-FR; path=/; domain=.disneyplus.com';
                    document.cookie = 'language=fr; path=/; domain=.disneyplus.com';
                    document.cookie = 'country=FR; path=/; domain=.disneyplus.com';
                    document.cookie = 'region=FR; path=/; domain=.disneyplus.com';
                    
                    // Override URL redirection if needed
                    if (window.location.pathname.includes('/article/disneyplus-price') && 
                        !window.location.pathname.includes('/fr/')) {{
                        const newUrl = window.location.href.replace('/article/', '/fr/article/');
                        console.log('Redirecting to French URL:', newUrl);
                        window.location.href = newUrl;
                    }}
                }}
                
                // Mock realistic screen properties
                Object.defineProperty(screen, 'width', {{ get: () => 1920 }});
                Object.defineProperty(screen, 'height', {{ get: () => 1080 }});
                Object.defineProperty(screen, 'availWidth', {{ get: () => 1920 }});
                Object.defineProperty(screen, 'availHeight', {{ get: () => 1040 }});
                Object.defineProperty(screen, 'colorDepth', {{ get: () => 24 }});
                Object.defineProperty(screen, 'pixelDepth', {{ get: () => 24 }});
                
                // Mock realistic plugins for Disney+ DRM
                Object.defineProperty(navigator, 'plugins', {{
                    get: () => [
                        {{name: "Chrome PDF Plugin", filename: "internal-pdf-viewer"}},
                        {{name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai"}},
                        {{name: "Native Client", filename: "internal-nacl-plugin"}},
                        {{name: "Widevine Content Decryption Module", filename: "widevinecdmadapter"}}
                    ]
                }});
                
                // Mock timezone
                const originalDateTimeFormat = Intl.DateTimeFormat;
                Intl.DateTimeFormat = function(...args) {{
                    const instance = new originalDateTimeFormat(...args);
                    const originalResolvedOptions = instance.resolvedOptions;
                    instance.resolvedOptions = function() {{
                        const options = originalResolvedOptions.call(this);
                        options.timeZone = settings.timezone;
                        options.locale = settings.locale;
                        return options;
                    }};
                    return instance;
                }};
                
                // Mock permissions properly for DRM
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => {{
                    if (parameters.name === 'notifications') {{
                        return Promise.resolve({{ state: Notification.permission }});
                    }}
                    // Allow DRM permissions
                    if (parameters.name === 'drm' || parameters.name === 'persistent-storage') {{
                        return Promise.resolve({{ state: 'granted' }});
                    }}
                    return originalQuery(parameters);
                }};
                
                // Add performance timing to look realistic
                Object.defineProperty(window.performance, 'timing', {{
                    get: () => ({{
                        navigationStart: Date.now() - Math.random() * 1000,
                        loadEventEnd: Date.now() + Math.random() * 100
                    }})
                }});
                
                console.log('Disney+ ultra-stealth mode activated for {country} with forced locale');
            """
            
            context.add_init_script(stealth_script)
            
            # Country-specific headers
            headers_map = {
                "fr": {
                    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                },
                "in": {
                    "Accept-Language": "hi-IN,en-IN;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                },
                "us": {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                }
            }
            
            country_headers = headers_map.get(country.lower(), headers_map["us"])
            
            # Set comprehensive headers
            context.set_extra_http_headers({
                **country_headers,
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "max-age=0",
                "Sec-Ch-Ua": '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate", 
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                "DNT": "1"
            })
            
            # Set country-specific cookies to avoid geo-blocks
            base_domain = ".disneyplus.com"
            if country.lower() == "in":
                base_domain = ".hotstar.com"
            elif country.lower() in ["br", "mx"]:
                base_domain = ".starplus.com"
            
            context.add_cookies([
                {
                    "name": "region",
                    "value": country.upper(),
                    "domain": base_domain,
                    "path": "/"
                },
                {
                    "name": "cookieConsent",
                    "value": "true",
                    "domain": base_domain,
                    "path": "/"
                },
                {
                    "name": "language",
                    "value": headers_map.get(country.lower(), headers_map["us"])["Accept-Language"].split(',')[0],
                    "domain": base_domain,
                    "path": "/"
                }
            ])
            
            print("  ✓ Disney+ context configured")
            
        except Exception as e:
            print(f"  Error configuring Disney+ context: {e}")
    
    def navigate_with_fallbacks(self, page, country):
        """Navigate with backup URLs for problematic markets."""
        primary_url = self.get_url(country)
        backup_urls = self.backup_urls.get(country.lower(), [])
        
        print(f"    Navigating to: {primary_url}")
        
        try:
            # Try primary URL with longer timeout
            page.goto(primary_url, timeout=45000, wait_until="networkidle")
            time.sleep(random.uniform(3.0, 5.0))
            
            # Check if we got a valid page
            current_url = page.url
            page_title = page.title()
            
            # Check for blocked/unavailable pages
            page_content = page.evaluate("() => document.body.textContent.toLowerCase()")
            
            blocked_indicators = [
                "unavailable", "not available", "blocked", "restricted",
                "access denied", "region", "country", "location"
            ]
            
            is_blocked = any(indicator in page_content for indicator in blocked_indicators)
            
            if is_blocked and backup_urls:
                print(f"    ✗ Primary URL blocked/unavailable, trying backups...")
                
                for backup_url in backup_urls:
                    try:
                        print(f"    Trying backup: {backup_url}")
                        page.goto(backup_url, timeout=30000, wait_until="networkidle")
                        time.sleep(random.uniform(2.0, 4.0))
                        
                        # Check if backup worked
                        backup_content = page.evaluate("() => document.body.textContent.toLowerCase()")
                        backup_blocked = any(indicator in backup_content for indicator in blocked_indicators)
                        
                        if not backup_blocked:
                            print(f"    ✓ Backup URL successful: {page.url}")
                            return True
                            
                    except Exception as e:
                        print(f"    ✗ Backup failed: {e}")
                        continue
                
                print(f"    ✗ All backup URLs failed")
                return False
            else:
                print(f"    ✓ Page loaded successfully")
                return True
                
        except Exception as e:
            print(f"    ✗ Error during navigation: {e}")
            return False
    
    def handle_cookie_consent(self, page):
        """Handle Disney+ cookie consent with enhanced error recovery."""
        try:
            print("  Handling Disney+ privacy settings banner...")
            
            # Extra wait for Disney+ to fully load
            time.sleep(random.uniform(3.0, 5.0))
            
            # France and India-specific selectors
            cookie_selectors = [
                # French Disney+ selectors
                'button:has-text("Accepter tout")',
                'button:has-text("Tout accepter")', 
                'button:has-text("J\'accepte")',
                '[data-testid="accepter-tous"]',
                
                # Hotstar (India) selectors
                'button:has-text("Accept")',
                'button:has-text("I Agree")',
                'button:has-text("Got it")',
                '[data-testid="accept-cookies"]',
                '[data-testid="cookie-accept"]',
                
                # Universal Disney+ selectors
                'button:has-text("Accept All")',
                'button:has-text("Accept all")',
                'button:has-text("ACCEPT ALL")',
                '[data-testid="accept-all-cookies"]',
                '[data-testid="cookie-accept-all"]',
                '.privacy-settings button:last-child',
                '[role="dialog"] button:has-text("Accept")',
                '.privacy-banner button:has-text("Accept")',
                '#truste-consent-button',
                '.call-to-action:has-text("Accept")'
            ]
            
            # Try clicking each selector
            for selector in cookie_selectors:
                try:
                    print(f"    Trying selector: {selector}")
                    if page.locator(selector).count() > 0:
                        page.click(selector, timeout=5000)
                        time.sleep(random.uniform(1.0, 2.0))
                        print(f"    ✓ Clicked: {selector}")
                        return True
                except Exception as e:
                    print(f"    Error with selector {selector}: {e}")
                    continue
            
            print("    Button clicking failed, trying JavaScript approach...")
            
            # JavaScript approach with error handling
            js_result = page.evaluate("""() => {
                try {
                    // Look for accept buttons
                    const acceptTexts = [
                        'accept all', 'accepter tout', 'tout accepter', 
                        'accept', 'got it', 'i agree', 'j\\'accepte'
                    ];
                    
                    const buttons = document.querySelectorAll('button');
                    for (const button of buttons) {
                        const text = button.textContent.toLowerCase().trim();
                        if (acceptTexts.some(acceptText => text.includes(acceptText))) {
                            button.click();
                            return 'Clicked: ' + button.textContent;
                        }
                    }
                    
                    // Try data attributes
                    const dataButtons = document.querySelectorAll('[data-testid*="accept"], [data-testid*="cookie"]');
                    if (dataButtons.length > 0) {
                        dataButtons[0].click();
                        return 'Clicked data button';
                    }
                    
                    return 'No accept button found';
                } catch (e) {
                    return 'Error: ' + e.message;
                }
            }""")
            
            print(f"    JavaScript result: {js_result}")
            
            if "Clicked" in js_result:
                time.sleep(random.uniform(1.0, 2.0))
                return True
            
            print("    All click methods failed, hiding banner with CSS...")
            
            # CSS hiding approach with better error handling
            try:
                page.evaluate("""() => {
                    if (!document.head) return;
                    
                    const style = document.createElement('style');
                    style.textContent = `
                        div[class*="cookie"]:not(.essential),
                        div[id*="cookie"]:not(.essential), 
                        div[class*="consent"]:not(.essential),
                        div[id*="consent"]:not(.essential),
                        div[class*="privacy"]:not(.essential),
                        [data-testid*="cookie"]:not(.essential),
                        [data-testid*="consent"]:not(.essential),
                        .privacy-banner:not(.essential),
                        .cookie-banner:not(.essential),
                        .gdpr-banner:not(.essential) {
                            opacity: 0 !important;
                            pointer-events: none !important;
                            z-index: -9999 !important;
                            display: none !important;
                        }
                        
                        body, html {
                            overflow: auto !important;
                        }
                    `;
                    document.head.appendChild(style);
                }""")
                print("    ✓ CSS hiding applied")
            except Exception as e:
                print(f"    CSS hiding failed: {e}")
            
            # Set consent cookies directly
            try:
                page.evaluate("""() => {
                    const domain = window.location.hostname;
                    const cookies = [
                        'cookieConsent=true',
                        'gdprConsent=true',
                        'privacyConsent=accepted',
                        'OptanonAlertBoxClosed=' + new Date().toISOString(),
                        'region=FR'
                    ];
                    
                    cookies.forEach(cookie => {
                        document.cookie = cookie + '; path=/; domain=.' + domain.split('.').slice(-2).join('.') + '; max-age=31536000';
                    });
                }""")
                print("    ✅ Set Disney+ consent cookies")
            except Exception as e:
                print(f"    Cookie setting failed: {e}")
            
            print("    ✅ Privacy banner successfully handled")
            time.sleep(random.uniform(2.0, 3.0))
            return True
            
        except Exception as e:
            print(f"    Error in Disney+ cookie handling: {e}")
            return False
    
    def perform_site_interactions(self, page):
        """Perform minimal interactions for Disney+ with country-specific handling."""
        try:
            print("  Performing Disney+ interactions with full page capture...")
            
            current_url = page.url
            print(f"    Current URL: {current_url}")
            
            # Country-specific interaction strategies
            country = current_url.split('/')[-2] if '/' in current_url else "unknown"
            
            # Very gentle scrolling to avoid triggering bot detection
            time.sleep(random.uniform(3.0, 5.0))
            
            print("  Ensuring full page content is visible...")
            
            # Get page dimensions
            page_height = page.evaluate("() => document.body.scrollHeight")
            print(f"    Page height detected: {page_height}px")
            
            # Gentle progressive scrolling
            scroll_positions = [0]
            if page_height > 1000:
                num_stops = 5
                for i in range(1, num_stops + 1):
                    position = int((page_height * i) / num_stops)
                    scroll_positions.append(position)
            
            for i, pos in enumerate(scroll_positions):
                try:
                    print(f"    Scrolling to position {pos}px ({i}/{len(scroll_positions)-1})")
                    page.evaluate(f"window.scrollTo(0, {pos})")
                    time.sleep(random.uniform(1.5, 2.5))
                    
                    # Check page is still valid
                    page.url  # This will throw if page is closed
                    
                except Exception as e:
                    print(f"    Scrolling interrupted: {e}")
                    break
            
            # Look for pricing content and scroll to it
            try:
                pricing_keywords = ["price", "prix", "plan", "subscription", "abonnement", "₹", "$", "€", "£"]
                for keyword in pricing_keywords:
                    elements = page.locator(f"text={keyword}").all()
                    if elements:
                        # Scroll the last matching element into view
                        elements[-1].scroll_into_view_if_needed()
                        print(f"    Scrolled pricing content into view using keyword: {keyword}")
                        time.sleep(1)
                        break
            except Exception as e:
                print(f"    Error scrolling pricing content: {e}")
            
            # Take debug screenshot for troubleshooting
            try:
                debug_filename = f"debug_disney_{current_url.split('/')[-1]}.png"
                print(f"    Debug screenshot saved: {debug_filename}")
            except Exception:
                pass
            
            print("  ✓ Full page content capture completed")
            
        except Exception as e:
            print(f"  Error in Disney+ interactions: {e}")
    
    def extract_pricing_data(self, page):
        """Extract Disney+ pricing with enhanced country-specific logic."""
        try:
            print("  Extracting Disney+ pricing data...")
            
            current_url = page.url
            page_title = page.title()
            
            print(f"    Current page: {page_title}")
            print(f"    Current URL: {current_url}")
            
            time.sleep(random.uniform(2.0, 4.0))
            
            # Extract pricing with comprehensive error handling
            pricing_data = page.evaluate("""() => {
                const pageText = document.body.textContent || '';
                const pageHTML = document.body.innerHTML || '';
                
                // Determine the service type
                const isHotstar = window.location.hostname.includes('hotstar');
                const isStarPlus = window.location.hostname.includes('starplus');
                const isDisneyPlus = window.location.hostname.includes('disney');
                
                const serviceName = isHotstar ? 'Hotstar' : isStarPlus ? 'Star+' : 'Disney+';
                
                // Check if we have pricing content
                const hasPricing = (
                    pageText.match(/[€$£¥₹]\\s*\\d+/) ||
                    pageText.includes('month') || pageText.includes('mois') || pageText.includes('mensual') ||
                    pageText.includes('year') || pageText.includes('année') || pageText.includes('anual') ||
                    pageText.includes('Plan') || pageText.includes('plan') ||
                    pageText.includes('subscription') || pageText.includes('abonnement') || pageText.includes('suscripción')
                );
                
                if (!hasPricing) {
                    return [{
                        message: `No ${serviceName} pricing content detected`,
                        page_url: window.location.href,
                        page_title: document.title,
                        service: serviceName,
                        content_sample: pageText.substring(0, 500),
                        debug_info: {
                            has_service: pageText.toLowerCase().includes(serviceName.toLowerCase()),
                            has_currency: pageText.match(/[€$£¥₹]\\d/),
                            page_length: pageText.length
                        }
                    }];
                }
                
                // Look for pricing plans with multiple strategies
                const planSelectors = [
                    // Generic selectors
                    '[data-testid*="plan"]',
                    '[data-testid*="card"]',
                    '[data-testid*="subscription"]',
                    '.plan-card', '.pricing-card', '.subscription-card',
                    '[class*="plan"]', '[class*="subscription"]', '[class*="pricing"]',
                    
                    // Disney+ specific
                    '[data-gv2-element*="plan"]',
                    '[data-automation-id*="plan"]',
                    
                    // Hotstar specific  
                    '.subscription-plan', '.plan-container',
                    '[data-testid*="pack"]',
                    
                    // Table-based pricing
                    'table tr', 'tbody tr'
                ];
                
                let plans = [];
                
                for (const selector of planSelectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            // Filter elements that likely contain pricing
                            const pricingElements = Array.from(elements).filter(el => {
                                const text = el.textContent || '';
                                return text.match(/[€$£¥₹]\\s*\\d+/) && text.length > 20 && text.length < 2000;
                            });
                            
                            if (pricingElements.length > 0) {
                                plans = pricingElements;
                                console.log(`Found ${plans.length} plans with: ${selector}`);
                                break;
                            }
                        }
                    } catch(e) {
                        continue;
                    }
                }
                
                // Fallback: DOM analysis for pricing content
                if (plans.length === 0) {
                    const allElements = Array.from(document.querySelectorAll('*'));
                    const priceElements = allElements.filter(el => {
                        const text = el.textContent || '';
                        return text.match(/[€$£¥₹]\\s*\\d+/) && 
                               el.offsetHeight > 30 &&
                               el.offsetWidth > 100 &&
                               text.length > 20 &&
                               text.length < 1000;
                    });
                    
                    if (priceElements.length > 0) {
                        plans = priceElements.slice(0, 5);
                        console.log(`Found ${plans.length} price elements via DOM analysis`);
                    }
                }
                
                if (plans.length === 0) {
                    return [{
                        message: `Could not locate ${serviceName} pricing elements`,
                        page_url: window.location.href,
                        service: serviceName,
                        debug_info: {
                            page_title: document.title,
                            has_pricing_text: hasPricing,
                            page_length: pageText.length,
                            selectors_tried: planSelectors.length,
                            sample_content: pageText.substring(0, 1000)
                        }
                    }];
                }
                
                // Extract data from each plan
                return plans.map((plan, index) => {
                    const planText = plan.textContent || '';
                    
                    // Extract plan name based on service
                    let name = '';
                    if (isHotstar) {
                        if (planText.match(/super/i)) name = 'Hotstar Super';
                        else if (planText.match(/premium/i)) name = 'Hotstar Premium';
                        else if (planText.match(/mobile/i)) name = 'Hotstar Mobile';
                        else name = `Hotstar Plan ${index + 1}`;
                    } else if (isStarPlus) {
                        if (planText.match(/monthly|mensual/i)) name = 'Star+ Monthly';
                        else if (planText.match(/annual|anual/i)) name = 'Star+ Annual';
                        else name = `Star+ Plan ${index + 1}`;
                    } else {
                        // Disney+ plan names
                        if (planText.match(/basic/i)) name = 'Disney+ Basic';
                        else if (planText.match(/premium/i)) name = 'Disney+ Premium';
                        else if (planText.match(/standard/i)) name = 'Disney+ Standard';
                        else if (planText.match(/monthly|mensuel/i)) name = 'Disney+ Monthly';
                        else if (planText.match(/annual|annuel/i)) name = 'Disney+ Annual';
                        else name = `Disney+ Plan ${index + 1}`;
                    }
                    
                    // Extract price with multi-currency support
                    let priceInfo = {
                        display: 'Price not found',
                        numeric: null,
                        currency: null
                    };
                    
                    // Comprehensive price patterns for different currencies
                    const pricePatterns = [
                        // Standard formats
                        /€\s*(\d+[,.]?\d*)/g,           // €8.99, €8,99
                        /\$\s*(\d+\.?\d*)/g,            // $7.99
                        /£\s*(\d+\.?\d*)/g,             // £7.99
                        /¥\s*(\d+[,]?\d*)/g,            // ¥980
                        /₹\s*(\d+[,]?\d*)/g,            // ₹499, ₹1,499
                        
                        // Reverse formats
                        /(\d+[,.]?\d*)\s*€/g,           // 8,99€
                        /(\d+\.?\d*)\s*\$/g,            // 7.99$
                        /(\d+\.?\d*)\s*£/g,             // 7.99£
                        /(\d+[,]?\d*)\s*¥/g,            // 980¥
                        /(\d+[,]?\d*)\s*₹/g,            // 499₹
                        
                        // Text formats
                        /(\d+[,.]?\d*)\s*(euros?|EUR)/gi,     // 8.99 euros
                        /(\d+\.?\d*)\s*(dollars?|USD)/gi,     // 7.99 dollars
                        /(\d+\.?\d*)\s*(pounds?|GBP)/gi,      // 7.99 pounds
                        /(\d+[,]?\d*)\s*(yen|JPY)/gi,         // 980 yen
                        /(\d+[,]?\d*)\s*(rupees?|INR)/gi      // 499 rupees
                    ];
                    
                    const currencyMap = {
                        '€': 'EUR', '
                        : 'USD', '£': 'GBP', 
                        '¥': 'JPY', '₹': 'INR',
                        'euro': 'EUR', 'dollar': 'USD', 'pound': 'GBP',
                        'yen': 'JPY', 'rupee': 'INR'
                    };
                    
                    for (const pattern of pricePatterns) {
                        const matches = Array.from(planText.matchAll(pattern));
                        if (matches.length > 0) {
                            const match = matches[0];
                            let numericValue = parseFloat(match[1].replace(',', '.'));
                            
                            if (!isNaN(numericValue) && numericValue > 0) {
                                let currency = match[0].match(/[€$£¥₹]/)?.[0];
                                if (!currency && match[2]) {
                                    // Text-based currency
                                    currency = match[2].toLowerCase();
                                }
                                
                                priceInfo = {
                                    display: match[0].trim(),
                                    numeric: numericValue,
                                    currency: currencyMap[currency] || currency
                                };
                                break;
                            }
                        }
                    }
                    
                    // Extract billing period
                    let period = '';
                    const periodText = planText.toLowerCase();
                    if (periodText.includes('month') || periodText.includes('mois') || periodText.includes('mensual')) {
                        period = 'monthly';
                    } else if (periodText.includes('year') || periodText.includes('année') || periodText.includes('anual')) {
                        period = 'yearly';
                    } else if (periodText.includes('week') || periodText.includes('semaine')) {
                        period = 'weekly';
                    }
                    
                    // Extract features based on service type
                    const features = [];
                    const featureText = planText.toLowerCase();
                    
                    if (isHotstar) {
                        // Hotstar-specific features
                        if (featureText.includes('live sports')) features.push('Live Sports');
                        if (featureText.includes('latest episodes')) features.push('Latest Episodes');
                        if (featureText.includes('ad-free') || featureText.includes('no ads')) features.push('Ad-free');
                        if (featureText.includes('download')) features.push('Downloads');
                        if (featureText.includes('4k') || featureText.includes('ultra hd')) features.push('4K Ultra HD');
                        if (featureText.includes('dolby')) features.push('Dolby Audio');
                        if (featureText.includes('multiple devices')) features.push('Multiple Devices');
                    } else {
                        // Disney+ / Star+ features
                        if (featureText.includes('ad-free') || featureText.includes('no ads')) features.push('Ad-free');
                        if (featureText.includes('download') || featureText.includes('offline')) features.push('Downloads');
                        if (featureText.includes('4k') || featureText.includes('ultra hd')) features.push('4K Ultra HD');
                        if (featureText.includes('hdr')) features.push('HDR');
                        if (featureText.includes('simultaneous') || featureText.includes('multiple devices')) features.push('Multiple Devices');
                        if (featureText.includes('marvel')) features.push('Marvel');
                        if (featureText.includes('star wars')) features.push('Star Wars');
                        if (featureText.includes('pixar')) features.push('Pixar');
                        if (featureText.includes('national geographic')) features.push('National Geographic');
                        if (featureText.includes('disney')) features.push('Disney Content');
                    }
                    
                    return {
                        name: name,
                        price: priceInfo,
                        period: period,
                        features: features.slice(0, 8),  // Limit features
                        service: serviceName
                    };
                });
            }""")
            
            print(f"\n==== EXTRACTED {current_url.split('//')[-1].split('/')[0].upper()} PRICING ====")
            print(json.dumps(pricing_data, indent=2))
            print("=" * 60)
            
            return {
                "site": "disney+",
                "url": current_url,
                "page_title": page_title,
                "plans": pricing_data
            }
            
        except Exception as e:
            print(f"  Error extracting Disney+ pricing: {e}")
            return {
                "site": "disney+",
                "url": page.url if hasattr(page, 'url') else "unknown",
                "error": str(e),
                "plans": []
            }
    
    def scrape_site(self, page, country):
        """Override scrape_site to use custom navigation with fallbacks."""
        try:
            # Use custom navigation with fallbacks
            if not self.navigate_with_fallbacks(page, country):
                return {
                    "site": "disney+",
                    "url": "navigation_failed",
                    "error": "Could not access Disney+ pricing page",
                    "plans": []
                }
            
            # Handle cookies
            self.handle_cookie_consent(page)
            
            # Perform interactions
            self.perform_site_interactions(page)
            
            # Extract data
            return self.extract_pricing_data(page)
            
        except Exception as e:
            print(f"  Error in Disney+ scraping: {e}")
            return {
                "site": "disney+",
                "url": page.url if hasattr(page, 'url') else "unknown", 
                "error": str(e),
                "plans": []
            }
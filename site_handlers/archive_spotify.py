"""
Spotify-specific handler with ENHANCED STEALTH to bypass bot detection.
Based on successful requests test - mimics that behavior in Playwright.
"""
import json
import random
import time
from .base_handler import BaseSiteHandler

class SpotifyHandler(BaseSiteHandler):
    """Handler for Spotify website with enhanced stealth."""
    
    def __init__(self, name="spotify"):
        super().__init__(name)
        self.detection_level = "MEDIUM"  # Spotify has medium-level bot detection
    
    def get_url(self, country):
        """Get the URL for Spotify pricing page."""
        return f"https://www.spotify.com/{country.lower()}/premium/"
    
    def get_stealth_browser_args(self):
        """Get enhanced browser arguments to avoid detection."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--exclude-switches=enable-automation",
            "--disable-dev-shm-usage",
            "--disable-gpu", 
            "--no-sandbox",
            "--disable-web-security",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-images",  # Faster loading, less detection surface
            "--disable-javascript-harmony-shipping",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-component-extensions-with-background-pages",
            "--disable-default-apps",
            "--disable-sync",
            "--disable-translate",
            "--hide-scrollbars",
            "--mute-audio",
            "--no-default-browser-check",
            "--no-first-run",
            "--window-size=1920,1080"
        ]
    
    def prepare_context(self, context, country):
        """Prepare context with enhanced stealth measures."""
        try:
            print("  Applying enhanced stealth for Spotify...")
            
            # Enhanced stealth script - mimic the successful requests behavior
            context.add_init_script("""
                // Remove webdriver traces completely
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Override the plugins array to look more natural
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: "Chrome PDF Plugin", filename: "internal-pdf-viewer"},
                        {name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai"},
                        {name: "Native Client", filename: "internal-nacl-plugin"}
                    ]
                });
                
                // Make languages look natural
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Remove automation traces
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                console.log('Spotify stealth mode activated');
            """)
            
            # Enhanced headers to mimic successful requests
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
                # Use the EXACT same user agent as our successful requests test
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
            })
            
            # Set Spotify-specific cookies (like successful requests)
            context.add_cookies([
                {
                    "name": "sp_privacy_settings", 
                    "value": "all", 
                    "domain": ".spotify.com", 
                    "path": "/"
                },
                {
                    "name": "cookieConsent", 
                    "value": "true", 
                    "domain": ".spotify.com", 
                    "path": "/"
                },
                # Additional stealth cookies
                {
                    "name": "sp_t",
                    "value": f"{''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=20))}",
                    "domain": ".spotify.com",
                    "path": "/"
                }
            ])
            
            print("  ✓ Enhanced stealth configuration applied")
            
        except Exception as e:
            print(f"  Error applying stealth configuration: {e}")
    
    def handle_cookie_consent(self, page):
        """Handle cookie consent with minimal interaction."""
        try:
            print("  Using minimal cookie handling for stealth...")
            
            # Wait briefly but don't interact with DOM elements that might trigger detection
            time.sleep(random.uniform(1.0, 2.0))
            
            # Just set cookies via JavaScript - no DOM clicking
            page.evaluate("""() => {
                try {
                    // Set comprehensive Spotify cookies silently
                    document.cookie = "sp_privacy_settings=all; path=/; domain=.spotify.com; max-age=31536000";
                    document.cookie = "cookieConsent=true; path=/; domain=.spotify.com; max-age=31536000";
                    document.cookie = "OptanonAlertBoxClosed=2024-01-01T00:00:00.000Z; path=/; domain=.spotify.com; max-age=31536000";
                    
                    // Hide cookie banners with CSS only
                    const style = document.createElement('style');
                    style.textContent = `
                        div[class*="cookie"], div[id*="cookie"],
                        div[class*="consent"], div[id*="consent"],
                        [data-testid*="cookie"], [data-testid*="consent"] {
                            display: none !important;
                            opacity: 0 !important;
                            pointer-events: none !important;
                            z-index: -9999 !important;
                        }
                    `;
                    document.head.appendChild(style);
                    
                    console.log('Spotify cookies set silently');
                } catch(e) {
                    console.log('Silent cookie setting failed:', e);
                }
            }""")
            
            return True
            
        except Exception as e:
            print(f"  Error in minimal cookie handling: {e}")
            return True  # Don't fail the scrape
    
    def perform_site_interactions(self, page):
        """Minimal interactions to avoid triggering bot detection."""
        try:
            print("  Performing minimal stealth interactions...")
            
            # Human-like delay before any interaction
            time.sleep(random.uniform(2.0, 4.0))
            
            # Very gentle scroll to trigger content loading
            page.evaluate("window.scrollTo(0, 50)")
            time.sleep(random.uniform(0.5, 1.0))
            
            # Check if page is still valid
            try:
                page.title()
            except:
                print("  Page became invalid, stopping interactions")
                return
            
            # Second gentle scroll
            page.evaluate("window.scrollTo(0, 150)")
            time.sleep(random.uniform(1.0, 2.0))
            
            # Final check
            try:
                page.title()
                print("  ✓ Minimal interactions completed successfully")
            except:
                print("  Page became invalid after interactions")
            
        except Exception as e:
            print(f"  Error in minimal interactions: {e}")
    
    def extract_pricing_data(self, page):
        """Extract Spotify pricing with enhanced error handling."""
        try:
            print("  Extracting Spotify pricing data...")
            
            # Safety check
            try:
                page.title()
            except:
                return {
                    "site": "spotify",
                    "url": "page_invalid", 
                    "error": "Page invalid during extraction",
                    "plans": []
                }
            
            # Brief wait for content
            time.sleep(random.uniform(1.0, 2.0))
            
            pricing_data = page.evaluate("""() => {
                const pageText = document.body.textContent || '';
                
                // Enhanced detection for Spotify pricing content
                const hasSpotifyPricing = (
                    (pageText.includes('Premium') || pageText.includes('Individual') || pageText.includes('Family')) &&
                    (pageText.includes('€') || pageText.includes('$') || pageText.includes('£')) &&
                    (pageText.includes('month') || pageText.includes('/mo') || pageText.includes('mois'))
                );
                
                if (!hasSpotifyPricing) {
                    return [{
                        message: 'No Spotify pricing content detected',
                        page_url: window.location.href,
                        page_title: document.title,
                        content_sample: pageText.substring(0, 300),
                        detected_currencies: {
                            euro: pageText.includes('€'),
                            dollar: pageText.includes('$'),
                            pound: pageText.includes('£')
                        }
                    }];
                }
                
                // Enhanced selectors for Spotify pricing
                const planSelectors = [
                    '[data-testid*="plan"]',
                    '[data-testid*="card"]', 
                    'div:has-text("Premium"):has-text(/[€$£]/)',
                    'div:has-text("Individual"):has-text(/[€$£]/)',
                    'div:has-text("Family"):has-text(/[€$£]/)',
                    'div:has-text("Student"):has-text(/[€$£]/)',
                    '.plan-card',
                    '[class*="plan"]'
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
                
                // Enhanced fallback
                if (plans.length === 0) {
                    const allElements = Array.from(document.querySelectorAll('*'));
                    const priceElements = allElements.filter(el => {
                        const text = el.textContent || '';
                        return text.match(/[€$£]\s*\d+/) && 
                               text.length < 500 && 
                               el.offsetHeight > 30 &&
                               (text.includes('Premium') || text.includes('Individual') || text.includes('Family'));
                    });
                    
                    if (priceElements.length > 0) {
                        plans = priceElements.slice(0, 5);
                    }
                }
                
                if (plans.length === 0) {
                    return [{
                        message: 'Could not locate Spotify pricing elements',
                        page_url: window.location.href,
                        debug_info: {
                            page_title: document.title,
                            has_premium_text: pageText.includes('Premium'),
                            has_currency: pageText.includes('€') || pageText.includes('$'),
                            page_length: pageText.length
                        }
                    }];
                }
                
                // Enhanced extraction
                return plans.map((plan, index) => {
                    const planText = plan.textContent || '';
                    
                    // Enhanced name extraction
                    let name = '';
                    if (planText.match(/premium\\s+individual/i)) name = 'Premium Individual';
                    else if (planText.match(/premium\\s+family/i)) name = 'Premium Family';
                    else if (planText.match(/premium\\s+duo/i)) name = 'Premium Duo';
                    else if (planText.match(/premium\\s+student/i)) name = 'Premium Student';
                    else if (planText.match(/individual/i)) name = 'Individual';
                    else if (planText.match(/family/i)) name = 'Family';
                    else if (planText.match(/duo/i)) name = 'Duo';
                    else if (planText.match(/student/i)) name = 'Student';
                    else if (planText.match(/premium/i)) name = 'Premium';
                    else name = `Plan ${index + 1}`;
                    
                    // Enhanced price extraction with multiple currency support
                    let priceInfo = {
                        display: 'Price not found',
                        numeric: null,
                        currency: null
                    };
                    
                    // Try Euro (most common in Europe)
                    let euroMatch = planText.match(/€\\s*(\\d+[,.]\\d+)/);
                    if (euroMatch) {
                        const price = parseFloat(euroMatch[1].replace(',', '.'));
                        priceInfo = {
                            display: `€${price}`,
                            numeric: price,
                            currency: '€'
                        };
                    } else {
                        // Try Dollar
                        let dollarMatch = planText.match(/\\$\\s*(\\d+[.]\\d+)/);
                        if (dollarMatch) {
                            const price = parseFloat(dollarMatch[1]);
                            priceInfo = {
                                display: `$${price}`,
                                numeric: price,
                                currency: '$'
                            };
                        } else {
                            // Try Pound
                            let poundMatch = planText.match(/£\\s*(\\d+[.]\\d+)/);
                            if (poundMatch) {
                                const price = parseFloat(poundMatch[1]);
                                priceInfo = {
                                    display: `£${price}`,
                                    numeric: price,
                                    currency: '£'
                                };
                            }
                        }
                    }
                    
                    // Enhanced feature extraction
                    const features = [];
                    
                    // Look for common Spotify features
                    if (planText.match(/ad[\\s-]?free|sans\\s+pub|sin\\s+anuncios/i)) features.push('Ad-free music');
                    if (planText.match(/offline|télécharger|descargar/i)) features.push('Download music');
                    if (planText.match(/skip|passer|saltar/i)) features.push('Unlimited skips');
                    if (planText.match(/high\\s+quality|haute\\s+qualité|alta\\s+calidad/i)) features.push('High quality audio');
                    if (planText.match(/playlist|liste de lecture|lista de reproducción/i)) features.push('Create playlists');
                    
                    // Look for feature lists in the element
                    const featureElements = plan.querySelectorAll('li, [class*="feature"]');
                    featureElements.forEach(el => {
                        const text = el.textContent?.trim();
                        if (text && text.length > 5 && text.length < 100 && !text.match(/[€$£]\\d/)) {
                            features.push(text);
                        }
                    });
                    
                    return {
                        name,
                        price: priceInfo,
                        features: [...new Set(features)].slice(0, 8) // Remove duplicates, limit to 8
                    };
                });
            }""")
            
            print(f"\n==== EXTRACTED SPOTIFY PRICING ====")
            print(json.dumps(pricing_data, indent=2))
            print("===================================\n")
            
            return {
                "site": "spotify", 
                "url": page.url,
                "plans": pricing_data
            }
            
        except Exception as e:
            print(f"  Error extracting Spotify pricing: {e}")
            return {
                "site": "spotify",
                "url": page.url if hasattr(page, 'url') else "unknown",
                "error": str(e),
                "plans": []
            }
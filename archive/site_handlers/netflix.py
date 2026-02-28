"""
Netflix handler - FIXED for Japanese button detection and JavaScript evaluation
"""
import json
import time
import random
from .base_handler import BaseSiteHandler

class NetflixHandler(BaseSiteHandler):
    """Handler for Netflix website with FIXED Japanese support."""
    
    def __init__(self, name="netflix"):
        super().__init__(name)
        self.detection_level = "HIGH"
        
        # FIXED: Updated Japanese language patterns
        self.language_patterns = {
            "en": {
                "step_detect": ["STEP 1 OF 4", "STEP 1 OF 3", "Choose your plan", "Next"],
                "buttons": ["Next", "Continue", "Get Started"],
                "currencies": ["£", "$"],
                "price_format": r"\$(\d+)\.(\d{2})"
            },
            "de": {
                "step_detect": ["SCHRITT 1 VON 3", "SCHRITT 1 VON 4", "Wählen Sie Ihr Abo", "Weiter"],
                "buttons": ["Weiter", "Fortfahren", "Jetzt loslegen"],
                "currencies": ["€"],
                "price_format": r"€\s*(\d+)[,.](\d{2})|(\d+)[,.](\d{2})\s*€"
            },
            "fr": {
                "step_detect": ["ÉTAPE 1 SUR", "Choisissez votre forfait", "Suivant"],
                "buttons": ["Suivant", "Continuer", "Commencer"],
                "currencies": ["€"],
                "price_format": r"€\s*(\d+)[,.](\d{2})|(\d+)[,.](\d{2})\s*€"
            },
            "es": {
                "step_detect": ["PASO 1 DE", "Elige tu plan", "Siguiente"],
                "buttons": ["Siguiente", "Continuar", "Empezar"],
                "currencies": ["€", "$"],
                "price_format": r"€\s*(\d+)[,.](\d{2})|(\d+)[,.](\d{2})\s*€|\$(\d+)\.(\d{2})"
            },
            "it": {
                "step_detect": ["PASSAGGIO 1 DI 3", "PASSAGGIO 1 DI 4", "Scegli un piano", "Continua"],
                "buttons": ["Continua", "Avanti", "Inizia"],
                "currencies": ["€"],
                "price_format": r"€\s*(\d+)[,.](\d{2})|(\d+)[,.](\d{2})\s*€"
            },
            "nl": {
                "step_detect": ["STAP 1 VAN 3", "STAP 1 VAN 4", "Kies je abonnement", "Volgende"],
                "buttons": ["Volgende", "Doorgaan", "Aan de slag"],
                "currencies": ["€"],
                "price_format": r"€\s*(\d+)[,.](\d{2})|(\d+)[,.](\d{2})\s*€"
            },
            "pt": {
                "step_detect": ["PASSO 1 DE 3", "PASSO 1 DE 4", "Escolha seu plano", "Próximo"],
                "buttons": ["Próximo", "Continuar", "Avançar", "Começar"],
                "currencies": ["R$"],
                "price_format": r"R\$\s*(\d+)[,.](\d{2})|(\d+)[,.](\d{2})\s*R\$"
            },
            # FIXED: Corrected Japanese patterns
            "ja": {
                "step_detect": ["ステップ1/3", "ステップ1/4", "プランを選択", "続ける"],
                "buttons": ["続ける", "次へ", "開始", "始める"],  # Continue, Next, Start, Begin
                "currencies": ["¥", "￥"],
                "price_format": r"¥\s*(\d+)|￥\s*(\d+)|(\d+)\s*円"
            }
        }
        
        self.country_to_lang = {
            "us": "en", "uk": "en", "gb": "en", "ca": "en", "au": "en",
            "de": "de", "at": "de", "ch": "de",
            "fr": "fr", "be": "fr",
            "es": "es", "mx": "es", "ar": "es",
            "it": "it",
            "nl": "nl",
            "br": "pt",
            "jp": "ja",  # Japanese mapping
        }
    
    def get_language_for_country(self, country):
        """Get language patterns for a country."""
        lang_code = self.country_to_lang.get(country.lower(), "en")
        return self.language_patterns.get(lang_code, self.language_patterns["en"])
    
    def get_url(self, country):
        """Get the URL for Netflix pricing page."""
        country_lower = country.lower()
        
        url_mapping = {
            "us": "https://www.netflix.com/signup",
            "uk": "https://www.netflix.com/signup?locale=en-GB", 
            "de": "https://www.netflix.com/signup?locale=de-DE",
            "fr": "https://www.netflix.com/signup?locale=fr-FR",
            "jp": "https://www.netflix.com/signup?locale=ja-JP",
            "in": "https://www.netflix.com/signup?locale=en-IN",
            "br": "https://www.netflix.com/signup?locale=pt-BR",
            "ca": "https://www.netflix.com/signup?locale=en-CA",
            "au": "https://www.netflix.com/signup?locale=en-AU",
            "mx": "https://www.netflix.com/signup?locale=es-MX",
            "es": "https://www.netflix.com/signup?locale=es-ES",
            "it": "https://www.netflix.com/signup?locale=it-IT",
            "nl": "https://www.netflix.com/signup?locale=nl-NL",
        }
        
        return url_mapping.get(country_lower, f"https://www.netflix.com/{country_lower}/signup/planform")
    
    def get_stealth_browser_args(self):
        """Get browser arguments for maximum stealth."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--exclude-switches=enable-automation",
            "--disable-extensions-except",
            "--disable-plugins-discovery",
            "--disable-default-apps",
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-field-trial-config",
            "--disable-ipc-flooding-protection",
            "--window-size=1920,1080",
            "--start-maximized"
        ]
    
    def get_firefox_args(self):
        """Get Firefox-specific arguments."""
        return [
            "--width=1920",
            "--height=1080",
            "--new-instance",
            "--private-window"
        ]
    
    def prepare_context(self, context, country):
        """Prepare context with anti-detection measures."""
        try:
            print(f"  Applying HIGH-level stealth configuration for Netflix...")
            
            context.add_init_script("""
                // Remove webdriver property completely
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Mock realistic plugins array
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: "Chrome PDF Plugin", filename: "internal-pdf-viewer"},
                        {name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai"},
                        {name: "Native Client", filename: "internal-nacl-plugin"}
                    ]
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Remove automation traces
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
                
                console.log('Netflix stealth mode activated');
            """)
            
            context.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "max-age=0",
                "Sec-Ch-Ua": '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
            })
            
            context.add_cookies([
                {
                    "name": "nfvdid",
                    "value": f"BQFmAAEBEHQ{random.randint(10000, 99999)}", 
                    "domain": ".netflix.com", 
                    "path": "/"
                },
                {
                    "name": "SecureNetflixId",
                    "value": f"v%3D2%26mac%3DAQEAEAABABQdwdGV{random.randint(1000, 9999)}", 
                    "domain": ".netflix.com", 
                    "path": "/"
                }
            ])
            
            print(f"  ✓ Applied comprehensive stealth configuration")
            
        except Exception as e:
            print(f"  Error setting stealth configuration: {e}")
    
    def handle_cookie_consent(self, page):
        """Ultra-stealth cookie handling."""
        try:
            print("  Applying ultra-stealth cookie handling for Netflix...")
            
            time.sleep(random.uniform(3.0, 5.0))
            
            page.evaluate("""() => {
                try {
                    document.cookie = "OptanonAlertBoxClosed=2024-01-01T00:00:00.000Z; path=/; domain=.netflix.com; max-age=31536000";
                    document.cookie = "OptanonConsent=isGpcEnabled=0&datestamp=Mon+Jan+01+2024; path=/; domain=.netflix.com; max-age=31536000";
                    document.cookie = "cookieConsent=true; path=/; domain=.netflix.com; max-age=31536000";
                    
                    const style = document.createElement('style');
                    style.textContent = `
                        div[class*="cookie"], div[id*="cookie"],
                        div[class*="consent"], div[id*="consent"],
                        div[class*="gdpr"], div[id*="gdpr"],
                        .cookie-disclosure, .gdpr-disclosure,
                        [data-uia*="cookie"], [data-uia*="consent"] {
                            opacity: 0 !important;
                            pointer-events: none !important;
                            z-index: -9999 !important;
                            display: none !important;
                        }
                    `;
                    document.head.appendChild(style);
                    
                    console.log('Netflix cookies set silently');
                } catch(e) {
                    console.log('Cookie setting failed:', e);
                }
            }""")
            
            print("  ✓ Cookies set silently without DOM interaction")
            time.sleep(random.uniform(2.0, 3.0))
            return True
                
        except Exception as e:
            print(f"  Error in ultra-stealth cookie handling: {e}")
            return False
    
    def perform_site_interactions(self, page):
        """FIXED: Netflix interactions with better Japanese button detection."""
        try:
            print("  Performing stealth Netflix interactions...")
            
            current_url = page.url
            print(f"  Current URL for country detection: {current_url}")
            
            country = self._extract_country_from_url(current_url)
            lang_patterns = self.get_language_for_country(country)
            
            print(f"  Using language patterns for country: {country}")
            print(f"  Step detection patterns: {lang_patterns['step_detect']}")
            print(f"  Button texts to look for: {lang_patterns['buttons']}")
            
            time.sleep(random.uniform(3.0, 5.0))
            
            # Check current page state
            try:
                page_html = page.content()
                
                step_found = []
                for pattern in lang_patterns["step_detect"]:
                    if pattern in page_html:
                        step_found.append(pattern)
                        print(f"    Found step pattern: '{pattern}'")
                
                is_step_1 = len(step_found) > 0
                
                if is_step_1:
                    print(f"  ✓ Detected Step 1 page using patterns: {step_found}")
                else:
                    print("  Not on Step 1 or already on pricing page")
                
            except Exception as e:
                print(f"  Could not analyze page content: {e}")
                is_step_1 = True
                print("  Assuming Step 1 - will try to click Next")
            
            # FIXED: Enhanced button detection for Japanese
            if is_step_1:
                print("  Attempting to click Next button to reach pricing...")
                
                # FIXED: Try direct clicking with the exact Japanese text first
                if country == "jp":
                    print("  Trying direct Japanese button click...")
                    try:
                        # The exact text we see in the screenshot
                        continue_button = page.locator("text=続ける").first
                        if continue_button.count() > 0:
                            print("    Found exact Japanese '続ける' button")
                            continue_button.click()
                            print("    ✓ Clicked Japanese continue button!")
                            
                            # Wait for navigation
                            time.sleep(random.uniform(4.0, 6.0))
                            
                            # Check if we successfully navigated
                            new_html = page.content()
                            new_url = page.url
                            print(f"    New URL: {new_url}")
                            
                            has_currency = any(curr in new_html for curr in lang_patterns["currencies"])
                            has_pricing_terms = any(term in new_html for term in ["Standard", "Premium", "plan", "プラン"])
                            
                            print(f"    Has currency ({lang_patterns['currencies']}): {has_currency}")
                            print(f"    Has pricing terms: {has_pricing_terms}")
                            
                            if has_currency and has_pricing_terms:
                                print("    ✓ SUCCESS! Found pricing content after Japanese button click!")
                                return  # Exit early - we're done
                            else:
                                print("    Button clicked but no pricing content yet - continuing...")
                        else:
                            print("    Japanese '続ける' button not found")
                    except Exception as e:
                        print(f"    Error with direct Japanese button click: {e}")
                
                # Fallback strategies with better selectors
                next_strategies = []
                
                # Language-specific button text strategies
                for button_text in lang_patterns["buttons"]:
                    # Multiple selector formats
                    selectors = [
                        f'button:has-text("{button_text}")',
                        f'[role="button"]:has-text("{button_text}")',
                        f'input[value="{button_text}"]',
                        f'a:has-text("{button_text}")'
                    ]
                    for selector in selectors:
                        next_strategies.append((selector, f"{button_text} button ({country})"))
                
                # CSS class and data attribute strategies
                next_strategies.extend([
                    ('[data-uia="next-button"]', "Netflix Next button"),
                    ('button[type="submit"]', "submit button"),
                    ('.btn-red', "Netflix red button"),
                    ('.nf-btn-primary', "Netflix primary button"),
                    ('button.btn', "button with btn class"),
                    ('[role="button"]', "element with button role"),
                ])
                
                clicked_next = False
                
                for selector, description in next_strategies:
                    if clicked_next:
                        break
                        
                    try:
                        print(f"    Trying {description}: {selector}")
                        elements = page.locator(selector).all()
                        
                        if len(elements) == 0:
                            print(f"    No elements found with {selector}")
                            continue
                        
                        print(f"    Found {len(elements)} elements with {selector}")
                        
                        for i, element in enumerate(elements):
                            try:
                                element_text = element.text_content() or ""
                                print(f"      Element {i+1} text: '{element_text}'")
                                
                                # For generic selectors, be more selective
                                if selector in ['button', '[role="button"]']:
                                    # Check if this is likely a continue/next button
                                    element_text_lower = element_text.lower()
                                    
                                    # Build comprehensive list including Japanese
                                    all_button_texts = []
                                    for lang_data in self.language_patterns.values():
                                        all_button_texts.extend([btn.lower() for btn in lang_data["buttons"]])
                                    
                                    # Japanese terms (exact match needed)
                                    japanese_terms = ['続ける', '次へ', '開始', '始める']
                                    
                                    has_button_text = (
                                        any(btn_text in element_text_lower for btn_text in all_button_texts) or
                                        any(term in element_text for term in japanese_terms) or
                                        any(term in element_text_lower for term in ['next', 'continue', 'weiter', 'suivant', 'continua', 'volgende', 'próximo'])
                                    )
                                    
                                    if not has_button_text:
                                        print(f"      Skipping element {i+1} - no relevant button text")
                                        continue
                                
                                print(f"    Attempting to click element {i+1}")
                                
                                # Try multiple click methods
                                click_methods = [
                                    lambda: element.click(),
                                    lambda: element.click(force=True),
                                    lambda: page.locator(selector).nth(i).click()
                                ]
                                
                                click_success = False
                                for j, click_method in enumerate(click_methods):
                                    try:
                                        print(f"      Click method {j+1}...")
                                        click_method()
                                        click_success = True
                                        break
                                    except Exception as click_e:
                                        print(f"      Click method {j+1} failed: {click_e}")
                                        continue
                                
                                if not click_success:
                                    print(f"      All click methods failed for element {i+1}")
                                    continue
                                
                                print("    ✓ Clicked!")
                                
                                print("    Waiting for page to navigate...")
                                time.sleep(random.uniform(4.0, 6.0))
                                
                                # Check if we successfully navigated
                                try:
                                    new_html = page.content()
                                    new_url = page.url
                                    
                                    print(f"    New URL: {new_url}")
                                    
                                    has_currency = any(curr in new_html for curr in lang_patterns["currencies"])
                                    has_pricing_terms = any(term in new_html for term in ["Standard", "Premium", "plan", "abo", "forfait", "piano", "abonnement", "プラン"])
                                    
                                    print(f"    Has currency ({lang_patterns['currencies']}): {has_currency}")
                                    print(f"    Has pricing terms: {has_pricing_terms}")
                                    
                                    if has_currency and has_pricing_terms:
                                        print("    ✓ SUCCESS! Found pricing content!")
                                        clicked_next = True
                                        break
                                    elif any(step_word in new_html for step_word in ["STEP 2", "SCHRITT 2", "ÉTAPE 2", "PASO 2", "PASSAGGIO 2", "STAP 2", "ステップ2"]):
                                        print("    ✓ Page changed to step 2 - might have pricing soon...")
                                        time.sleep(random.uniform(3.0, 5.0))
                                        
                                        final_html = page.content()
                                        final_has_currency = any(curr in final_html for curr in lang_patterns["currencies"])
                                        if final_has_currency:
                                            print("    ✓ SUCCESS! Pricing content loaded after delay!")
                                            clicked_next = True
                                            break
                                    else:
                                        print("    Page didn't navigate to pricing, trying next element...")
                                        
                                except Exception as e:
                                    print(f"    Error checking navigation result: {e}")
                                    
                            except Exception as e:
                                print(f"    Error clicking element {i+1}: {e}")
                                continue
                        
                        if clicked_next:
                            break
                            
                    except Exception as e:
                        print(f"    Error with strategy {description}: {e}")
                        continue
                
                if not clicked_next:
                    print("  ⚠️ Could not click Next button - trying direct URL navigation...")
                    
                    try:
                        direct_url = f"https://www.netflix.com/{country}/signup/planform"
                        print(f"  Trying direct navigation to: {direct_url}")
                        
                        page.goto(direct_url, wait_until="domcontentloaded", timeout=30000)
                        time.sleep(random.uniform(4.0, 6.0))
                        
                        final_html = page.content()
                        if any(curr in final_html for curr in lang_patterns["currencies"]):
                            print("  ✓ Direct navigation to pricing successful!")
                        else:
                            print("  Direct navigation didn't show pricing either")
                        
                    except Exception as e:
                        print(f"  Direct navigation failed: {e}")
            
            # Natural scrolling
            print("  Performing natural page exploration...")
            
            page.evaluate("window.scrollTo(0, 100)")
            time.sleep(random.uniform(1.0, 2.0))
            
            page.evaluate("window.scrollTo(0, 400)")
            time.sleep(random.uniform(1.5, 2.5))
            
            page.evaluate("window.scrollTo(0, 800)")
            time.sleep(random.uniform(1.0, 1.8))
            
            page.evaluate("window.scrollTo(0, 200)")
            time.sleep(random.uniform(0.8, 1.5))
            
            print("  ✓ Completed natural page interactions")
            
        except Exception as e:
            print(f"  Error in Netflix stealth interactions: {e}")
    
    def _extract_country_from_url(self, url):
        """Extract country code from Netflix URL."""
        try:
            print(f"    Extracting country from URL: {url}")
            
            if "locale=" in url:
                import re
                locale_match = re.search(r'locale=([a-z]{2})-([A-Z]{2})', url)
                if locale_match:
                    language_code = locale_match.group(1)
                    country_code = locale_match.group(2).lower()
                    print(f"    Detected locale: {language_code}-{country_code.upper()}")
                    print(f"    Using country code: {country_code}")
                    return country_code
            
            # Direct country code detection from URL path
            country_patterns = {
                "/de/": "de", "/gb/": "uk", "/fr/": "fr", "/es/": "es", 
                "/it/": "it", "/nl/": "nl", "/mx/": "mx", "/br/": "br", 
                "/ca/": "ca", "/au/": "au", "/jp/": "jp", "/kr/": "kr", 
                "/in/": "in", "/pl/": "pl", "/se/": "se", "/no/": "no", "/dk/": "dk"
            }
            
            for pattern, country in country_patterns.items():
                if pattern in url or url.endswith(pattern.replace("/", "")):
                    print(f"    Detected country: {country.upper()}")
                    return country
            
            print("    No country detected, defaulting to US")
            return "us"
            
        except Exception as e:
            print(f"    Error extracting country from URL: {e}")
            return "us"
    
    def extract_pricing_data(self, page):
        """FIXED: Extract Netflix pricing with properly escaped JavaScript."""
        try:
            print("  Extracting Netflix pricing data...")
            
            current_url = page.url
            country = self._extract_country_from_url(current_url)
            lang_patterns = self.get_language_for_country(country)
            
            time.sleep(random.uniform(2.0, 3.0))
            
            # FIXED: Properly escape JavaScript strings to avoid line break errors
            pricing_data = page.evaluate("""
            (langPatterns) => {
                const pageText = document.body.textContent || '';
                
                // Enhanced detection with Japanese support
                const hasPricing = langPatterns.currencies.some(curr => pageText.includes(curr)) && (
                    pageText.includes('Standard') || 
                    pageText.includes('Premium') || 
                    pageText.includes('Monthly price') ||
                    pageText.includes('Monatlicher Preis') ||
                    pageText.includes('Prix mensuel') ||
                    pageText.includes('Prezzo mensile') ||
                    pageText.includes('Maandelijkse prijs') ||
                    pageText.includes('plan') ||
                    pageText.includes('piano') ||
                    pageText.includes('abonnement') ||
                    pageText.includes('プラン') ||  // Japanese for "plan"
                    pageText.includes('月額')     // Japanese for "monthly"
                );
                
                if (!hasPricing) {
                    return [{
                        message: 'No pricing detected on current page',
                        page_url: window.location.href,
                        page_title: document.title,
                        content_sample: pageText.substring(0, 500),
                        expected_currencies: langPatterns.currencies,
                        debug_info: {
                            has_standard: pageText.includes('Standard'),
                            has_premium: pageText.includes('Premium'),
                            has_plan_jp: pageText.includes('プラン'),
                            has_monthly_jp: pageText.includes('月額'),
                            currency_checks: langPatterns.currencies.map(curr => ({
                                currency: curr,
                                found: pageText.includes(curr)
                            }))
                        }
                    }];
                }
                
                // Enhanced selectors for Netflix pricing cards
                const planSelectors = [
                    '[data-uia="plan-card"]',
                    '[data-uia*="plan"]',
                    '.plan-card',
                    'div:has(.plan-title)',
                    'div:has([data-uia*="price"])',
                    'div[class*="plan"]',
                    'div[class*="card"]'
                ];
                
                let plans = [];
                
                for (const selector of planSelectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length >= 2) {
                            plans = Array.from(elements);
                            console.log('Found ' + plans.length + ' plans with: ' + selector);
                            break;
                        }
                    } catch(e) {
                        continue;
                    }
                }
                
                // Fallback: Find pricing containers by DOM analysis
                if (plans.length === 0) {
                    const allElements = Array.from(document.querySelectorAll('*'));
                    const priceElements = allElements.filter(el => {
                        const text = el.textContent || '';
                        const hasPrice = langPatterns.currencies.some(curr => 
                            text.includes(curr) && text.match(new RegExp('\\\\' + curr + '\\\\d+|\\\\d+\\\\' + curr))
                        );
                        return hasPrice && 
                               el.offsetHeight > 100 && 
                               el.offsetWidth > 200 &&
                               (text.includes('Standard') || text.includes('Premium') || text.includes('abonnement') || text.includes('プラン'));
                    });
                    
                    if (priceElements.length > 0) {
                        const containers = new Set();
                        priceElements.forEach(el => {
                            let parent = el.parentElement;
                            while (parent && parent !== document.body) {
                                if (parent.offsetHeight > 300 && parent.offsetWidth > 250) {
                                    containers.add(parent);
                                    break;
                                }
                                parent = parent.parentElement;
                            }
                        });
                        
                        if (containers.size > 0) {
                            plans = Array.from(containers);
                            console.log('Found ' + plans.length + ' plan containers via DOM analysis');
                        }
                    }
                }
                
                if (plans.length === 0) {
                    return [{
                        message: 'Could not locate Netflix pricing plans',
                        page_url: window.location.href,
                        debug_info: {
                            has_currencies: langPatterns.currencies.map(curr => ({curr: curr, found: pageText.includes(curr)})),
                            has_standard: pageText.includes('Standard'),
                            has_premium: pageText.includes('Premium'),
                            has_abonnement: pageText.includes('abonnement'),
                            has_plan_jp: pageText.includes('プラン'),
                            page_length: pageText.length
                        }
                    }];
                }
                
                // Extract data from each plan with comprehensive language support including Japanese
                return plans.map((plan, index) => {
                    const planText = plan.textContent || '';
                    
                    // Extract plan name with multi-language support including Japanese
                    let name = '';
                    
                    // Standard patterns
                    if (planText.match(/standard.*with.*ads/i)) name = 'Standard with ads';
                    else if (planText.match(/standard(?!.*with.*ads)/i)) name = 'Standard';
                    else if (planText.match(/premium/i)) name = 'Premium';
                    else if (planText.match(/basic/i)) name = 'Basic';
                    // German
                    else if (planText.match(/standard.*mit.*werbung/i)) name = 'Standard mit Werbung';
                    else if (planText.match(/basis/i)) name = 'Basis';
                    // Italian
                    else if (planText.match(/standard.*con.*pubblicità/i)) name = 'Standard con pubblicità';
                    else if (planText.match(/base/i)) name = 'Base';
                    // Dutch
                    else if (planText.match(/standaard.*met.*advertenties/i)) name = 'Standaard met advertenties';
                    else if (planText.match(/standaard/i)) name = 'Standaard';
                    // Portuguese (Brazil)
                    else if (planText.match(/padrão.*com.*anúncios/i)) name = 'Padrão com anúncios';
                    else if (planText.match(/padrão/i)) name = 'Padrão';
                    // Japanese patterns
                    else if (planText.includes('スタンダード')) name = 'スタンダード';
                    else if (planText.includes('プレミアム')) name = 'プレミアム';
                    else if (planText.includes('ベーシック')) name = 'ベーシック';
                    
                    // Look in specific elements if no name found
                    if (!name) {
                        const nameElements = plan.querySelectorAll('h1, h2, h3, h4, [class*="title"], [class*="name"]');
                        for (const el of nameElements) {
                            const text = el.textContent?.trim();
                            if (text && text.length < 30 && (
                                text.match(/(standard|premium|basic|basis|standaard|padrão)/i) ||
                                text.includes('スタンダード') || text.includes('プレミアム') || text.includes('ベーシック')
                            )) {
                                name = text;
                                break;
                            }
                        }
                    }
                    
                    if (!name) name = 'Plan ' + (index + 1);
                    
                    // Extract price with enhanced multi-currency support including Japanese Yen
                    let priceInfo = {
                        display: 'Price not found',
                        numeric: null,
                        currency: null
                    };
                    
                    // Try each currency pattern for this country
                    for (const currency of langPatterns.currencies) {
                        let pricePattern;
                        if (currency === ') {
                            pricePattern = /\\$?(\\d+\\.\\d+)/g;
                        } else if (currency === '€') {
                            // European formatting: €9,99 or 9,99€ or 9.99€
                            pricePattern = /€\\s*(\\d+)[,.]\\d+|(\\d+)[,.]\\d+\\s*€/g;
                        } else if (currency === '£') {
                            pricePattern = /£(\\d+\\.\\d+)/g;
                        } else if (currency === 'R) {
                            // Brazilian Real pattern: R$ 25,90 or 25,90 R$
                            pricePattern = /R\\$\\s*(\\d+)[,.]\\d+|(\\d+)[,.]\\d+\\s*R\\$/g;
                        } else if (currency === '¥' || currency === '￥') {
                            // Japanese Yen patterns: ¥990, ￥990, 990円
                            pricePattern = /[¥￥]\\s*(\\d+)|(\\d+)\\s*円/g;
                        }
                        
                        const priceMatches = planText.match(pricePattern);
                        if (priceMatches && priceMatches.length > 0) {
                            const price = priceMatches[0];
                            let numericPrice;
                            
                            if (currency === ' || currency === '£') {
                                numericPrice = parseFloat(price.replace(/[$£]/, ''));
                            } else if (currency === '€') {
                                const cleanPrice = price.replace(/[€\\s]/g, '').replace(',', '.');
                                numericPrice = parseFloat(cleanPrice);
                            } else if (currency === 'R) {
                                const cleanPrice = price.replace(/[R$\\s]/g, '').replace(',', '.');
                                numericPrice = parseFloat(cleanPrice);
                            } else if (currency === '¥' || currency === '￥') {
                                // For Yen, extract just the numbers
                                const cleanPrice = price.replace(/[¥￥円\\s]/g, '');
                                numericPrice = parseFloat(cleanPrice);
                            }
                            
                            if (!isNaN(numericPrice)) {
                                priceInfo = {
                                    display: currency + numericPrice.toString(),
                                    numeric: numericPrice,
                                    currency: currency
                                };
                                break;
                            }
                        }
                    }
                    
                    // Extract features
                    const features = [];
                    const featureElements = plan.querySelectorAll('li, p, div');
                    
                    for (const el of featureElements) {
                        const text = el.textContent?.trim();
                        if (text && 
                            text.length > 10 && 
                            text.length < 100 && 
                            !langPatterns.currencies.some(curr => text.includes(curr)) &&
                            !text.includes('Monthly price') &&
                            !text.includes('Monatlicher Preis') &&
                            !text.includes('Prezzo mensile') &&
                            !text.includes('Maandelijkse prijs') &&
                            !text.includes('月額') &&
                            text.match(/[a-zA-Zあ-んア-ン一-龯]/)) {  // Include Japanese characters
                            features.push(text);
                        }
                    }
                    
                    return {
                        name: name,
                        price: priceInfo,
                        features: features.slice(0, 6)
                    };
                });
            }
            """, lang_patterns)
            
            print(f"\n==== EXTRACTED NETFLIX PRICING ({country.upper()}) ====")
            print(json.dumps(pricing_data, indent=2))
            print("===================================\n")
            
            return {
                "site": "netflix",
                "country": country,
                "url": page.url,
                "plans": pricing_data
            }
            
        except Exception as e:
            print(f"  Error extracting Netflix pricing: {e}")
            return {
                "site": "netflix",
                "url": page.url if hasattr(page, 'url') else "unknown",
                "error": str(e),
                "plans": []
            }
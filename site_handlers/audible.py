"""
Audible-specific handler with international domain support.
"""
import json
import time
import random
from .base_handler import BaseSiteHandler

class AudibleHandler(BaseSiteHandler):
    """Handler for Audible with multi-market domain support."""
    
    def __init__(self, name="audible"):
        super().__init__(name)
        self.detection_level = "LOW"  # Audible is generally not heavily protected
        
        # Country-specific domain mapping
        self.domain_mapping = {
            "us": "com",
            "uk": "co.uk", 
            "fr": "fr",
            "ca": "ca",
            "de": "de",
            "au": "com.au",
            "jp": "co.jp",
            "in": "in",
            "br": "com.br",
            "mx": "com",  # Mexico uses US domain
            "it": "it",
            "es": "es",
            "nl": "co.uk"  # Netherlands uses UK domain
        }
        
        # Country-specific fallback URLs (some markets use different paths)
        self.fallback_paths = {
            "us": ["/ep/memberbenefits", "/membership", "/plans"],
            "uk": ["/ep/memberbenefits", "/membership", "/plans"],
            "fr": ["/ep/1er-livre-audio-offert", "/ep/memberbenefits", "/abonnement"],  # French main page
            "de": ["/ep/flexiabo_01", "/ep/prime", "/mitgliedschaft", "/ep/memberbenefits"],  # German pricing pages
            "ca": ["/ep/memberbenefits", "/membership", "/plans"],
            "au": ["/ep/memberbenefits", "/membership", "/plans"],
            "jp": ["/ep/membership", "/ep/audible/", "/ep/memberbenefits"],  # Japanese membership pages
            "in": ["/ep/free-trial-amazon-prime", "/", "/ep/audible-member-benefit", "/ep/memberbenefits"],  # Indian pricing pages
            "br": ["/ep/lto", "/", "/assinatura", "/ep/memberbenefits"],  # Brazilian pricing - LTO page
            "mx": ["/ep/espanol-plus-membresia", "/ep/audiblelatino", "/ep/memberbenefits"],  # Mexico uses US domain with Spanish content
            "it": ["/ep/lto", "/ep/come-funziona-audible", "/ep/memberbenefits"],  # Italian pricing pages
            "es": ["/blog/suscripcion-de-audible", "/ep/amu", "/ep/memberbenefits"],  # Spanish pricing pages - try blog first
            "nl": ["/ep/memberbenefits", "/membership", "/plans"]  # Netherlands uses UK domain
        }
    
    def get_url(self, country):
        """Get the correct Audible URL for the given country."""
        domain = self.domain_mapping.get(country.lower(), "com")
        
        # Use the first fallback path for the country as primary
        paths = self.fallback_paths.get(country.lower(), ["/ep/memberbenefits"])
        primary_path = paths[0]
        
        return f"https://www.audible.{domain}{primary_path}"
    
    def get_fallback_urls(self, country):
        """Get fallback URLs if the primary URL fails."""
        domain = self.domain_mapping.get(country.lower(), "com")
        base_url = f"https://www.audible.{domain}"
        
        paths = self.fallback_paths.get(country.lower(), ["/ep/memberbenefits", "/membership"])
        return [f"{base_url}{path}" for path in paths[1:]]  # Skip the first one as it's the primary
    
    def prepare_context(self, context, country):
        """Prepare context with Audible-specific settings."""
        # Set appropriate language headers for the country
        language_mapping = {
            "us": "en-US,en;q=0.9",
            "uk": "en-GB,en;q=0.9",
            "fr": "fr-FR,fr;q=0.9,en;q=0.8",
            "ca": "en-CA,en;q=0.9,fr;q=0.8",
            "de": "de-DE,de;q=0.9,en;q=0.8",
            "au": "en-AU,en;q=0.9",
            "jp": "ja-JP,ja;q=0.9,en;q=0.8",
            "in": "en-IN,en;q=0.9,hi;q=0.8",
            "br": "pt-BR,pt;q=0.9,en;q=0.8",
            "mx": "es-MX,es;q=0.9,en;q=0.8",
            "it": "it-IT,it;q=0.9,en;q=0.8",
            "es": "es-ES,es;q=0.9,en;q=0.8",
            "nl": "nl-NL,nl;q=0.9,en;q=0.8"
        }
        
        accept_language = language_mapping.get(country.lower(), "en-US,en;q=0.9")
        
        context.set_extra_http_headers({
            "Accept-Language": accept_language,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })
        
        print(f"  Set Audible headers for {country.upper()}: {accept_language}")
    
    def handle_cookie_consent(self, page):
        """Handle Audible's cookie consent dialogs."""
        cookie_selectors = [
            # Common Audible cookie consent selectors
            'button:has-text("Accept Cookies")',
            'button:has-text("Accept All")',
            'button:has-text("I Accept")',
            'button:has-text("Accepter")',  # French
            'button:has-text("Akzeptieren")',  # German
            'button:has-text("Aceitar")',  # Portuguese
            'button:has-text("Aceptar")',  # Spanish
            'button:has-text("Accetta")',  # Italian
            'button:has-text("Accepteren")',  # Dutch
            'button:has-text("同意")',  # Japanese
            'button[data-testid="accept-cookies"]',
            'button[id*="cookie"][id*="accept"]',
            'button[class*="cookie"][class*="accept"]',
            '#sp-cc-accept',
            '.sp-cc-accept',
            'button[aria-label*="Accept"]',
            # Additional selectors for persistent banners
            '[class*="banner"] button',
            '[class*="consent"] button',
            '[class*="notification"] button',
            '.adchoices-close',
            '.close-banner'
        ]
        
        for selector in cookie_selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"  Found and clicking cookie consent: {selector}")
                    page.click(selector, timeout=5000)
                    page.wait_for_timeout(2000)
                    return True
            except Exception as e:
                continue
        
        # Try to hide any remaining dark overlays or banners with CSS
        try:
            page.evaluate("""
                // Hide common banner/overlay patterns
                const selectors = [
                    '[class*="banner"]',
                    '[class*="overlay"]', 
                    '[class*="notification"]',
                    '[style*="background: black"]',
                    '[style*="background-color: black"]',
                    '[style*="background:#000"]',
                    '[style*="background-color:#000"]'
                ];
                selectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        if (el.offsetHeight < 100) { // Only hide small banners
                            el.style.display = 'none';
                        }
                    });
                });
            """)
            print("  Applied CSS hiding for remaining banners")
        except:
            pass
        
        return False
    
    def perform_site_interactions(self, page):
        """Perform Audible-specific interactions to reveal pricing."""
        try:
            # Get country from URL to adjust wait times
            current_url = page.url
            is_japan = '.co.jp' in current_url
            is_india = '.in' in current_url
            
            # Wait longer for Japanese pages as they load more slowly
            wait_time = 5000 if is_japan else 3000
            page.wait_for_timeout(wait_time)
            
            # Additional banner cleanup - hide any remaining dark bars
            try:
                page.evaluate("""
                    // Remove any dark horizontal bars that might be notifications
                    const darkBars = document.querySelectorAll('*');
                    darkBars.forEach(el => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        if ((style.backgroundColor === 'rgb(0, 0, 0)' || 
                             style.backgroundColor === 'black') &&
                            rect.height > 30 && rect.height < 100 &&
                            rect.width > 200) {
                            el.style.display = 'none';
                        }
                    });
                """)
                print("  Applied additional banner cleanup")
            except:
                pass
            
            # Check if we're on a page that doesn't have pricing content
            page_content = page.content().lower()
            
            # Enhanced content detection for different markets
            has_pricing_content = (
                "abonnement" in page_content or 
                "membership" in page_content or 
                "pricing" in page_content or
                "plan" in page_content or
                "premium" in page_content or
                "会員" in page_content or  # Japanese: member
                "プラン" in page_content or  # Japanese: plan
                "₹199" in page_content or  # Indian pricing
                "free trial" in page_content or
                "30-day" in page_content or
                "30 day" in page_content
            )
            
            if not has_pricing_content and len(page_content) < 10000:
                print(f"  Page appears to have minimal content, trying fallback URLs...")
                return self._try_fallback_urls(page)
            
            # For India, try clicking on pricing/trial buttons to reveal more info
            if is_india:
                trial_buttons = [
                    'button:has-text("Start your 30-day free trial")',
                    'button:has-text("Start your free trial")',
                    'a:has-text("Start your 30-day free trial")',
                    'a:has-text("Start your free trial")',
                    '.trial-button',
                    '[data-testid="trial-button"]'
                ]
                
                for selector in trial_buttons:
                    try:
                        if page.locator(selector).count() > 0:
                            print(f"  Clicking trial button to reveal pricing: {selector}")
                            page.click(selector)
                            page.wait_for_timeout(2000)
                            break
                    except:
                        continue
            
            # Look for sign-in prompts and dismiss them
            sign_in_selectors = [
                'button:has-text("Not now")',
                'button:has-text("Maybe later")',
                'button:has-text("Plus tard")',  # French
                'button:has-text("Pas maintenant")',  # French
                'button:has-text("Non ora")',  # Italian
                'button:has-text("Più tardi")',  # Italian
                'button:has-text("後で")',  # Japanese: later
                'button:has-text("いいえ")',  # Japanese: no
                '.modal button[aria-label="Close"]',
                '.overlay button[aria-label="Close"]'
            ]
            
            for selector in sign_in_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Dismissing sign-in prompt: {selector}")
                        page.click(selector)
                        page.wait_for_timeout(1000)
                        break
                except:
                    continue
            
            # Scroll to ensure all pricing information is loaded
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(2000)
            
            # For Japan, try scrolling down further to trigger content loading
            if is_japan:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(1000)
            
            # Look for pricing toggle buttons (monthly/yearly) and ensure monthly is selected
            toggle_selectors = [
                'button:has-text("Monthly")',
                'button:has-text("Mensuel")',  # French
                'button:has-text("Mensile")',  # Italian
                'button:has-text("月額")',  # Japanese: monthly
                'input[value="monthly"]',
                'button[data-testid="monthly"]',
                '.billing-toggle button:first-child'
            ]
            
            for selector in toggle_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Setting to monthly pricing: {selector}")
                        page.click(selector)
                        page.wait_for_timeout(1500)
                        break
                except:
                    continue
            
            # Final scroll to capture everything
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1000)
            
            return True
            
        except Exception as e:
            print(f"  Error in Audible site interactions: {e}")
            return False
    
    def _try_fallback_urls(self, page):
        """Try fallback URLs when the primary URL doesn't work."""
        try:
            current_url = page.url
            domain_match = current_url.split('//')[1].split('/')[0]  # Extract domain
            country = None
            
            # Determine country from domain
            for c, d in self.domain_mapping.items():
                if f"audible.{d}" == domain_match:
                    country = c
                    break
            
            if not country:
                return False
            
            fallback_urls = self.get_fallback_urls(country)
            print(f"  Trying {len(fallback_urls)} fallback URLs for {country}")
            
            for url in fallback_urls:
                try:
                    print(f"    Trying: {url}")
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(3000)
                    
                    content = page.content().lower()
                    if ("membership" in content or "plan" in content or 
                        "premium" in content or "abonnement" in content):
                        print(f"    ✓ Found pricing content at: {url}")
                        return True
                        
                except Exception as e:
                    print(f"    ✗ Failed: {e}")
                    continue
            
            print(f"  All fallback URLs failed")
            return False
            
        except Exception as e:
            print(f"  Error trying fallback URLs: {e}")
            return False
    
    def extract_pricing_data(self, page):
        """Extract pricing data from Audible page."""
        try:
            pricing_data = {
                "tiers": [],
                "currency": "USD",  # Default, will be detected
                "country": None
            }
            
            # Try to detect currency from page
            currency_patterns = [
                r'\$(\d+\.?\d*)',  # USD
                r'£(\d+\.?\d*)',   # GBP
                r'€(\d+\.?\d*)',   # EUR
                r'¥(\d+\.?\d*)',   # JPY
                r'₹(\d+\.?\d*)',   # INR
                r'R\$(\d+\.?\d*)', # BRL
                r'C\$(\d+\.?\d*)'  # CAD
            ]
            
            page_content = page.content()
            
            # Common pricing tier selectors for Audible
            tier_selectors = [
                '.pricing-card',
                '.plan-card',
                '.membership-option',
                '[data-testid*="plan"]',
                '.tier'
            ]
            
            for selector in tier_selectors:
                try:
                    tiers = page.locator(selector).all()
                    if tiers:
                        print(f"  Found {len(tiers)} pricing tiers using selector: {selector}")
                        for tier in tiers:
                            tier_data = self._extract_tier_info(tier)
                            if tier_data:
                                pricing_data["tiers"].append(tier_data)
                        break
                except:
                    continue
            
            # If no structured tiers found, try to extract from text
            if not pricing_data["tiers"]:
                print("  No structured tiers found, attempting text extraction")
                pricing_data = self._extract_from_text(page_content)
            
            return pricing_data
            
        except Exception as e:
            print(f"  Error extracting Audible pricing data: {e}")
            return {"error": str(e)}
    
    def _extract_tier_info(self, tier_element):
        """Extract information from a single pricing tier element."""
        try:
            tier_info = {}
            
            # Try to get tier name
            name_selectors = ['.plan-name', '.tier-name', 'h3', 'h4', '.title']
            for selector in name_selectors:
                try:
                    name = tier_element.locator(selector).first.inner_text()
                    if name:
                        tier_info['name'] = name.strip()
                        break
                except:
                    continue
            
            # Try to get price
            price_selectors = ['.price', '.cost', '[data-testid*="price"]', '.amount']
            for selector in price_selectors:
                try:
                    price_text = tier_element.locator(selector).first.inner_text()
                    if price_text:
                        tier_info['price_text'] = price_text.strip()
                        # Extract numeric price
                        import re
                        price_match = re.search(r'(\d+\.?\d*)', price_text)
                        if price_match:
                            tier_info['price'] = float(price_match.group(1))
                        break
                except:
                    continue
            
            # Try to get features
            feature_selectors = ['.features li', '.benefits li', 'ul li', '.feature-list li']
            for selector in feature_selectors:
                try:
                    features = tier_element.locator(selector).all()
                    if features:
                        tier_info['features'] = [f.inner_text().strip() for f in features if f.inner_text().strip()]
                        break
                except:
                    continue
            
            return tier_info if tier_info else None
            
        except Exception as e:
            print(f"  Error extracting tier info: {e}")
            return None
    
    def _extract_from_text(self, page_content):
        """Fallback method to extract pricing from page text."""
        import re
        
        pricing_data = {
            "tiers": [],
            "extraction_method": "text_fallback"
        }
        
        # Look for common Audible pricing patterns
        patterns = [
            r'Premium Plus.*?(\$\d+\.?\d*)',
            r'Plus.*?(\$\d+\.?\d*)',
            r'Premium.*?(\$\d+\.?\d*)',
            r'monthly.*?(\$\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                pricing_data["tiers"].append({
                    "price_text": match,
                    "extraction_method": "regex"
                })
        
        return pricing_data
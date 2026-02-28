"""
YouTube handler with enhanced debugging for India and other problematic regions.
"""
import json
import time
import random
from .base_handler import BaseSiteHandler

class YoutubeHandler(BaseSiteHandler):
    """Handler for YouTube Premium with enhanced regional debugging."""
    
    def __init__(self, name="youtube"):
        super().__init__(name)
        # Countries that might need special handling
        self.problematic_regions = ['in', 'pk', 'bd', 'lk']
    
    def get_url(self, country):
        """Get URL for YouTube Premium with region-specific handling."""
        base_url = "https://www.youtube.com/premium/"
        
        # For problematic regions, try different URL strategies
        if country.lower() in self.problematic_regions:
            print(f"  Using enhanced URL strategy for {country.upper()}")
            # Try with explicit locale parameter
            return f"https://www.youtube.com/premium/?gl={country.upper()}&hl=en"
        
        return base_url
    
    def prepare_context(self, context, country):
        """Enhanced context preparation for problematic regions."""
        try:
            if country.lower() in self.problematic_regions:
                print(f"  Applying enhanced context settings for {country.upper()}")
                
                # Set additional headers for India/South Asia
                context.set_extra_http_headers({
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8" if country.lower() == 'in' else "en-US,en;q=0.9",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1"
                })
                
                # Set region-specific cookies preemptively
                context.add_cookies([
                    {
                        "name": "CONSENT",
                        "value": "YES+cb.20210328-17-p0.en+FX+000",
                        "domain": ".youtube.com",
                        "path": "/"
                    },
                    {
                        "name": "SOCS",
                        "value": "CAI",
                        "domain": ".youtube.com", 
                        "path": "/"
                    },
                    {
                        "name": "VISITOR_INFO1_LIVE",
                        "value": f"{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=20))}",
                        "domain": ".youtube.com",
                        "path": "/"
                    }
                ])
                
                print(f"  ✓ Enhanced context configured for {country.upper()}")
        except Exception as e:
            print(f"  Error in enhanced context preparation: {e}")
    
    def navigate_with_fallbacks(self, page, country):
        """Navigate with multiple fallback strategies for problematic regions."""
        urls_to_try = []
        
        if country.lower() in self.problematic_regions:
            print(f"  Using fallback navigation strategy for {country.upper()}")
            
            # Multiple URL strategies for India
            urls_to_try = [
                f"https://www.youtube.com/premium/?gl={country.upper()}&hl=en",
                f"https://www.youtube.com/premium/",
                f"https://youtube.com/premium/",
                f"https://www.youtube.com/red/",  # Legacy YouTube Red URL
                f"https://www.youtube.com/?gl={country.upper()}&hl=en"  # Fallback to homepage
            ]
        else:
            urls_to_try = ["https://www.youtube.com/premium/"]
        
        for i, url in enumerate(urls_to_try):
            try:
                print(f"    Attempt {i+1}: {url}")
                
                # For first attempts, use shorter timeout
                timeout = 30000 if i < 2 else 45000
                
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                
                # Wait a bit and check if page loaded
                time.sleep(3)
                
                current_url = page.url
                page_title = page.title()
                
                print(f"    ✓ Loaded: {current_url}")
                print(f"    Title: {page_title}")
                
                # Check if we got somewhere useful
                if any(term in current_url.lower() for term in ['youtube.com', 'youtu.be']):
                    if 'error' not in page_title.lower() and '404' not in page_title:
                        print(f"    ✓ Successfully loaded YouTube page")
                        return True
                
                print(f"    Page loaded but may not be ideal, trying next URL...")
                
            except Exception as e:
                print(f"    ✗ Failed: {e}")
                if i < len(urls_to_try) - 1:
                    print(f"    Trying next URL...")
                    time.sleep(2)
                else:
                    print(f"    All navigation attempts failed")
                    return False
        
        return False
    
    def handle_cookie_consent(self, page):
        """Enhanced cookie consent with India-specific handling."""
        try:
            print("  🎯 Enhanced YouTube cookie consent handling...")
            
            time.sleep(random.uniform(3.0, 5.0))
            
            current_url = page.url
            print(f"    Current URL: {current_url}")
            
            # Check for India-specific patterns
            if any(indicator in current_url.lower() for indicator in ['consent', 'privacy', 'policy']):
                print("    ✓ Detected consent/privacy page")
                
                # India might have different consent patterns
                consent_strategies = [
                    # English (common in India)
                    {
                        "selector": 'button:has-text("Accept all")',
                        "avoid_text": ["sign", "login", "log in"],
                        "language": "English"
                    },
                    {
                        "selector": 'button:has-text("I agree")',
                        "avoid_text": ["sign", "login", "log in"], 
                        "language": "English"
                    },
                    {
                        "selector": 'button:has-text("Continue")',
                        "avoid_text": ["sign", "login", "log in"],
                        "language": "English"
                    },
                    # Hindi (possible in India)
                    {
                        "selector": 'button:has-text("स्वीकार करें")',  # "Accept" in Hindi
                        "avoid_text": ["साइन", "लॉगिन"],
                        "language": "Hindi"
                    },
                    # Add more as needed
                ]
                
                # Try consent strategies
                for strategy in consent_strategies:
                    try:
                        selector = strategy["selector"]
                        language = strategy["language"]
                        
                        print(f"    Trying {language}: {selector}")
                        
                        if page.locator(selector).count() > 0:
                            button = page.locator(selector).first
                            button_text = button.text_content()
                            print(f"      Found button: '{button_text}'")
                            
                            button.click(timeout=10000)
                            time.sleep(4)
                            
                            new_url = page.url
                            print(f"      New URL: {new_url}")
                            
                            if current_url != new_url:
                                print(f"      ✓ Successfully navigated away from consent")
                                return True
                    except Exception as e:
                        print(f"    Strategy {language} failed: {e}")
                        continue
                
                # If clicking failed, try enhanced bypass
                print("  🔧 Trying enhanced bypass for India...")
                try:
                    page.evaluate("""() => {
                        // Set comprehensive cookies
                        document.cookie = "CONSENT=YES+cb.20210328-17-p0.en+FX+000; path=/; domain=.youtube.com; max-age=31536000";
                        document.cookie = "SOCS=CAI; path=/; domain=.youtube.com; max-age=31536000";
                        
                        // Force navigation to premium page
                        setTimeout(() => {
                            window.location.href = 'https://www.youtube.com/premium/';
                        }, 1000);
                    }""")
                    
                    time.sleep(5)
                    
                    final_url = page.url
                    if 'consent' not in final_url.lower():
                        print("    ✓ Enhanced bypass successful")
                        return True
                except Exception as e:
                    print(f"    Enhanced bypass failed: {e}")
            
            else:
                print("  ✓ Not on consent page")
                return True
            
            return False
            
        except Exception as e:
            print(f"  Error in enhanced consent handling: {e}")
            return False
    
    def perform_site_interactions(self, page):
        """Enhanced interactions with better error handling."""
        try:
            print("  Performing enhanced site interactions...")
            
            current_url = page.url
            print(f"  Current URL: {current_url}")
            
            # Check if we're on a valid YouTube page
            if 'youtube.com' not in current_url:
                print("  ⚠️ Not on YouTube domain, attempting redirect")
                try:
                    page.goto("https://www.youtube.com/premium/", timeout=30000)
                    time.sleep(3)
                except Exception as e:
                    print(f"  Redirect failed: {e}")
            
            # Gentle interactions
            try:
                time.sleep(2)
                page.evaluate("window.scrollTo(0, 200)")
                time.sleep(1)
                page.evaluate("window.scrollTo(0, 600)")
                time.sleep(1)
                print("  ✓ Interactions completed")
            except Exception as e:
                print(f"  Error in interactions: {e}")
                
        except Exception as e:
            print(f"  Error in enhanced interactions: {e}")
    
    def extract_pricing_data(self, page):
        """Enhanced extraction with regional debugging."""
        try:
            print("  Extracting YouTube Premium pricing with enhanced debugging...")
            
            time.sleep(2)
            
            current_url = page.url
            page_title = page.title()
            
            print(f"  Current URL: {current_url}")
            print(f"  Page title: {page_title}")
            
            # Enhanced error detection
            error_indicators = ['404', 'error', 'not found', 'unavailable', 'blocked']
            if any(indicator in page_title.lower() for indicator in error_indicators):
                return {
                    "site": "youtube",
                    "url": current_url,
                    "error": f"Error page detected: {page_title}",
                    "page_title": page_title,
                    "debug_info": {
                        "error_indicators_found": [ind for ind in error_indicators if ind in page_title.lower()],
                        "url_analysis": {
                            "on_youtube_domain": 'youtube.com' in current_url,
                            "has_premium_path": '/premium' in current_url,
                            "has_consent_indicators": any(term in current_url for term in ['consent', 'privacy'])
                        }
                    },
                    "plans": []
                }
            
            # Get page content for analysis
            page_content = page.evaluate("() => document.body.textContent || ''")
            
            # Enhanced content analysis
            pricing_data = page.evaluate("""() => {
                const pageText = document.body.textContent || '';
                
                // Check for regional restrictions
                const restrictionIndicators = [
                    'not available', 'unavailable', 'restricted',
                    'coming soon', 'limited', 'blocked'
                ];
                
                const hasRestrictions = restrictionIndicators.some(indicator => 
                    pageText.toLowerCase().includes(indicator)
                );
                
                if (hasRestrictions) {
                    return [{
                        message: 'Regional restrictions detected',
                        page_url: window.location.href,
                        restriction_indicators: restrictionIndicators.filter(ind => 
                            pageText.toLowerCase().includes(ind)
                        ),
                        content_sample: pageText.substring(0, 500)
                    }];
                }
                
                // Look for Premium content
                const premiumIndicators = [
                    'Premium', 'premium', 'PREMIUM',
                    'YouTube Premium', 'YouTube Music'
                ];
                
                const hasPremiumContent = premiumIndicators.some(indicator => 
                    pageText.includes(indicator)
                );
                
                if (!hasPremiumContent) {
                    return [{
                        message: 'No Premium content found',
                        page_url: window.location.href,
                        page_title: document.title,
                        content_sample: pageText.substring(0, 500),
                        premium_search_attempted: true
                    }];
                }
                
                // Enhanced price detection for multiple currencies
                const pricePatterns = [
                    /₹\s*\d+/g,           // Indian Rupees
                    /[£$€¥]\s*\d+/g,      // Other currencies
                    /\d+\s*₹/g,           // Rupees after number
                    /\d+[,.]?\d*\s*INR/g, // INR format
                ];
                
                let allPrices = [];
                pricePatterns.forEach(pattern => {
                    const matches = pageText.match(pattern);
                    if (matches) {
                        allPrices = allPrices.concat(matches);
                    }
                });
                
                if (allPrices.length === 0) {
                    return [{
                        message: 'Premium content found but no prices detected',
                        page_url: window.location.href,
                        has_premium_content: hasPremiumContent,
                        content_sample: pageText.substring(0, 800),
                        searched_currencies: ['₹', '$', '€', '£', 'INR']
                    }];
                }
                
                const uniquePrices = [...new Set(allPrices)];
                
                return uniquePrices.map((price, index) => ({
                    name: `YouTube Premium Plan ${index + 1}`,
                    price: price.trim(),
                    currency_detected: price.includes('₹') ? 'INR' : 'Unknown',
                    found_in_content: true
                }));
            }""")
            
            print(f"\n==== ENHANCED YOUTUBE PRICING EXTRACTION ====")
            print(json.dumps(pricing_data, indent=2))
            print("=============================================\n")
            
            return {
                "site": "youtube",
                "url": current_url,
                "page_title": page_title,
                "extraction_successful": len(pricing_data) > 0 and not any('message' in item for item in pricing_data),
                "debug_info": {
                    "page_content_length": len(page_content),
                    "has_youtube_domain": 'youtube.com' in current_url,
                    "navigation_successful": True
                },
                "plans": pricing_data
            }
            
        except Exception as e:
            print(f"  Error in enhanced extraction: {e}")
            return {
                "site": "youtube",
                "url": page.url if hasattr(page, 'url') else "unknown",
                "error": str(e),
                "plans": []
            }
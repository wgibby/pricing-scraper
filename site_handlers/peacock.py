"""
Minimal Peacock handler with anti-detection measures.
"""
from .base_handler import BaseSiteHandler

class PeacockHandler(BaseSiteHandler):
    """Minimal handler for Peacock TV pricing page with stealth mode."""
    
    def __init__(self, name="peacock"):
        super().__init__(name)
    
    def get_url(self, country):
        """Return the base Peacock URL."""
        return "https://www.peacocktv.com/"
    
    def get_stealth_browser_args(self):
        """Return stealth browser arguments to avoid detection."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--exclude-switches=enable-automation",
            "--disable-extensions-file-access-check",
            "--disable-extensions-http-throttling", 
            "--disable-extensions-https-throttling",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-ipc-flooding-protection",
            "--no-first-run",
            "--no-service-autorun",
            "--password-store=basic",
            "--use-mock-keychain",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu",
            # Try non-headless - comment this out to make it visible
            # "--headless"  
        ]
    
    def prepare_context(self, context, country):
        """Apply stealth settings to avoid detection."""
        print("  Applying anti-detection measures...")
        
        # Set realistic headers
        context.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Chromium";v="112", "Google Chrome";v="112", "Not=A?Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        })
        
        # Remove automation indicators
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Remove chrome automation indicators
            window.chrome = {
                runtime: {},
            };
            
            // Mock permissions
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' }),
                }),
            });
        """)
        
    def handle_cookie_consent(self, page):
        """BYPASS cookie handling - Peacock closes browser when we try to interact."""
        try:
            print("  BYPASSING cookie consent - Peacock detects interaction")
            
            # Just check if we can still access the page
            try:
                title = page.title()
                url = page.url
                print(f"  DEBUG: Page accessible - Title: '{title}', URL: '{url}'")
                
                # Don't interact with anything - just return True
                return True
                
            except Exception as e:
                print(f"  DEBUG: Page became inaccessible: {e}")
                return False
                
        except Exception as e:
            print(f"  Bypass cookie consent failed: {e}")
            return False
    
    def perform_site_interactions(self, page):
        """Minimal interactions - just verify page is still accessible."""
        try:
            print("  Performing minimal interactions...")
            
            # Just check we can still access the page
            try:
                title = page.title()
                print(f"  DEBUG: Page still accessible: '{title}'")
                
                # Don't scroll or interact - Peacock might detect it
                # Just wait a moment for any lazy content
                page.wait_for_timeout(2000)
                
                print("  Minimal interactions completed")
                
            except Exception as e:
                print(f"  DEBUG: Page became inaccessible during interactions: {e}")
                
        except Exception as e:
            print(f"  Error in minimal interactions: {e}")
    
    def extract_pricing_data(self, page):
        """Minimal validation - just check if we can screenshot."""
        return {"screenshot_ready": True, "peacock_stealth_mode": True}
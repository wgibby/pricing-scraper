from abc import ABC, abstractmethod
from playwright.sync_api import Page, BrowserContext

class BaseSiteHandler(ABC):
    """
    Base class for site-specific handlers.
    All site handlers should inherit from this class and implement the required methods.
    """
    
    def __init__(self, name):
        """
        Initialize the site handler.
        
        Args:
            name (str): Name of the site
        """
        self.name = name.lower()
        
    @property
    def site_name(self):
        """Get the site name."""
        return self.name
    
    def get_url(self, country):
        """
        Get the URL for the site for a specific country.
        
        Args:
            country (str): Country code (e.g., 'us', 'uk')
            
        Returns:
            str: URL for the site
        """
        # Default implementation for sites with simple URL structure
        return f"https://www.{self.name}.com/{country}/pricing"
    
    def prepare_context(self, context, country):
        """
        Prepare the browser context before navigating to the site.
        
        Args:
            context (BrowserContext): Playwright browser context
            country (str): Country code
        """
        # Default implementation - can be overridden by subclasses
        pass
    
    def handle_cookie_consent(self, page):
        """
        Handle cookie consent dialogs.
        
        Args:
            page (Page): Playwright page object
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Default implementation - can be overridden by subclasses
        common_selectors = [
            'button:has-text("Accept")', 
            'button:has-text("Accept All")',
            'button:has-text("Accept Cookies")',
            '#onetrust-accept-btn-handler',
            '[data-testid="cookie-notice-accept-button"]',
            'button:has-text("Allow all")',
            'button:has-text("I agree")',
            'button:has-text("Allow cookies")',
            'button.accept-cookies',
            '.cookie-banner button',
            'button.consent-accept',
            '[aria-label="Accept cookies"]'
        ]
        
        for selector in common_selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"  Clicking cookie consent: {selector}")
                    page.click(selector)
                    page.wait_for_timeout(1000)
                    return True
            except Exception as e:
                print(f"  Error with cookie selector {selector}: {str(e)}")
                continue
        
        return False
    
    def perform_site_interactions(self, page):
        """
        Perform site-specific interactions needed to reveal pricing content.
        
        Args:
            page (Page): Playwright page object
        """
        # Default implementation - can be overridden by subclasses
        # Basic scroll interaction to reveal content
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
            page.wait_for_timeout(1000)
        except Exception as e:
            print(f"  Error in basic scroll interaction: {e}")
    
    @abstractmethod
    def extract_pricing_data(self, page):
        """
        Extract pricing data from the page.
        This method must be implemented by all subclasses.
        
        Args:
            page (Page): Playwright page object
            
        Returns:
            dict: Extracted pricing data
        """
        pass
    
    def clean_up(self, page):
        """
        Perform any clean-up actions after scraping.
        
        Args:
            page (Page): Playwright page object
        """
        # Default implementation - can be overridden by subclasses
        pass
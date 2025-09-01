"""
Site handlers package for the pricing scraper.
This package contains handlers for specific sites that implement custom scraping logic.
"""
import importlib
import os
import sys
from typing import Dict, Optional, Type
from .base_handler import BaseSiteHandler

# Dictionary to store site handler classes
_handlers: Dict[str, Type[BaseSiteHandler]] = {}

def register_handler(site_name: str, handler_class: Type[BaseSiteHandler]) -> None:
    """
    Register a site handler.
    
    Args:
        site_name (str): Name of the site
        handler_class (Type[BaseSiteHandler]): Handler class
    """
    _handlers[site_name.lower()] = handler_class

def get_handler(site_name: str) -> Optional[BaseSiteHandler]:
    """
    Get a handler for a specific site.
    
    Args:
        site_name (str): Name of the site
        
    Returns:
        Optional[BaseSiteHandler]: Handler instance or None if not found
    """
    site_name = site_name.lower()
    
    # Handle special name mappings
    name_mappings = {
        'chatgpt_plus': 'chatgpt_plus',
        'chatgpt-plus': 'chatgpt_plus',
        'chatgpt plus': 'chatgpt_plus',
        'openai': 'chatgpt_plus'
    }
    
    # Use mapping if available
    mapped_name = name_mappings.get(site_name, site_name)
    
    # Try to get from registered handlers
    handler_class = _handlers.get(mapped_name)
    
    if handler_class:
        return handler_class(mapped_name)
    
    # If not registered, try to import dynamically
    try:
        # Convert site name to module name
        module_name = f".{mapped_name}"
        module = importlib.import_module(module_name, package=__package__)
        
        # Look for a class named [SiteName]Handler
        class_name = f"{mapped_name.replace('_', '').capitalize()}Handler"
        if hasattr(module, class_name):
            handler_class = getattr(module, class_name)
            # Register for future use
            register_handler(mapped_name, handler_class)
            return handler_class(mapped_name)
    except (ImportError, AttributeError) as e:
        print(f"No handler found for {site_name}: {e}")
    
    return None

# Automatically discover and register all handlers
def _discover_handlers():
    """Discover and register all handlers in the package."""
    # Get the directory of the current package
    package_dir = os.path.dirname(__file__)
    
    # List all Python files in the directory
    for filename in os.listdir(package_dir):
        if filename.endswith('.py') and filename not in ['__init__.py', 'base_handler.py', 'template.py']:
            # Get the module name (filename without .py)
            module_name = filename[:-3]
            
            try:
                # Import the module
                module = importlib.import_module(f".{module_name}", package=__package__)
                
                # Look for handler classes (ending with "Handler")
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, BaseSiteHandler) and 
                        attr != BaseSiteHandler and
                        attr_name.endswith('Handler')):
                        
                        # Register the handler
                        register_handler(module_name, attr)
                        print(f"Registered handler for {module_name}")
                        break
                        
            except (ImportError, AttributeError) as e:
                print(f"Error loading handler from {filename}: {e}")

# Run discovery when the package is imported
_discover_handlers()
# proxy_utils.py - UPDATED FOR DYNAMIC COUNTRY SELECTION
from proxy_config import IPROYAL_USERNAME, IPROYAL_HOST, IPROYAL_PORT, COUNTRY_MAPPING

# Base password (without country suffix) - update this with your actual base password
IPROYAL_BASE_PASSWORD = "UtKjAObD0X8CPr6A"

def get_proxy_url(country_code):
    """
    Generate a proxy URL for a specific country using IProyal with DYNAMIC country selection.
    
    Args:
        country_code: Two-letter country code (e.g., "us", "uk", "de")
        
    Returns:
        Proxy URL string or None if country is not supported
    """
    country_code = country_code.lower()
    
    # Check if we have a mapping for this country
    if country_code not in COUNTRY_MAPPING:
        print(f"Warning: No proxy mapping for country code '{country_code}'")
        return None
    
    # Get the IProyal country code
    iproyal_country = COUNTRY_MAPPING[country_code]
    
    # UPDATED: Build dynamic password with the specific country for this request
    # Format: base_password_country-XX
    dynamic_password = f"{IPROYAL_BASE_PASSWORD}_country-{iproyal_country}"
    
    # Create the proxy URL with dynamic country
    proxy_auth = f"{IPROYAL_USERNAME}:{dynamic_password}"
    proxy_host = f"{IPROYAL_HOST}:{IPROYAL_PORT}"
    
    # Create the proxy URL
    proxy_url = f"http://{proxy_auth}@{proxy_host}"
    
    print(f"  Generated proxy for {country_code.upper()} -> {iproyal_country} proxy")
    
    return proxy_url

def test_proxy_connection(country_code):
    """
    Test if the proxy connection works for a specific country.
    
    Args:
        country_code: Country code to test
        
    Returns:
        bool: True if connection successful
    """
    import requests
    
    proxy_url = get_proxy_url(country_code)
    if not proxy_url:
        return False
        
    try:
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        print(f"  Testing {country_code.upper()} proxy connection...")
        response = requests.get('https://ipinfo.io/json', proxies=proxies, timeout=10)
        
        if response.status_code == 200:
            ip_data = response.json()
            detected_country = ip_data.get('country', 'Unknown')
            expected_country = COUNTRY_MAPPING.get(country_code.lower(), '').upper()
            
            print(f"  ✓ Proxy test successful!")
            print(f"    Expected country: {expected_country}")
            print(f"    Detected country: {detected_country}")
            print(f"    IP: {ip_data.get('ip')}")
            
            # Warn if country doesn't match (but don't fail - some proxies are flexible)
            if detected_country != expected_country:
                print(f"  ⚠️ Warning: Expected {expected_country} but got {detected_country}")
            
            return True
        else:
            print(f"  ✗ Proxy test failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ✗ Proxy test failed: {e}")
        return False
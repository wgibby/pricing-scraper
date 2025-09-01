#!/usr/bin/env python3
"""
Test which countries can actually access Spotify through IProyal proxies.
"""
import requests
import time
from proxy_utils import get_proxy_url

# Test countries in order of priority
test_countries = [
    "us", "uk", "de",  # Known working baseline
    "fr", "jp", "ca", "au", "br", "in", "mx", "it", "es", "nl"  # New targets
]

def test_spotify_access(country):
    """Test if we can access Spotify through a country's proxy."""
    print(f"\n=== Testing Spotify Access via {country.upper()} ===")
    
    try:
        # Get proxy for this country
        proxy_url = get_proxy_url(country)
        if not proxy_url:
            return False, "No proxy URL generated"
        
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Test 1: Verify proxy works at all
        print(f"  Step 1: Testing proxy connection...")
        response = requests.get('https://ipinfo.io/json', proxies=proxies, timeout=10)
        
        if response.status_code != 200:
            return False, f"Proxy failed: HTTP {response.status_code}"
        
        ip_data = response.json()
        detected_country = ip_data.get('country', 'Unknown')
        ip = ip_data.get('ip', 'Unknown')
        
        print(f"    ✅ Proxy works: IP {ip} ({detected_country})")
        
        # Test 2: Try to access Spotify homepage
        print(f"  Step 2: Testing Spotify homepage access...")
        spotify_url = f"https://www.spotify.com/{country.lower()}/"
        
        try:
            response = requests.get(spotify_url, proxies=proxies, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                print(f"    ✅ Spotify homepage accessible")
                
                # Test 3: Try premium page specifically
                print(f"  Step 3: Testing Spotify premium page...")
                premium_url = f"https://www.spotify.com/{country.lower()}/premium/"
                
                try:
                    response = requests.get(premium_url, proxies=proxies, timeout=15, allow_redirects=True)
                    
                    if response.status_code == 200:
                        # Check if we got pricing content
                        content = response.text.lower()
                        has_pricing = any(term in content for term in ['premium', 'individual', 'family', 'price', 'month'])
                        
                        if has_pricing:
                            print(f"    ✅ Premium page accessible with pricing content")
                            return True, f"Full access - IP: {ip} ({detected_country})"
                        else:
                            print(f"    ⚠️ Premium page loads but no pricing content")
                            return True, f"Partial access - IP: {ip} ({detected_country})"
                    else:
                        print(f"    ❌ Premium page failed: HTTP {response.status_code}")
                        return False, f"Premium page blocked: HTTP {response.status_code}"
                        
                except requests.exceptions.RequestException as e:
                    print(f"    ❌ Premium page request failed: {e}")
                    return False, f"Premium page request failed: {str(e)}"
                    
            else:
                print(f"    ❌ Spotify homepage failed: HTTP {response.status_code}")
                return False, f"Homepage blocked: HTTP {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            print(f"    ❌ Spotify request failed: {e}")
            # Check if it's a tunnel/proxy error
            if "tunnel" in str(e).lower() or "proxy" in str(e).lower():
                return False, f"Spotify blocks this proxy IP: {str(e)}"
            else:
                return False, f"Request failed: {str(e)}"
            
    except Exception as e:
        return False, f"Test failed: {str(e)}"

def main():
    """Test Spotify access for all countries."""
    print("🎵 Testing Spotify Access by Country")
    print("=" * 50)
    
    working_countries = []
    blocked_countries = []
    failed_countries = []
    
    for country in test_countries:
        success, message = test_spotify_access(country)
        
        if success:
            working_countries.append((country, message))
            print(f"  ✅ {country.upper()}: {message}")
        else:
            if "blocks this proxy" in message or "tunnel" in message.lower():
                blocked_countries.append((country, message))
            else:
                failed_countries.append((country, message))
            print(f"  ❌ {country.upper()}: {message}")
        
        # Delay between tests to avoid rate limiting
        time.sleep(3)
    
    # Generate report
    print("\n" + "=" * 60)
    print("📊 SPOTIFY ACCESS REPORT")
    print("=" * 60)
    
    print(f"\n✅ SPOTIFY ACCESSIBLE COUNTRIES ({len(working_countries)}):")
    for country, message in working_countries:
        print(f"  - {country.upper()}: {message}")
    
    print(f"\n🚫 SPOTIFY BLOCKS THESE PROXIES ({len(blocked_countries)}):")
    for country, message in blocked_countries:
        print(f"  - {country.upper()}: {message}")
    
    print(f"\n❌ OTHER FAILURES ({len(failed_countries)}):")
    for country, message in failed_countries:
        print(f"  - {country.upper()}: {message}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if working_countries:
        working_codes = [c[0] for c in working_countries]
        print(f"  ✅ Use these countries for Spotify scraping: {working_codes}")
        print(f"  📝 Update config.json Spotify countries to: {working_codes}")
    
    if blocked_countries:
        print(f"  🚫 Spotify actively blocks {len(blocked_countries)} of your proxy countries")
        print(f"     This is common - streaming sites are aggressive about proxy blocking")
    
    if failed_countries:
        print(f"  ❓ {len(failed_countries)} countries had other issues (proxy plan limits, etc.)")
    
    # Suggested config update
    if working_countries:
        working_codes = [c[0] for c in working_countries]
        print(f"\n📝 SUGGESTED CONFIG UPDATE:")
        print(f'  For Spotify: "countries": {working_codes}')

if __name__ == "__main__":
    main()
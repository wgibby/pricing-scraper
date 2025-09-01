#!/usr/bin/env python3
"""
Enhanced proxy utilities with geo-validation for YouTube and other geo-sensitive sites.
"""
import requests
import time
import random
from proxy_utils import get_proxy_url

def test_proxy_geo_accuracy(proxy_url, target_country, max_retries=3):
    """
    Test if a proxy accurately represents the target country.
    
    Args:
        proxy_url (str): Proxy URL
        target_country (str): Expected country code (e.g., 'uk', 'de')
        max_retries (int): Number of retries for geo-validation
        
    Returns:
        dict: Validation results with geo-accuracy info
    """
    
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    results = {
        'proxy_works': False,
        'geo_accurate': False,
        'detected_country': None,
        'detected_ip': None,
        'youtube_accessible': False,
        'retry_count': 0,
        'errors': []
    }
    
    for attempt in range(max_retries):
        results['retry_count'] = attempt + 1
        
        try:
            print(f"  Testing proxy geo-accuracy (attempt {attempt + 1}/{max_retries})...")
            
            # Test 1: Basic proxy functionality
            response = requests.get('https://ipinfo.io/json', proxies=proxies, timeout=20)
            
            if response.status_code == 200:
                ip_data = response.json()
                results['proxy_works'] = True
                results['detected_ip'] = ip_data.get('ip')
                results['detected_country'] = ip_data.get('country', '').lower()
                
                print(f"    IP: {results['detected_ip']}")
                print(f"    Detected country: {results['detected_country']}")
                print(f"    Target country: {target_country.lower()}")
                
                # Check geo-accuracy
                if results['detected_country'] == target_country.lower():
                    results['geo_accurate'] = True
                    print(f"    ✓ Geo-location accurate!")
                elif target_country.lower() == 'uk' and results['detected_country'] == 'gb':
                    results['geo_accurate'] = True
                    print(f"    ✓ Geo-location accurate (GB for UK)!")
                else:
                    print(f"    ✗ Geo-location mismatch!")
                    
                    # For some providers, try a different endpoint
                    try:
                        alt_response = requests.get('http://ip-api.com/json/', proxies=proxies, timeout=15)
                        if alt_response.status_code == 200:
                            alt_data = alt_response.json()
                            alt_country = alt_data.get('countryCode', '').lower()
                            print(f"    Alternative geo-check: {alt_country}")
                            
                            if alt_country == target_country.lower() or (target_country.lower() == 'uk' and alt_country == 'gb'):
                                results['geo_accurate'] = True
                                results['detected_country'] = alt_country
                                print(f"    ✓ Alternative geo-check passed!")
                    except:
                        pass
                
                # Test 2: YouTube accessibility (critical for YouTube scraping)
                try:
                    print(f"    Testing YouTube accessibility...")
                    yt_response = requests.get('https://www.youtube.com/', 
                                             proxies=proxies, 
                                             timeout=15,
                                             headers={
                                                 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
                                             })
                    
                    if yt_response.status_code == 200:
                        results['youtube_accessible'] = True
                        print(f"    ✓ YouTube accessible")
                        
                        # Check for unexpected redirects in YouTube response
                        if any(term in yt_response.text for term in ['Прийняти', 'Україна', 'ukraine']):
                            print(f"    ⚠️ YouTube showing Ukrainian content (potential geo-issue)")
                            results['youtube_accessible'] = False
                    else:
                        print(f"    ✗ YouTube not accessible (status: {yt_response.status_code})")
                        
                except Exception as yt_e:
                    print(f"    ✗ YouTube accessibility test failed: {yt_e}")
                    results['errors'].append(f"YouTube test: {yt_e}")
                
                # If geo is accurate and YouTube works, we're good
                if results['geo_accurate'] and results['youtube_accessible']:
                    break
                elif results['geo_accurate']:
                    print(f"    Geo accurate but YouTube issues - retrying...")
                    time.sleep(random.uniform(3, 6))
                else:
                    print(f"    Geo inaccurate - retrying...")
                    time.sleep(random.uniform(2, 4))
            else:
                print(f"    ✗ Proxy test failed (status: {response.status_code})")
                results['errors'].append(f"Proxy test failed: {response.status_code}")
                
        except Exception as e:
            print(f"    ✗ Proxy test error: {e}")
            results['errors'].append(f"Attempt {attempt + 1}: {e}")
            time.sleep(random.uniform(2, 5))
    
    return results

def get_validated_proxy_for_country(country, max_proxy_attempts=3):
    """
    Get a validated proxy for a specific country with geo-accuracy verification.
    
    Args:
        country (str): Target country code
        max_proxy_attempts (int): Maximum number of different proxies to try
        
    Returns:
        tuple: (proxy_url, validation_results) or (None, None) if no valid proxy found
    """
    
    print(f"Getting validated proxy for {country.upper()}...")
    
    for proxy_attempt in range(max_proxy_attempts):
        print(f"\nProxy attempt {proxy_attempt + 1}/{max_proxy_attempts}")
        
        # Get a proxy URL
        proxy_url = get_proxy_url(country)
        
        if not proxy_url:
            print(f"  No proxy URL available for {country}")
            continue
        
        # Test the proxy thoroughly
        validation_results = test_proxy_geo_accuracy(proxy_url, country)
        
        # Check if proxy meets our requirements
        if validation_results['proxy_works'] and validation_results['geo_accurate']:
            if validation_results['youtube_accessible']:
                print(f"  ✓ Found fully validated proxy for {country}")
                return proxy_url, validation_results
            else:
                print(f"  ⚠️ Proxy geo-accurate but YouTube access issues")
                # For non-YouTube sites, this might still be okay
                return proxy_url, validation_results
        else:
            print(f"  ✗ Proxy validation failed:")
            print(f"    - Works: {validation_results['proxy_works']}")
            print(f"    - Geo-accurate: {validation_results['geo_accurate']}")
            print(f"    - YouTube accessible: {validation_results['youtube_accessible']}")
            
            if validation_results['errors']:
                print(f"    - Errors: {validation_results['errors']}")
        
        # Wait before trying next proxy
        if proxy_attempt < max_proxy_attempts - 1:
            print(f"  Waiting before trying next proxy...")
            time.sleep(random.uniform(5, 10))
    
    print(f"  ✗ Could not find valid proxy for {country} after {max_proxy_attempts} attempts")
    return None, None

def handle_youtube_geo_issues(page, target_country):
    """
    Handle YouTube-specific geo-detection issues.
    
    Args:
        page: Playwright page object
        target_country (str): Expected country code
        
    Returns:
        bool: True if geo-issues were resolved
    """
    
    try:
        current_url = page.url
        page_content = page.evaluate("() => document.body.textContent || ''")
        
        print(f"  Checking for geo-issues on: {current_url}")
        
        # Detect unexpected geo-redirects
        unexpected_indicators = [
            ('ukraine', 'ukrainian', ['Прийняти', 'Україна', '/intl/uk/']),
            ('russia', 'russian', ['Россия', 'Принять', '/intl/ru/']),
            ('poland', 'polish', ['Akceptuj', 'Polska', '/intl/pl/']),
            # Add more as needed
        ]
        
        detected_issue = None
        for country_name, language, indicators in unexpected_indicators:
            if any(indicator in current_url.lower() or indicator in page_content for indicator in indicators):
                detected_issue = country_name
                break
        
        if detected_issue:
            print(f"  ⚠️ Detected unexpected redirect to {detected_issue}")
            print(f"  Attempting to force correct region...")
            
            # Strategy 1: Try direct navigation to correct locale
            target_urls = [
                f"https://www.youtube.com/intl/en_{target_country}/premium/",
                f"https://www.youtube.com/intl/{target_country}/premium/",
                f"https://www.youtube.com/premium/?gl={target_country.upper()}",
                "https://www.youtube.com/premium/"
            ]
            
            for url in target_urls:
                try:
                    print(f"    Trying: {url}")
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(3000)
                    
                    # Check if we successfully changed region
                    new_content = page.evaluate("() => document.body.textContent || ''")
                    new_url = page.url
                    
                    # Check if the unwanted content is gone
                    issue_resolved = not any(indicator in new_url.lower() or indicator in new_content 
                                           for _, _, indicators in unexpected_indicators 
                                           for indicator in indicators)
                    
                    if issue_resolved:
                        print(f"    ✓ Successfully redirected to correct region")
                        return True
                except Exception as e:
                    print(f"    Failed: {e}")
                    continue
            
            # Strategy 2: Try to manipulate page settings
            try:
                print(f"    Trying to set language/region via page controls...")
                
                # Look for settings/language buttons
                settings_selectors = [
                    'button[aria-label*="Settings"]',
                    'button[aria-label*="Language"]',
                    '.ytd-topbar-menu-button-renderer',
                    '#country-picker',
                    '[aria-label*="Region"]'
                ]
                
                for selector in settings_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            page.click(selector)
                            page.wait_for_timeout(2000)
                            
                            # Look for language options
                            english_selectors = [
                                'a:has-text("English")',
                                f'a:has-text("{target_country.upper()}")',
                                '[data-language="en"]',
                                '[lang="en"]'
                            ]
                            
                            for lang_selector in english_selectors:
                                try:
                                    if page.locator(lang_selector).count() > 0:
                                        page.click(lang_selector)
                                        page.wait_for_timeout(3000)
                                        
                                        # Check if change was successful
                                        final_content = page.evaluate("() => document.body.textContent || ''")
                                        if not any(indicator in final_content for _, _, indicators in unexpected_indicators for indicator in indicators):
                                            print(f"    ✓ Successfully changed language/region")
                                            return True
                                except:
                                    continue
                    except:
                        continue
            except Exception as e:
                print(f"    Language/region change failed: {e}")
            
            print(f"    ✗ Could not resolve geo-redirect issue")
            return False
        
        else:
            print(f"  ✓ No geo-issues detected")
            return True
    
    except Exception as e:
        print(f"  Error handling geo-issues: {e}")
        return False

def get_country_specific_headers(country):
    """
    Get country-specific headers for enhanced geo-targeting.
    
    Args:
        country (str): Country code
        
    Returns:
        dict: Headers dictionary
    """
    
    headers_map = {
        "us": {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "uk": {
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "de": {
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "fr": {
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "it": {
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "es": {
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "br": {
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "mx": {
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "nl": {
            "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "jp": {
            "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "ca": {
            "Accept-Language": "en-CA,en;q=0.9,fr;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "au": {
            "Accept-Language": "en-AU,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        },
        "in": {
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        }
    }
    
    return headers_map.get(country.lower(), headers_map["us"])
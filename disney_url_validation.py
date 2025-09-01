#!/usr/bin/env python3
"""
Disney+ URL Validation Script
Tests which Disney+ URLs work in different markets
"""
import requests
import time
from proxy_utils import get_proxy_url

def test_disney_urls_by_market():
    """Test Disney+ URLs across different markets."""
    
    test_countries = ["us", "uk", "ca", "au", "de", "fr", "it", "es", "nl", "br", "mx", "jp", "in"]
    
    test_urls = {
        "help_page": "https://help.disneyplus.com/article/disneyplus-price",
        "main_signup": "https://www.disneyplus.com/sign-up",
        "localized_signup": {
            "us": "https://www.disneyplus.com/sign-up",
            "uk": "https://www.disneyplus.com/en-gb/sign-up",
            "ca": "https://www.disneyplus.com/en-ca/sign-up", 
            "au": "https://www.disneyplus.com/en-au/sign-up",
            "de": "https://www.disneyplus.com/de-de/sign-up",
            "fr": "https://www.disneyplus.com/fr-fr/sign-up",
            "it": "https://www.disneyplus.com/it-it/sign-up",
            "es": "https://www.disneyplus.com/es-es/sign-up",
            "nl": "https://www.disneyplus.com/nl-nl/sign-up",
            "br": "https://www.disneyplus.com/pt-br/sign-up",
            "mx": "https://www.disneyplus.com/es-mx/sign-up",
            "jp": "https://www.disneyplus.com/ja-jp/sign-up",
            "in": "https://www.disneyplus.com/en-in/sign-up"
        }
    }
    
    results = {}
    
    print("🏰 DISNEY+ URL VALIDATION ACROSS MARKETS")
    print("=" * 60)
    
    for country in test_countries:
        print(f"\n🌍 Testing {country.upper()}...")
        results[country] = {}
        
        # Get proxy for this country (skip US)
        if country.lower() != "us":
            proxy_url = get_proxy_url(country)
            if proxy_url:
                proxies = {'http': proxy_url, 'https': proxy_url}
                print(f"  📡 Using proxy for {country}")
            else:
                print(f"  ⚠️  No proxy available for {country} - using direct connection")
                proxies = None
        else:
            proxies = None
            print(f"  🇺🇸 Using direct connection for US")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Test 1: Help page (our target)
        try:
            print(f"    📋 Testing help page...")
            response = requests.get(test_urls["help_page"], 
                                  proxies=proxies, 
                                  headers=headers, 
                                  timeout=20,
                                  allow_redirects=True)
            
            results[country]["help_page"] = {
                "status_code": response.status_code,
                "final_url": response.url,
                "accessible": response.status_code == 200,
                "has_pricing": "pricing" in response.text.lower() or "price" in response.text.lower(),
                "has_disney": "disney" in response.text.lower(),
                "content_length": len(response.text)
            }
            
            if response.status_code == 200:
                print(f"      ✅ Help page accessible (content: {len(response.text)} chars)")
                if results[country]["help_page"]["has_pricing"]:
                    print(f"      💰 Contains pricing content")
                else:
                    print(f"      ⚠️  No obvious pricing content")
            else:
                print(f"      ❌ Help page failed: {response.status_code}")
                
        except Exception as e:
            print(f"      💥 Help page error: {e}")
            results[country]["help_page"] = {"error": str(e), "accessible": False}
        
        # Test 2: Main signup page
        try:
            print(f"    📝 Testing main signup...")
            response = requests.get(test_urls["main_signup"],
                                  proxies=proxies,
                                  headers=headers,
                                  timeout=20,
                                  allow_redirects=True)
            
            results[country]["main_signup"] = {
                "status_code": response.status_code,
                "final_url": response.url,
                "accessible": response.status_code == 200,
                "redirected": response.url != test_urls["main_signup"],
                "content_length": len(response.text)
            }
            
            if response.status_code == 200:
                print(f"      ✅ Main signup accessible")
                if results[country]["main_signup"]["redirected"]:
                    print(f"      🔄 Redirected to: {response.url}")
            else:
                print(f"      ❌ Main signup failed: {response.status_code}")
                
        except Exception as e:
            print(f"      💥 Main signup error: {e}")
            results[country]["main_signup"] = {"error": str(e), "accessible": False}
        
        # Test 3: Localized signup page
        if country in test_urls["localized_signup"]:
            try:
                localized_url = test_urls["localized_signup"][country]
                print(f"    🌐 Testing localized signup...")
                response = requests.get(localized_url,
                                      proxies=proxies,
                                      headers=headers,
                                      timeout=20,
                                      allow_redirects=True)
                
                results[country]["localized_signup"] = {
                    "status_code": response.status_code,
                    "final_url": response.url,
                    "accessible": response.status_code == 200,
                    "content_length": len(response.text)
                }
                
                if response.status_code == 200:
                    print(f"      ✅ Localized signup accessible")
                else:
                    print(f"      ❌ Localized signup failed: {response.status_code}")
                    
            except Exception as e:
                print(f"      💥 Localized signup error: {e}")
                results[country]["localized_signup"] = {"error": str(e), "accessible": False}
        
        # Small delay between countries
        if country != test_countries[-1]:
            time.sleep(2)
    
    # Summary report
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY REPORT")
    print(f"{'='*60}")
    
    help_page_success = sum(1 for country, data in results.items() 
                           if data.get("help_page", {}).get("accessible", False))
    
    main_signup_success = sum(1 for country, data in results.items() 
                             if data.get("main_signup", {}).get("accessible", False))
    
    localized_success = sum(1 for country, data in results.items() 
                           if data.get("localized_signup", {}).get("accessible", False))
    
    print(f"📋 Help page success rate: {help_page_success}/{len(test_countries)} ({help_page_success/len(test_countries)*100:.1f}%)")
    print(f"📝 Main signup success rate: {main_signup_success}/{len(test_countries)} ({main_signup_success/len(test_countries)*100:.1f}%)")
    print(f"🌐 Localized signup success rate: {localized_success}/{len(test_countries)} ({localized_success/len(test_countries)*100:.1f}%)")
    
    # Best strategy recommendation
    print(f"\n🎯 RECOMMENDED STRATEGY:")
    if help_page_success >= len(test_countries) * 0.8:
        print(f"✅ USE HELP PAGE - High success rate ({help_page_success}/{len(test_countries)})")
        print(f"   URL: https://help.disneyplus.com/article/disneyplus-price")
    elif localized_success >= len(test_countries) * 0.8:
        print(f"✅ USE LOCALIZED SIGNUPS - High success rate ({localized_success}/{len(test_countries)})")
        print(f"   Strategy: Use country-specific signup URLs")
    else:
        print(f"⚠️  MIXED APPROACH NEEDED")
        print(f"   Use help page where available, fallback to localized signups")
    
    # Problematic countries
    problem_countries = []
    for country, data in results.items():
        help_ok = data.get("help_page", {}).get("accessible", False)
        main_ok = data.get("main_signup", {}).get("accessible", False)
        local_ok = data.get("localized_signup", {}).get("accessible", False)
        
        if not (help_ok or main_ok or local_ok):
            problem_countries.append(country)
    
    if problem_countries:
        print(f"\n❌ PROBLEMATIC MARKETS: {', '.join(problem_countries)}")
        print(f"   These markets may need special handling or different URLs")
    
    # Detailed results for key countries
    key_countries = ["us", "uk", "de", "jp"]
    print(f"\n📋 DETAILED RESULTS FOR KEY MARKETS:")
    print("-" * 50)
    
    for country in key_countries:
        if country in results:
            data = results[country]
            print(f"\n{country.upper()}:")
            
            help_data = data.get("help_page", {})
            if help_data.get("accessible"):
                pricing_indicator = "💰" if help_data.get("has_pricing") else "📄"
                print(f"  Help page: ✅ {pricing_indicator} ({help_data.get('content_length', 0)} chars)")
            else:
                error = help_data.get("error", "Failed")
                print(f"  Help page: ❌ {error}")
            
            main_data = data.get("main_signup", {})
            if main_data.get("accessible"):
                redirect_indicator = "🔄" if main_data.get("redirected") else "➡️"
                print(f"  Main signup: ✅ {redirect_indicator}")
            else:
                print(f"  Main signup: ❌")
            
            local_data = data.get("localized_signup", {})
            if local_data.get("accessible"):
                print(f"  Localized: ✅")
            else:
                print(f"  Localized: ❌")
    
    return results

if __name__ == "__main__":
    results = test_disney_urls_by_market()
    
    # Save results to file
    import json
    with open(f"disney_url_test_results_{int(time.time())}.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to disney_url_test_results_*.json")
#!/usr/bin/env python3
"""
Quick test for India Figma pricing
"""
import requests

def test_india_figma():
    """Test Figma India pricing detection"""
    
    url = "https://www.figma.com/pricing/"
    
    # Headers that might trigger INR pricing
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'en-IN,hi-IN;q=0.9,en;q=0.8',
        'CF-IPCountry': 'IN',  # Cloudflare country header
        'X-Forwarded-For': '103.21.244.0',  # Indian IP range
    }
    
    print("Testing Figma India pricing...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")
        print(f"Content length: {len(response.text):,}")
        
        content = response.text.lower()
        
        # Check for currency indicators
        indicators = {
            'has_inr_symbol': '₹' in response.text,
            'has_inr_text': 'inr' in content,
            'has_rupee': 'rupee' in content,
            'has_usd': '$' in response.text,
            'has_professional': 'professional' in content,
            'has_pricing': 'pricing' in content,
            'has_1000': '1000' in content or '1,000' in content,  # ~1k INR mentioned in search
        }
        
        print(f"Currency indicators: {indicators}")
        
        # Look for specific price patterns
        import re
        
        inr_prices = re.findall(r'₹\s*[\d,]+', response.text)
        usd_prices = re.findall(r'\$\s*\d+', response.text)
        
        print(f"Found INR prices: {inr_prices}")
        print(f"Found USD prices: {usd_prices}")
        
        # Save snippet for manual inspection
        with open('india_figma_test.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("Full HTML saved to india_figma_test.html")
        
        return {
            'status_code': response.status_code,
            'has_inr': indicators['has_inr_symbol'] or indicators['has_inr_text'],
            'has_pricing_content': indicators['has_professional'] and indicators['has_pricing'],
            'inr_prices': inr_prices,
            'usd_prices': usd_prices
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    result = test_india_figma()
    print(f"\nResult: {result}")
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a concurrent pricing scraper that collects subscription pricing data from various websites across different countries using Playwright automation. The scraper supports both sequential and concurrent processing modes.

## Dependencies

Install dependencies with:
```bash
pip install -r requirements.txt
playwright install
```

Key dependencies:
- `playwright==1.40.0` - Browser automation
- `requests==2.31.0` - HTTP requests and proxy validation
- `beautifulsoup4==4.12.2` - HTML parsing
- `python-dotenv==1.0.0` - Environment variables
- `Pillow==10.1.0` - Image processing

## Running the Scraper

Main entry points:
- `concurrent_modified_scraper.py` - Latest version with concurrent processing
- `modified_scraper.py` - Sequential version

Basic usage:
```bash
python concurrent_modified_scraper.py --websites netflix spotify --countries us uk de
python concurrent_modified_scraper.py --concurrent --max-workers 4
```

Test scripts:
- `spotify_test.py` - Spotify-specific testing
- `disney_test_script.py` - Disney+ testing
- Individual debug scripts for specific sites

## Architecture

### Core Components

1. **Site Handlers** (`site_handlers/`):
   - `base_handler.py` - Abstract base class for all site handlers
   - Individual handlers for each website (netflix.py, spotify.py, etc.)
   - Each handler implements site-specific scraping logic

2. **Proxy Management**:
   - `proxy_utils.py` - Basic proxy functionality
   - `enhanced_proxy_utils.py` - Enhanced validation for geo-sensitive sites
   - Automatic proxy selection based on target country

3. **Configuration**:
   - `config.json` - Website definitions, countries, and priority tiers
   - Supports dynamic URL templating with `{country}` placeholders

### Site Handler Pattern

All site handlers inherit from `BaseSiteHandler` and must implement:
- `scrape()` method for extracting pricing data
- Country-specific URL handling
- Currency detection and normalization
- Anti-detection mechanisms (timeouts, random delays)

### Data Flow

1. Configuration loaded from `config.json`
2. Proxy selected and validated for target country
3. Site handler instantiated for specific website
4. Playwright browser launched with proxy configuration
5. Pricing data extracted and saved as JSON
6. Screenshots captured for verification

## Output Structure

- `screenshots/` - Browser screenshots organized by date
- Results saved as JSON files with timestamp and country code
- Format: `{website}_{country}_{timestamp}_result.json`

## Development Notes

- The scraper includes anti-detection measures (random delays, user agents)
- Geo-sensitive sites (Netflix, YouTube, Disney+) use enhanced proxy validation
- Site handlers support multiple languages and regional variations
- Concurrent mode uses ThreadPoolExecutor for parallel processing
- Thread-safe logging implemented for concurrent operations

## Recent Work (Last Updated: 2025-10-01)

### Canva Handler - COMPLETED ✅
**Date**: October 1, 2025
**Status**: Fully functional and tested

**Implementation Details**:
- Created `site_handlers/canva.py` with full pricing extraction
- Uses **Firefox** instead of Chromium (Canva has strong bot detection that blocks/crashes Chromium)
- Added to `geo_ip_sites` list in `concurrent_modified_scraper.py` (line 287)
- Added to Firefox browser list (line 328)
- Successfully extracts all 4 plans: Free ($0), Pro ($15/mo), Teams ($10/mo), Enterprise (contact)
- Monthly/yearly toggle support with multiple fallback strategies

**Critical Technical Notes**:
- **DO NOT use `add_init_script`** in Canva's `prepare_context` - it causes Chromium crashes on macOS
- **DO NOT use extensive browser args** - keep minimal (`--disable-blink-features`, `--disable-dev-shm-usage`, `--no-sandbox`)
- Firefox is essential - Chromium gets blocked by Canva's protection (likely Cloudflare)
- Test script available: `canva_test_script.py`

**Extraction Strategy**:
- Searches for exact plan names ("Canva Free", "Canva Pro", etc.)
- Traverses DOM upward to find pricing card container
- Handles "US$" format and "Contact for pricing" for Enterprise
- Features extraction implemented (though currently returns empty - may need refinement)

### Next Steps (TODO)
1. **Feature extraction refinement** - Canva features array is empty, may need to adjust selector or container traversal
2. **Test with other countries** - Verify geo-targeting works correctly (Canva uses same URL globally)
3. **Add more sites** - Continue expanding coverage
4. **Optimize concurrent scraping** - Test with multiple sites/countries in parallel

### Handler Best Practices (Learned from Canva)
1. **For high-detection sites**: Use Firefox over Chromium
2. **Avoid init scripts on macOS**: They can cause crashes with certain browser configurations
3. **Keep browser args minimal**: Only add what's necessary for stealth
4. **Test in isolation first**: Use dedicated test scripts before full integration
5. **DOM traversal approach**: When selectors fail, search for text and traverse up to find containers
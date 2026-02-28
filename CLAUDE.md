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

## V2 Pipeline (Last Updated: 2026-02-27)

### Status: Phase 1 COMPLETE ✅ — Phase 2 COMPLETE ✅

The `v2/` directory contains the new LLM-powered pricing scraper pipeline. It replaces
per-site handler code with a config-driven orchestrator + generic extraction cascade.
See `REFACTOR_PROPOSAL.md` for full architecture and session notes.

### V2 Components (`v2/`)

| File | Purpose |
|------|---------|
| `company_registry.json` | Static config for all 16 sites — URLs, browser, geo strategy, interactions |
| `registry.py` | Load registry, resolve URLs per (site, country), proxy selection |
| `browser.py` | Browser launch, stealth profiles, cookie consent, page stabilization |
| `interactions.py` | Site-specific overrides: Netflix multi-step, Adobe geo-popup |
| `orchestrator.py` | Main entry point — sequential + concurrent scrape pipeline |
| `models.py` | Pydantic data models (PricingPlan, PricingExtraction) + Claude tool schema |
| `html_cleaner.py` | 5-pass HTML cleaning — 95-98% size reduction, target <20K chars |
| `llm_client.py` | Claude tool_use wrapper (Sonnet) — text + vision, .env API key loading |
| `extractor.py` | Tiered cascade: JSON-LD (stub) → Cleaned HTML → OCR (stub) → Vision |
| `capture_html.py` | (Phase 1) Browser/URL configs for offline testing |
| `test_extraction.py` | (Phase 1) Comparison harness — old handlers vs v2 |

### Running V2 (Phase 2 Orchestrator)

```bash
# Scrape specific sites for US
python -m v2.orchestrator --sites spotify netflix --countries us

# Scrape all 16 sites for US
python -m v2.orchestrator --all --countries us

# Multi-country
python -m v2.orchestrator --all --countries us uk de

# All sites, all countries
python -m v2.orchestrator --all --all-countries

# Concurrent mode (3 workers)
python -m v2.orchestrator --all --countries us --concurrent --max-workers 3

# Registry info
python -m v2.registry                              # list all sites
python -m v2.registry --site netflix --country de   # single site detail

# Browser test (no extraction)
python -m v2.browser --site spotify --country us
```

### Phase 2 Validation Results (16/16 US)
- 16/16 sites succeeded (100% pass rate)
- 13 sites resolve at Tier 2 (HTML) — 81%
- 3 sites resolve at Tier 4 (Vision) — 19% (Adobe, Figma, Netflix)
- 5 high confidence, 10 medium, 1 low (Netflix)
- Concurrent mode validated (ThreadPoolExecutor, per-thread browsers)
- Results saved to `results/v2/{site}_{country}_{timestamp}.json`
- Screenshots saved to `screenshots/v2/{site}_{country}_{timestamp}.png`

### Browser Requirements
- **Firefox required (8):** Adobe, Box, Canva, ChatGPT+, Disney+, Netflix, Peacock, YouTube
- **Chromium works (8):** Audible, Dropbox, Evernote, Figma, Grammarly, Notion, Spotify, Zwift

### Critical Technical Notes
- **DO NOT use `add_init_script`** for Canva — crashes Chromium on macOS (registry: `skip_init_script: true`)
- **Anthropic API max image dimension is 8000px** — `llm_client.py` auto-resizes larger screenshots
- **HTML cleaner target is 20K chars** — reduced from 32K after validation
- **max_tokens is 4096** — complex pages with many plans need the extra output space
- **`.env` file** in project root holds `ANTHROPIC_API_KEY` (loaded via stdlib, not python-dotenv)
- **Box runs non-headless** (`headless: false` in registry) — Cloudflare bypass
- Old handlers are degraded on 13/16 sites — V2 replaces all extraction

### Known Issues
- **Concurrent mode transient failures:** Running 3+ browsers simultaneously causes occasional
  `Target page, context or browser has been closed` or navigation timeout errors due to macOS
  resource contention. All failures are transient — the same (site, country) pairs succeed in
  sequential mode. Multi-country concurrent run scored 43/48 (90%). Potential mitigations:
  automatic retry with backoff, lower default `--max-workers`, or sequential fallback on failure.

### Next Steps (Phase 2.5+)
1. **Concurrent robustness** — retry logic / sequential fallback for transient browser crashes
2. Multi-country validation with proxies (UK, DE) — initial run: 43/48 pass (90%)
3. Archive old handlers to `archive/`
4. Phase 3: SQLite storage, historical tracking
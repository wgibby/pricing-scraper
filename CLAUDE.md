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

## V2 Extraction Pipeline (Last Updated: 2026-02-27)

### Status: Phase 1 COMPLETE ✅ — Phase 2 not started

The `v2/` directory contains a new LLM-powered extraction system that replaces per-site
handler extraction with a generic tiered cascade. See `REFACTOR_PROPOSAL.md` for full
architecture and session notes.

### V2 Components (`v2/`)

| File | Purpose |
|------|---------|
| `models.py` | Pydantic data models (PricingPlan, PricingExtraction) + Claude tool schema |
| `html_cleaner.py` | 5-pass HTML cleaning — 95-98% size reduction, target <20K chars |
| `llm_client.py` | Claude tool_use wrapper (Sonnet) — text + vision, .env API key loading |
| `extractor.py` | Tiered cascade: JSON-LD (stub) → Cleaned HTML → OCR (stub) → Vision |
| `capture_html.py` | Browser/URL configs for all 16 sites, stealth setup, cookie dismissal |
| `test_extraction.py` | Comparison harness — old handlers vs v2, with `--v2-only` mode |

### Running V2

```bash
# Test single site extraction (HTML input)
./venv/bin/python -m v2.llm_client screenshots/html/grammarly_us.html Grammarly us

# Test extraction cascade (HTML + Vision fallback)
./venv/bin/python -m v2.extractor screenshots/html/grammarly_us.html Grammarly us

# Run comparison harness (old handlers vs v2)
./venv/bin/python -m v2.test_extraction --sites grammarly spotify --country us

# Run v2 only (bypasses old handlers — use for sites where old handlers crash)
./venv/bin/python -m v2.test_extraction --v2-only --sites chatgpt_plus notion --country us

# Run all 16 sites
./venv/bin/python -m v2.test_extraction --all --country us
```

### Phase 1 Results (16/16 sites passing)
- 13 sites resolve at Tier 2 (HTML) — 81%
- 3 sites resolve at Tier 4 (Vision) — 19%
- 5 high confidence, 11 medium, 0 low
- API cost: ~$0.03/page (Sonnet)

### Browser Requirements
- **Firefox required (8):** Adobe, Box, Canva, ChatGPT+, Disney+, Netflix, Peacock, YouTube
- **Chromium works (8):** Audible, Dropbox, Evernote, Figma, Grammarly, Notion, Spotify, Zwift

### Critical Technical Notes
- **DO NOT use `add_init_script`** in Canva's `prepare_context` — crashes Chromium on macOS
- **Anthropic API max image dimension is 8000px** — `llm_client.py` auto-resizes larger screenshots
- **HTML cleaner target is 20K chars** — reduced from 32K after validation (larger inputs cause incomplete LLM responses)
- **max_tokens is 4096** — complex pages with many plans need the extra output space
- **`.env` file** in project root holds `ANTHROPIC_API_KEY` (loaded via stdlib, not python-dotenv)
- Old handlers are degraded on 13/16 sites — crashes, null prices, regex spam. V2 replaces all extraction.

### Next Steps (Phase 2)
1. **Company registry** (`v2/company_registry.json`) — config-driven site definitions
2. **Orchestrator** (`v2/orchestrator.py`) — new entry point replacing `concurrent_modified_scraper.py`
3. **Generic cookie consent + stealth profiles** — consolidate from old handlers
4. **Thin interaction overrides** — only Netflix (click "Next") and Adobe (dismiss geo-popup)
5. After Phase 2 validated: archive old handlers to `archive/`
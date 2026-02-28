# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM-powered pricing scraper that collects subscription pricing data from 16 websites
across multiple countries. Uses Playwright for browser automation and Claude (Sonnet) for
intelligent extraction via a tiered cascade (HTML → Vision).

The old per-site handler scraper has been archived to `archive/`. The `v2/` pipeline is
the only active system. See `REFACTOR_PROPOSAL.md` for full architecture and session notes.

## Dependencies

Install dependencies with:
```bash
pip install -r requirements.txt
playwright install
```

Key dependencies:
- `playwright==1.40.0` - Browser automation
- `anthropic` - Claude API for LLM extraction
- `requests==2.31.0` - HTTP requests and proxy validation
- `beautifulsoup4==4.12.2` - HTML parsing/cleaning
- `pydantic` - Data models
- `Pillow==10.1.0` - Image processing (screenshot resizing)

## Running the Scraper

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

## Architecture

### Data Flow

1. Site config loaded from `v2/company_registry.json`
2. Proxy selected and validated for target country (via `enhanced_proxy_utils.py`)
3. Playwright browser launched with stealth profile + cookie consent handling
4. Site-specific interactions executed (Netflix signup flow, Adobe geo-popup, etc.)
5. Tiered extraction cascade: Cleaned HTML (Tier 2) → Vision/OCR (Tier 4)
6. Structured pricing data returned as Pydantic models, saved as JSON
7. Screenshots captured for verification

### Proxy Management

- `proxy_utils.py` - Basic proxy functionality
- `enhanced_proxy_utils.py` - Enhanced validation for geo-sensitive sites
- `proxy_config.py` - Proxy configuration
- Automatic proxy selection based on target country

## Output Structure

- `results/v2/{site}_{country}_{timestamp}.json` - Structured pricing data
- `screenshots/v2/{site}_{country}_{timestamp}.png` - Browser screenshots

## V2 Pipeline (Last Updated: 2026-02-28)

### Status: Phase 1 COMPLETE ✅ — Phase 2 COMPLETE ✅ — Phase 2.5 COMPLETE ✅

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
| `capture_html.py` | Browser/URL configs for offline HTML capture (dev tool) |

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

### Known Issues
- **Concurrent mode transient failures:** Running 3+ browsers simultaneously causes occasional
  `Target page, context or browser has been closed` or navigation timeout errors due to macOS
  resource contention. All failures are transient — the same (site, country) pairs succeed in
  sequential mode. Multi-country concurrent run scored 43/48 (90%). Potential mitigations:
  automatic retry with backoff, lower default `--max-workers`, or sequential fallback on failure.

### Archived Code (`archive/`)

The original per-site handler scraper is preserved in `archive/` for reference:
- `archive/scrapers/` — Old entry points (`concurrent_modified_scraper.py`, `modified_scraper.py`, `requests_scraper.py`)
- `archive/site_handlers/` — All 20 handler files (base, template, 16 sites + archive_spotify)
- `archive/test_scripts/` — Test/debug scripts and Phase 1 comparison harness
- `archive/debug/` — Debug scripts, test screenshots, HTML artifacts

### Next Steps (Phase 3+)
1. **Concurrent robustness** — retry logic / sequential fallback for transient browser crashes
2. Multi-country validation with proxies (UK, DE) — initial run: 43/48 pass (90%)
3. Phase 3: SQLite storage, historical tracking
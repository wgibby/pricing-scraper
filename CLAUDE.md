# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM-powered pricing scraper that collects subscription pricing data from 15 websites
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
# Scrape specific sites for US (includes SQLite storage + change detection)
python -m v2.orchestrator --sites spotify netflix --countries us

# Scrape all 16 sites for US
python -m v2.orchestrator --all --countries us

# Multi-country
python -m v2.orchestrator --all --countries us uk de

# All sites, all countries
python -m v2.orchestrator --all --all-countries

# Concurrent mode (default 2 workers, with automatic retry)
python -m v2.orchestrator --all --countries us --concurrent

# Skip database (JSON only, same as pre-Phase 3)
python -m v2.orchestrator --all --countries us --no-db

# Registry info
python -m v2.registry                              # list all sites
python -m v2.registry --site netflix --country de   # single site detail

# Browser test (no extraction)
python -m v2.browser --site spotify --country us

# Database info
python -m v2.db --info

# Export for website
python -m v2.export --output /path/to/pricing_data_formatted.json
python -m v2.export --dry-run

# View price changes
python -m v2.diff --last          # most recent run
python -m v2.diff --run-id 5      # specific run

# One-time import of existing results
python -m v2.import_history
```

## Architecture

### Data Flow

1. Site config loaded from `v2/company_registry.json`
2. Proxy selected and validated for target country (via `enhanced_proxy_utils.py`)
3. Playwright browser launched with stealth profile + cookie consent handling
4. Site-specific interactions executed (Netflix signup flow, Adobe geo-popup, etc.)
5. Tiered extraction cascade: Cleaned HTML (Tier 2) → Vision/OCR (Tier 4)
6. Structured pricing data returned as Pydantic models, saved as JSON
7. Results stored in SQLite (`data/pricing.db`) with automatic change detection
8. Screenshots captured for verification

### Proxy Management

- `proxy_utils.py` - Basic proxy functionality
- `enhanced_proxy_utils.py` - Enhanced validation for geo-sensitive sites
- `proxy_config.py` - Proxy configuration
- Automatic proxy selection based on target country

## Output Structure

- `data/pricing.db` - SQLite database (runs, results, plans, price_changes)
- `results/v2/{site}_{country}_{timestamp}.json` - Structured pricing data (kept for debugging)
- `screenshots/v2/{site}_{country}_{timestamp}.png` - Browser screenshots

## V2 Pipeline (Last Updated: 2026-03-03)

### Status: Phase 1 ✅ — Phase 2 ✅ — Phase 2.5 ✅ — Phase 3 ✅ — Phase 3.5 ✅ — Phase 3.6 ✅ — Phase 5a ✅ — Phase 5b ✅

### V2 Components (`v2/`)

| File | Purpose |
|------|---------|
| `company_registry.json` | Static config for all 16 sites — URLs, browser, geo strategy, interactions |
| `registry.py` | Load registry, resolve URLs per (site, country), proxy selection |
| `browser.py` | Browser launch, stealth profiles, cookie consent, page stabilization |
| `interactions.py` | Site-specific overrides: Netflix multi-step, Adobe geo-popup |
| `orchestrator.py` | Main entry point — sequential + concurrent scrape pipeline + SQLite storage |
| `models.py` | Pydantic data models (PricingPlan, PricingExtraction) + Claude tool schema |
| `html_cleaner.py` | 5-pass HTML cleaning — 95-98% size reduction, target <20K chars |
| `llm_client.py` | Claude tool_use wrapper (Sonnet) — text + vision, .env API key loading |
| `extractor.py` | Tiered cascade: JSON-LD (stub) → Cleaned HTML → OCR (stub) → Vision |
| `capture_html.py` | Browser/URL configs for offline HTML capture (dev tool) |
| `db.py` | SQLite schema, connection management, `--info` CLI |
| `store.py` | Write orchestrator results to SQLite (runs/results/plans) |
| `diff.py` | Detect price changes between runs, `--last` / `--run-id` CLI |
| `export.py` | Export latest prices as grouped website-compatible JSON, `--output` / `--dry-run` |
| `import_history.py` | One-time import of existing `results/v2/*.json` files into SQLite |

### Phase 2 Validation Results (16/16 US → now 15 sites)
- Adobe removed (Phase 3.6) — 15 active sites
- 13 sites resolve at Tier 2 (HTML) — 81%
- 2 sites resolve at Tier 4 (Vision) — Figma, Netflix
- 5 high confidence, 10 medium, 1 low (Netflix)
- Concurrent mode validated (ThreadPoolExecutor, per-thread browsers)
- Results saved to `results/v2/{site}_{country}_{timestamp}.json`
- Screenshots saved to `screenshots/v2/{site}_{country}_{timestamp}.png`

### Browser Requirements
- **Firefox required (7):** Box, Canva, ChatGPT+, Disney+, Netflix, Peacock, YouTube
- **Chromium works (8):** Audible, Dropbox, Evernote, Figma, Grammarly, Notion, Spotify, Zwift

### Critical Technical Notes
- **DO NOT use `add_init_script`** for Canva — crashes Chromium on macOS (registry: `skip_init_script: true`)
- **Anthropic API max image dimension is 8000px** — `llm_client.py` auto-resizes larger screenshots
- **HTML cleaner target is 20K chars** — reduced from 32K after validation
- **max_tokens is 4096** — complex pages with many plans need the extra output space
- **`.env` file** in project root holds `ANTHROPIC_API_KEY` (loaded via stdlib, not python-dotenv)
- **Box runs non-headless** (`headless: false` in registry) — Cloudflare bypass

### Retry Logic
- **Smart retry** in `scrape_one()`: classifies errors as transient vs. structural
- Transient errors (browser crash, proxy tunnel, timeout): up to 2 inline retries with 3s delay
- Structural errors (site redirect to different domain): fail immediately, no retry
- Unknown errors: not retried (conservative default)
- Error patterns defined in `RETRYABLE_PATTERNS` and `STRUCTURAL_PATTERNS` constants

### Concurrent Mode
- Default `--max-workers` is 2 (reduced from 3 to avoid macOS resource contention)
- After concurrent batch, transient failures retried sequentially (structural failures skipped)
- Summary shows inline retries, concurrent retries, and error breakdown (structural vs transient)

### Archived Code (`archive/`)

The original per-site handler scraper is preserved in `archive/` for reference:
- `archive/scrapers/` — Old entry points (`concurrent_modified_scraper.py`, `modified_scraper.py`, `requests_scraper.py`)
- `archive/site_handlers/` — All 20 handler files (base, template, 16 sites + archive_spotify)
- `archive/test_scripts/` — Test/debug scripts and Phase 1 comparison harness
- `archive/debug/` — Debug scripts, test screenshots, HTML artifacts

### Phase 3: SQLite Storage + Change Detection + Website Export
- Database: `data/pricing.db` (SQLite, WAL mode)
- Tables: `runs`, `results`, `plans`, `price_changes` + `latest_results` view
- Orchestrator auto-stores results and runs change detection after each scrape
- Use `--no-db` flag to skip SQLite (JSON-only mode, same as pre-Phase 3)
- `v2/export.py` transforms v2 data into grouped website format: `{success, data: [{website, country, plans}]}`
- Historical import: `python -m v2.import_history` backfills existing JSON files

### Phase 3.5: Multi-Country Validation (2026-03-01) — COMPLETE
- Full matrix: 16 sites x 13 countries = 208 pairs
- **207/208 (99.5%)** after retries — only Disney+ IN is a structural failure (redirects to Hotstar)
- Per-country: US/UK/DE/MX/ES/JP/NL = 100%, FR/CA/BR/IT/AU = 94%, IN = 94%
- Tier distribution: 136 T2 (69%), 62 T4 (31%)
- Smart retry logic added: transient errors auto-retry, structural errors fail fast

### Phase 3.6: 100% Pricing Coverage (2026-03-03)
Changes to achieve full pricing coverage across all paid plans:

**Registry cleanup:**
- Adobe removed (`status: "removed"`) — unreliable pricing page
- Peacock restricted to US-only (geo-blocked everywhere else)
- Disney+ IN removed (redirects to Hotstar)
- Spotify: `plan_name_blocklist: ["Audiobooks Access"]` to filter spurious upsell panel

**Post-processing (`v2/orchestrator.py`):**
- `_postprocess_extraction()` runs after LLM extraction, before storage
- Computes `annual_price = annual_monthly_equivalent * 12` when missing
- Computes `annual_monthly_equivalent = annual_price / 12` when missing
- Filters plans matching `plan_name_blocklist` from registry config

**Prompt engineering (`v2/models.py`, `v2/llm_client.py`):**
- Price field descriptions clarified: month-to-month vs billed-annually
- SYSTEM_PROMPT now has explicit rules for `$X/mo billed annually` → annual_monthly_equivalent + annual_price
- Prices must go in price fields, not notes

**Netflix overhaul (`v2/interactions.py`, `v2/registry.py`, registry):**
- Locale-based URLs: `?locale=en-US`, `?locale=ja-JP`, etc. (was bare `/signup/planform`)
- Anti-detection init_script: webdriver mask, fake plugins, automation trace removal
- **Locale-matched init_script**: `navigator.languages` and `Accept-Language` header match target country (was hardcoded to en-US, causing Netflix to switch to English after clicks)
- Ultra-stealth cookie consent via JS eval + CSS injection
- **Zero-width character stripping** (`U+FEFF` etc.): Netflix injects invisible chars between every character in non-English pages as anti-scraping; `_strip_zero_width()` applied to all text matching
- **JS CTA click** (`_netflix_js_click_cta`): finds button by DOM size/position instead of text (bypasses zero-width char issues); uses Playwright click + dispatchEvent for React reliability
- **Polling with re-click** (`_netflix_wait_for_pricing`): polls every 2s for up to 18s after click; re-clicks CTA at halfway point if pricing hasn't appeared (handles flaky React hydration)
- **Auto language detection**: step indicator check scans ALL language patterns, not just expected country, to handle Netflix serving English for non-English locales
- Visible text pricing detection: `_has_pricing_content()` uses `page.inner_text('body')` (not raw HTML) and requires BOTH a currency signal AND a billing period signal
- Multi-click fallback methods (normal → force), Japanese locator, country-prefixed fallback nav
- Natural scrolling after reaching plan form
- **13/13 countries validated** (2026-03-03): all Tier 2, all high confidence

**Browser fixes:**
- Configurable `stabilization_wait_ms` in registry (Disney+ 8000ms, Evernote 6000ms)
- `navigation_wait_until` config (YouTube uses `"load"` instead of `"networkidle"`)
- Disney+ `disney_wait_for_prices` interaction: `wait_for_selector` on price elements
- Zwift `zwift_region_popup` interaction: close button + Escape dismissal

**Coverage metric (`v2/orchestrator.py`):**
- `--coverage-report` flag: shows per-plan pricing gaps
- Pricing coverage always printed after summary (count of paid plans with prices)
- `_count_pricing_coverage()` counts paid plans (excluding free/contact-sales)

### Phase 5a: Export Format Fix (2026-03-03) — COMPLETE
- `v2/export.py` restructured from flat entries to grouped format
- Output: `{success: true, data: [{website, country, timestamp, plans: [...]}]}`
- Export now filters removed sites (adobe) via registry status check
- 173 groups, 828 plan entries from 15 active sites across 13 countries
- Pipeline: `./venv/bin/python -m v2.export --output /path/to/stratdesk-web/pricing_data_formatted.json`

### Phase 5b: Public /data Page (2026-03-03) — COMPLETE
- stratdesk-web repo: `/Users/williamgibby/documents/documents - wgibby-mac-01/stratdesk_web/stratdesk-web`

**Files created/changed in stratdesk-web:**
- `app/data/page.tsx` (new) — server component, reads `pricing_data_formatted.json` at build time via `fs`
- `components/DataTable.tsx` (new) — client component with Monthly/Annual/Trials/Features view switching
- `components/Hero.tsx` (edited) — added "Explore Pricing Data" CTA button linking to `/data`
- `app/page.tsx` (edited) — removed CoverageMatrix, added "Pricing Data" nav link

**DataTable features:**
- Groups plans by `website + planName`, stores both monthly and yearly per country
- View-aware row filtering: Monthly/Annual views hide rows without matching duration data
- Sticky Company/Plan columns, 13 scrollable country columns (US, UK, FR, CA, DE, JP, AU, BR, MX, IT, ES, NL, IN)
- Search bar filtering by company or plan name
- Company name formatting: `chatgpt_plus` → "ChatGPT+", `disney_plus` → "Disney+"
- `font-mono tabular-nums` for price alignment, non-breaking space in prices
- "Beta" badges on Trials and Features tabs
- Footer stats (plan/company/country counts)
- No MongoDB, no API calls — pure static data from props

**Export fix (`v2/export.py`):**
- Now imports `load_registry()` and filters out sites with `status != "active"`
- Eliminates stale historical data from removed sites (adobe)

### Session 12 Validation Results (2026-03-03)
- Partial run: 15 sites x 4 countries (US/DE/JP/BR) = 57 pairs
- **54/57 passed (94.7%)** — zero crashes, Netflix 4/4 perfect
- 3 failures: Box BR/DE/JP (Cloudflare blocks non-US proxies)
- Pricing coverage: 162/163 paid plans (99.4%)
- Only gap: ChatGPT+ BR "Business" plan missing price

### Next Steps

**Immediate — Phase 5c: Plan Name Standardization**
- Plan names vary across countries for same plan (e.g., Netflix "Estándar" vs "Standard")
- Need normalization layer so grouped rows match correctly across languages
- User flagged this as the next priority

**Then — Port Archived Handler Techniques**
Review complete (see memory). Techniques worth porting to v2:
1. **Cloudflare polling loop (Box):** wait up to 60s for Turnstile challenge to auto-resolve
2. **Human mouse simulation (ChatGPT):** `page.mouse.move()` + `bounding_box()` click instead of `element.click()`
3. **DRM permission mock (Disney+):** grant `drm` and `persistent-storage` permissions for streaming sites
4. **Per-country timezone/locale injection (Disney+):** `countrySettings` dict in init_script
5. **`euconsent-v2` and `CybotCookiebotDialogClosed` cookies (Figma):** IAB TCF v2 + Cybot consent
6. **Expand collapsed sections (Evernote):** click `[aria-expanded="false"]` before extraction

**Phase 4 — Scale to 50 Companies**
- Semi-automated pricing page discovery, batch onboarding of ~33 new companies
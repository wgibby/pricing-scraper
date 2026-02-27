"""
HTML cleaning pipeline for the v2 extraction engine.

Takes raw page HTML (typically 200K-1.5MB) and strips it down to
LLM-friendly content (~3-30K chars) while preserving pricing information.

5-pass cleaning strategy:
  Pass 1 — Remove noise tags (script, style, svg, etc.)
  Pass 2 — Remove non-pricing structural elements (nav, footer, header)
  Pass 3 — Strip attributes, keeping only semantic ones
  Pass 4 — Remove empty elements
  Pass 5 — Collapse whitespace and normalize

Then truncate if still oversized (target: <20K chars / ~5K tokens).
"""

import re
import sys
from bs4 import BeautifulSoup, Comment


# Tags that never contain visible pricing content
NOISE_TAGS = [
    "script", "style", "svg", "noscript", "link", "meta",
    "iframe", "img", "picture", "source", "video", "audio",
    "canvas", "map", "object", "embed",
]

# Structural tags that wrap site chrome, not pricing content.
# Pricing cards live in <main>, <section>, <article>, or <div> — not these.
STRUCTURAL_NOISE_TAGS = ["nav", "footer", "header"]

# Attributes worth keeping — they carry semantic meaning the LLM can use
KEEP_ATTRS = {"aria-label", "alt", "title", "role", "data-testid"}

# Tags that should be preserved even if empty (structural purpose)
PRESERVE_EMPTY = {"br", "hr", "td", "th", "tr", "thead", "tbody", "table"}

# Pricing keywords used to identify relevant sections during truncation
PRICING_KEYWORDS = re.compile(
    r"\$|€|£|¥|₹|R\$|/month|/year|/mo|/yr|per month|per year|annually|"
    r"pricing|plan[s ]|subscribe|subscription|premium|pro |enterprise|"
    r"free tier|free plan|contact.?sales|get started|upgrade|billing",
    re.IGNORECASE,
)

# Max output size in characters (~5K tokens for Sonnet).
# Reduced from 32K — large HTML (16-30K) causes incomplete LLM responses.
MAX_OUTPUT_CHARS = 20_000


def clean_html(raw_html: str) -> str:
    """
    Clean raw HTML down to LLM-friendly content.

    Args:
        raw_html: Full page HTML from page.content()

    Returns:
        Cleaned HTML string, typically 3-30K chars with pricing intact.
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    # Pass 1: Remove noise tags
    _remove_noise_tags(soup)

    # Pass 2: Remove structural chrome (nav, footer, header)
    _remove_structural_noise(soup)

    # Pass 3: Strip non-semantic attributes
    _strip_attributes(soup)

    # Pass 4: Remove empty elements
    _remove_empty_elements(soup)

    # Pass 5: Collapse whitespace
    result = _collapse_whitespace(str(soup))

    # Truncate if still oversized
    if len(result) > MAX_OUTPUT_CHARS:
        result = _truncate(soup, result)

    return result


def _remove_noise_tags(soup: BeautifulSoup) -> None:
    """Pass 1: Remove tags that never contain visible pricing content."""
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()

    # Also remove HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()


def _remove_structural_noise(soup: BeautifulSoup) -> None:
    """Pass 2: Remove site chrome (nav, footer, header)."""
    for tag in soup.find_all(STRUCTURAL_NOISE_TAGS):
        tag.decompose()


def _strip_attributes(soup: BeautifulSoup) -> None:
    """Pass 3: Strip attributes, keeping only semantic ones."""
    for tag in soup.find_all(True):
        tag.attrs = {
            k: v for k, v in tag.attrs.items()
            if k in KEEP_ATTRS
        }


def _remove_empty_elements(soup: BeautifulSoup) -> None:
    """Pass 4: Remove elements with no text content and no meaningful children."""
    # Multiple passes — removing an empty child may make the parent empty too
    for _ in range(3):
        changed = False
        for tag in soup.find_all(True):
            if tag.name in PRESERVE_EMPTY:
                continue
            # Check if tag has any non-whitespace text content (direct or nested)
            if not tag.get_text(strip=True):
                tag.decompose()
                changed = True
        if not changed:
            break


def _collapse_whitespace(html: str) -> str:
    """Pass 5: Collapse multiple whitespace chars and blank lines."""
    # Collapse runs of whitespace (but preserve single newlines for readability)
    html = re.sub(r"[ \t]+", " ", html)
    # Collapse multiple blank lines into one
    html = re.sub(r"\n\s*\n+", "\n", html)
    # Remove whitespace between tags
    html = re.sub(r">\s+<", "> <", html)
    return html.strip()


def _truncate(soup: BeautifulSoup, cleaned: str) -> str:
    """
    Truncation strategy for oversized pages.

    Tries three approaches in order:
    1. Extract just <main> content
    2. Extract sections containing pricing keywords
    3. Hard truncate from the bottom (pricing is almost always above-fold)
    """
    # Strategy 1: Look for <main> tag
    main_tag = soup.find("main")
    if main_tag:
        candidate = _collapse_whitespace(str(main_tag))
        if len(candidate) <= MAX_OUTPUT_CHARS:
            _log(f"Truncation: used <main> tag ({len(candidate)} chars)")
            return candidate

    # Strategy 2: Find sections with pricing keywords
    pricing_sections = []
    for section in soup.find_all(["section", "div", "main", "article"]):
        text = section.get_text()
        if PRICING_KEYWORDS.search(text):
            pricing_sections.append(str(section))

    if pricing_sections:
        candidate = _collapse_whitespace(" ".join(pricing_sections))
        if len(candidate) <= MAX_OUTPUT_CHARS:
            _log(f"Truncation: extracted pricing sections ({len(candidate)} chars)")
            return candidate
        # If combined sections still too large, take the best ones
        # Sort by density of pricing keywords
        scored = []
        for sec_html in pricing_sections:
            matches = len(PRICING_KEYWORDS.findall(sec_html))
            density = matches / max(len(sec_html), 1)
            scored.append((density, sec_html))
        scored.sort(reverse=True)

        result_parts = []
        total_len = 0
        for _, sec_html in scored:
            if total_len + len(sec_html) > MAX_OUTPUT_CHARS:
                break
            result_parts.append(sec_html)
            total_len += len(sec_html)

        if result_parts:
            candidate = _collapse_whitespace(" ".join(result_parts))
            _log(f"Truncation: top pricing sections by density ({len(candidate)} chars)")
            return candidate

    # Strategy 3: Hard truncate from the bottom
    _log(f"Truncation: hard cut at {MAX_OUTPUT_CHARS} chars (pricing is usually above-fold)")
    return cleaned[:MAX_OUTPUT_CHARS]


def _log(msg: str) -> None:
    """Log cleaner diagnostics to stderr."""
    print(f"[html_cleaner] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI entry point for testing
# ---------------------------------------------------------------------------

def main():
    """Run the cleaner against an HTML file and print diagnostics."""
    if len(sys.argv) < 2:
        print("Usage: python -m v2.html_cleaner <path_to_html_file>")
        print("       python -m v2.html_cleaner <path1> <path2> ...")
        sys.exit(1)

    for filepath in sys.argv[1:]:
        print(f"\n{'='*60}")
        print(f"  File: {filepath}")
        print(f"{'='*60}")

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()

        cleaned = clean_html(raw)

        print(f"  Raw size:     {len(raw):>10,} chars")
        print(f"  Cleaned size: {len(cleaned):>10,} chars")
        print(f"  Reduction:    {(1 - len(cleaned)/len(raw))*100:.1f}%")
        print(f"  Under 20K:    {'YES' if len(cleaned) <= MAX_OUTPUT_CHARS else 'NO'}")

        # Check for pricing content survival
        pricing_hits = PRICING_KEYWORDS.findall(cleaned)
        print(f"  Pricing keywords found: {len(pricing_hits)}")

        # Show a sample of the output
        print(f"\n  --- First 2000 chars of cleaned output ---")
        print(cleaned[:2000])
        print(f"\n  --- Last 1000 chars of cleaned output ---")
        print(cleaned[-1000:])
        print()


if __name__ == "__main__":
    main()

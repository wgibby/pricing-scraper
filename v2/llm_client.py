"""
LLM client for the v2 pricing extraction pipeline.

Wraps the Anthropic API with tool_use to force structured pricing output.
Shared by Tier 2 (cleaned HTML), Tier 3 (OCR text), and Tier 4 (screenshot vision).

Usage:
    from v2.llm_client import extract_pricing
    result = extract_pricing(content, company="Grammarly", country="us")
    result = extract_pricing(image_b64, company="Canva", country="us", input_type="vision")
"""

import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _load_env():
    """Load .env file from project root into os.environ (stdlib, no deps)."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()

import anthropic

from v2.models import (
    PRICING_EXTRACTION_TOOL,
    Confidence,
    PricingExtraction,
    PricingPlan,
)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096  # Bumped from 2048 — complex pages with many plans need more output space

SYSTEM_PROMPT = (
    "You are a pricing data extraction assistant. Extract ALL subscription/pricing "
    "plans shown on this page. Be precise with prices — include exact amounts as "
    "displayed. If a price shows a comma as decimal separator (European format like "
    "€9,99), convert to dot notation (9.99). For Japanese yen and other zero-decimal "
    "currencies, use integer values. If you cannot determine a field with confidence, "
    "set extraction_confidence to \"low\" and explain in extraction_notes."
)


def extract_pricing(
    content: str,
    company: str,
    country: str,
    input_type: str = "html",
) -> PricingExtraction:
    """
    Send content to Claude Sonnet and get structured pricing data back.

    Args:
        content: Cleaned HTML (Tier 2), OCR text (Tier 3), or base64 PNG (Tier 4).
        company: Company name (e.g., "Grammarly") — gives the LLM context.
        country: ISO country code (e.g., "us") — helps identify expected currency.
        input_type: One of "html", "ocr_text", or "vision".

    Returns:
        PricingExtraction with validated pricing data.
        On failure, returns a low-confidence result with error details.
    """
    client = anthropic.Anthropic()

    messages = _build_messages(content, company, country, input_type)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=[PRICING_EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_pricing_data"},
            messages=messages,
        )
    except anthropic.APIError as e:
        _log(f"API error: {e}")
        return _error_result(f"Anthropic API error: {e}")

    return _parse_response(response)


def extract_pricing_from_screenshot(
    screenshot_path: str,
    company: str,
    country: str,
) -> PricingExtraction:
    """
    Convenience wrapper: read a screenshot file and run vision extraction.

    Args:
        screenshot_path: Path to a PNG screenshot.
        company: Company name.
        country: ISO country code.

    Returns:
        PricingExtraction from Tier 4 vision.
    """
    path = Path(screenshot_path)
    if not path.exists():
        return _error_result(f"Screenshot not found: {screenshot_path}")

    image_bytes = _resize_if_needed(path)
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    return extract_pricing(image_b64, company, country, input_type="vision")


MAX_IMAGE_DIMENSION = 8000


def _resize_if_needed(path: Path) -> bytes:
    """
    Read an image and resize it if either dimension exceeds the API limit (8000px).

    Uses Pillow if available, otherwise falls back to macOS sips.
    Returns the (possibly resized) image bytes as PNG.
    """
    # Try Pillow first
    try:
        from PIL import Image

        img = Image.open(path)
        w, h = img.size
        if w <= MAX_IMAGE_DIMENSION and h <= MAX_IMAGE_DIMENSION:
            return path.read_bytes()

        scale = min(MAX_IMAGE_DIMENSION / w, MAX_IMAGE_DIMENSION / h)
        new_w, new_h = int(w * scale), int(h * scale)
        _log(f"Resizing {w}x{h} → {new_w}x{new_h} (Pillow)")
        img = img.resize((new_w, new_h), Image.LANCZOS)

        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        pass

    # Fallback: macOS sips
    try:
        result = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
            capture_output=True, text=True,
        )
        lines = result.stdout.strip().splitlines()
        w = int([l for l in lines if "pixelWidth" in l][0].split()[-1])
        h = int([l for l in lines if "pixelHeight" in l][0].split()[-1])

        if w <= MAX_IMAGE_DIMENSION and h <= MAX_IMAGE_DIMENSION:
            return path.read_bytes()

        scale = min(MAX_IMAGE_DIMENSION / w, MAX_IMAGE_DIMENSION / h)
        new_w, new_h = int(w * scale), int(h * scale)
        _log(f"Resizing {w}x{h} → {new_w}x{new_h} (sips)")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        subprocess.run(
            ["sips", "--resampleHeightWidth", str(new_h), str(new_w),
             str(path), "--out", tmp_path],
            capture_output=True,
        )
        data = Path(tmp_path).read_bytes()
        os.unlink(tmp_path)
        return data
    except Exception as e:
        _log(f"Resize fallback failed: {e}, sending original")
        return path.read_bytes()


def _build_messages(
    content: str, company: str, country: str, input_type: str
) -> list[dict]:
    """Build the messages array for the API call."""
    country_upper = country.upper()

    if input_type == "vision":
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": content,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Extract all subscription pricing plans from this "
                            f"{company} pricing page ({country_upper}). "
                            f"Include free tiers and enterprise/contact-sales tiers."
                        ),
                    },
                ],
            }
        ]

    # Tier 2 (HTML) or Tier 3 (OCR text) — both are plain text
    source_label = "cleaned HTML" if input_type == "html" else "OCR text"
    return [
        {
            "role": "user",
            "content": (
                f"Extract all subscription pricing plans from this {company} "
                f"pricing page ({country_upper}). Source: {source_label}\n\n"
                f"{content}"
            ),
        }
    ]


def _parse_response(response) -> PricingExtraction:
    """
    Extract the tool_use block from Claude's response and validate with Pydantic.

    Returns a low-confidence result if parsing or validation fails.
    """
    # Find the tool_use content block
    tool_input = None
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_pricing_data":
            tool_input = block.input
            break

    if tool_input is None:
        _log("No tool_use block found in response")
        return _error_result("No tool_use block in Claude response")

    # Validate with Pydantic
    try:
        result = PricingExtraction.model_validate(tool_input)
        return result
    except Exception as e:
        _log(f"Pydantic validation failed: {e}")
        _log(f"Partial tool_input keys: {list(tool_input.keys()) if isinstance(tool_input, dict) else 'N/A'}")
        # Graceful degradation: salvage whatever the LLM did return
        # (e.g., currency_code/symbol but missing plans/confidence)
        return _error_result(
            f"Pydantic validation failed: {e}",
            raw_input=tool_input,
        )


def _error_result(
    message: str, raw_input: dict | None = None
) -> PricingExtraction:
    """Build a low-confidence PricingExtraction for error cases.

    Salvages whatever the LLM did return — currency_code, currency_symbol,
    and any valid plan objects — rather than discarding everything.
    """
    # Defaults
    currency_code = "UNKNOWN"
    currency_symbol = "?"
    plans = []

    if raw_input and isinstance(raw_input, dict):
        # Salvage currency fields if present
        if "currency_code" in raw_input and isinstance(raw_input["currency_code"], str):
            currency_code = raw_input["currency_code"]
        if "currency_symbol" in raw_input and isinstance(raw_input["currency_symbol"], str):
            currency_symbol = raw_input["currency_symbol"]

        # Salvage any valid plan objects
        if "plans" in raw_input and isinstance(raw_input["plans"], list):
            for plan_data in raw_input["plans"]:
                try:
                    plans.append(PricingPlan.model_validate(plan_data))
                except Exception:
                    pass

    return PricingExtraction(
        currency_code=currency_code,
        currency_symbol=currency_symbol,
        plans=plans,
        extraction_confidence=Confidence.LOW,
        extraction_notes=message,
    )


def _log(msg: str) -> None:
    """Log to stderr."""
    print(f"[llm_client] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI entry point for testing
# ---------------------------------------------------------------------------

def main():
    """
    Quick test: clean an HTML file and extract pricing.

    Usage:
        python -m v2.llm_client <html_file> <company_name> [country]
        python -m v2.llm_client screenshots/html/grammarly_us_....html Grammarly us
    """
    if len(sys.argv) < 3:
        print("Usage: python -m v2.llm_client <html_file> <company> [country]")
        print("       python -m v2.llm_client --vision <screenshot.png> <company> [country]")
        sys.exit(1)

    # Check for --vision flag
    if sys.argv[1] == "--vision":
        if len(sys.argv) < 4:
            print("Usage: python -m v2.llm_client --vision <screenshot.png> <company> [country]")
            sys.exit(1)
        screenshot_path = sys.argv[2]
        company = sys.argv[3]
        country = sys.argv[4] if len(sys.argv) > 4 else "us"

        print(f"Extracting pricing from screenshot: {screenshot_path}")
        print(f"Company: {company}, Country: {country}")
        print()

        result = extract_pricing_from_screenshot(screenshot_path, company, country)
    else:
        html_file = sys.argv[1]
        company = sys.argv[2]
        country = sys.argv[3] if len(sys.argv) > 3 else "us"

        print(f"Extracting pricing from HTML: {html_file}")
        print(f"Company: {company}, Country: {country}")
        print()

        # Clean and extract
        from v2.html_cleaner import clean_html

        with open(html_file, "r", encoding="utf-8", errors="replace") as f:
            raw_html = f.read()

        cleaned = clean_html(raw_html)
        print(f"Cleaned HTML: {len(cleaned):,} chars ({len(raw_html):,} raw)")
        print()

        result = extract_pricing(cleaned, company, country, input_type="html")

    # Display results
    print(f"{'='*60}")
    print(f"  EXTRACTION RESULT — {company} ({country.upper()})")
    print(f"{'='*60}")
    print(f"  Confidence: {result.extraction_confidence.value}")
    print(f"  Currency:   {result.currency_symbol} ({result.currency_code})")
    print(f"  Plans:      {len(result.plans)}")
    if result.extraction_notes:
        print(f"  Notes:      {result.extraction_notes}")
    print()

    for i, plan in enumerate(result.plans, 1):
        print(f"  Plan {i}: {plan.plan_name}")
        if plan.is_free_tier:
            print(f"    Price:    FREE")
        elif plan.is_contact_sales:
            print(f"    Price:    Contact Sales")
        else:
            if plan.monthly_price is not None:
                print(f"    Monthly:  {result.currency_symbol}{plan.monthly_price}")
            if plan.annual_price is not None:
                print(f"    Annual:   {result.currency_symbol}{plan.annual_price}")
            if plan.annual_monthly_equivalent is not None:
                print(f"    Annual/mo:{result.currency_symbol}{plan.annual_monthly_equivalent}")
        print(f"    Billing:  {', '.join(b.value for b in plan.billing_periods_available)}")
        print(f"    Audience: {plan.target_audience.value}")
        if plan.key_features:
            print(f"    Features: {', '.join(plan.key_features[:5])}")
        if plan.notes:
            print(f"    Notes:    {plan.notes}")
        print()

    # Also dump the full JSON for inspection
    print(f"{'='*60}")
    print("  FULL JSON OUTPUT")
    print(f"{'='*60}")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

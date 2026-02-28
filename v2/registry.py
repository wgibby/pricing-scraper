"""
Company registry loader and URL resolver for the v2 pipeline.

Loads site configs from company_registry.json and resolves pricing URLs
per (site, country) pair. Also handles proxy selection by delegating to
the existing proxy_utils / enhanced_proxy_utils modules.

Usage:
    python -m v2.registry                              # print all 16 sites with US URLs
    python -m v2.registry --site netflix --country de  # resolved URL + proxy config
"""

import json
import sys
from pathlib import Path

# Registry file lives alongside this module
_REGISTRY_PATH = Path(__file__).parent / "company_registry.json"


def load_registry() -> list[dict]:
    """Load all site configs from company_registry.json."""
    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["sites"]


def get_sites(site_ids: list[str] | None = None) -> list[dict]:
    """
    Get site configs, optionally filtered by ID list.

    Args:
        site_ids: List of site IDs to include (e.g., ["spotify", "netflix"]).
                  None returns all active sites.

    Returns:
        List of matching site config dicts.
    """
    sites = load_registry()
    if site_ids is None:
        return [s for s in sites if s["status"] == "active"]
    id_set = {sid.lower() for sid in site_ids}
    matched = [s for s in sites if s["id"] in id_set and s["status"] == "active"]
    unknown = id_set - {s["id"] for s in matched}
    if unknown:
        print(f"Warning: unknown site IDs: {', '.join(sorted(unknown))}", file=sys.stderr)
    return matched


def resolve_url(site_config: dict, country: str) -> str:
    """
    Resolve the pricing URL for a (site, country) pair.

    For url_country_code strategy: replaces {country} placeholder in the URL.
    For geo_ip / other strategies: returns the URL as-is (geo handled by proxy).

    Args:
        site_config: Site config dict from the registry.
        country: ISO alpha-2 country code (lowercase).

    Returns:
        Resolved URL string.
    """
    url = site_config["pricing_url"]
    strategy = site_config["geo_strategy"]

    if strategy == "url_country_code" and "{country}" in url:
        fmt = site_config.get("url_country_format", "iso_alpha2_lower")
        if fmt == "iso_alpha2_lower":
            return url.replace("{country}", country.lower())
        elif fmt == "iso_alpha2_upper":
            return url.replace("{country}", country.upper())
        else:
            return url.replace("{country}", country.lower())

    return url


def get_proxy_config(site_config: dict, country: str) -> str | None:
    """
    Get proxy URL for a (site, country) pair.

    - US requests: no proxy needed (returns None).
    - Enhanced proxy sites (Netflix, YouTube, Disney+): uses validated proxy.
    - Standard sites: uses basic proxy.

    Args:
        site_config: Site config dict from the registry.
        country: ISO alpha-2 country code (lowercase).

    Returns:
        Proxy URL string, or None if no proxy needed.
    """
    if country.lower() == "us":
        return None

    if site_config.get("enhanced_proxy_validation"):
        try:
            from enhanced_proxy_utils import get_validated_proxy_for_country
            proxy_url, validation = get_validated_proxy_for_country(country)
            if proxy_url:
                return proxy_url
            print(f"  Warning: enhanced proxy validation failed for {country}", file=sys.stderr)
            return None
        except ImportError:
            print("  Warning: enhanced_proxy_utils not available, falling back to basic proxy", file=sys.stderr)

    try:
        from proxy_utils import get_proxy_url
        return get_proxy_url(country)
    except ImportError:
        print("  Warning: proxy_utils not available", file=sys.stderr)
        return None


def get_all_countries() -> list[str]:
    """Get the union of all countries across all active sites."""
    sites = load_registry()
    countries = set()
    for s in sites:
        if s["status"] == "active":
            countries.update(s["countries"])
    return sorted(countries)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="V2 Company Registry")
    parser.add_argument("--site", help="Show details for a specific site ID")
    parser.add_argument("--country", default="us", help="Country code for URL resolution (default: us)")
    parser.add_argument("--list-countries", action="store_true", help="List all supported countries")
    args = parser.parse_args()

    if args.list_countries:
        countries = get_all_countries()
        print(f"Supported countries ({len(countries)}): {', '.join(countries)}")
        return

    if args.site:
        sites = get_sites([args.site])
        if not sites:
            print(f"Unknown site: {args.site}")
            all_sites = get_sites()
            print(f"Available: {', '.join(s['id'] for s in all_sites)}")
            sys.exit(1)

        site = sites[0]
        country = args.country.lower()
        url = resolve_url(site, country)
        print(f"{'='*60}")
        print(f"  {site['display_name']} ({site['id']})")
        print(f"{'='*60}")
        print(f"  Domain:      {site['domain']}")
        print(f"  Category:    {site['category']}")
        print(f"  Browser:     {site['browser']}")
        print(f"  Headless:    {site['headless']}")
        print(f"  Geo strategy:{site['geo_strategy']}")
        print(f"  URL ({country.upper()}):    {url}")
        print(f"  Interaction: {site['interaction_type'] or 'none'}")
        print(f"  Enhanced proxy: {site['enhanced_proxy_validation']}")
        print(f"  Stealth:     {site['stealth_profile']}")
        print(f"  Countries:   {', '.join(site['countries'])}")

        # Show proxy config (skip actual proxy lookup to stay offline)
        if country == "us":
            print(f"  Proxy:       None (US — no proxy needed)")
        elif site["enhanced_proxy_validation"]:
            print(f"  Proxy:       Enhanced validation required")
        else:
            print(f"  Proxy:       Standard proxy for {country.upper()}")

        return

    # Default: show all sites with resolved URLs
    sites = get_sites()
    country = args.country.lower()

    print(f"{'='*70}")
    print(f"  V2 COMPANY REGISTRY — {len(sites)} sites, resolved for {country.upper()}")
    print(f"{'='*70}")
    print(f"  {'ID':<16} {'Browser':<10} {'Geo':<18} {'URL'}")
    print(f"  {'─'*16} {'─'*10} {'─'*18} {'─'*40}")

    for site in sites:
        url = resolve_url(site, country)
        flags = []
        if site["requires_interaction"]:
            flags.append(site["interaction_type"])
        if site["enhanced_proxy_validation"]:
            flags.append("enhanced_proxy")
        if not site["headless"]:
            flags.append("non-headless")
        flag_str = f" [{', '.join(flags)}]" if flags else ""

        print(f"  {site['id']:<16} {site['browser']:<10} {site['geo_strategy']:<18} {url}{flag_str}")

    print(f"\n  Countries: {', '.join(get_all_countries())}")


if __name__ == "__main__":
    main()

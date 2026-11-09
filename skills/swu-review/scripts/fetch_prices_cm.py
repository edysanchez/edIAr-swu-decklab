#!/usr/bin/env python3
"""Fetch the Cardmarket bulk catalog and price guide for Star Wars: Unlimited.

Cardmarket publishes these files publicly and allows importing them into other
applications, so no authentication is needed and the website is never scraped.

Usage::

    python3 skills/swu-review/scripts/fetch_prices_cm.py
    python3 skills/swu-review/scripts/fetch_prices_cm.py --cache-dir /tmp/cm

Files are written to ``data/cm/`` (gitignored):

* ``products_singles_21.json``
* ``price_guide_21.json``
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).parent))

import constants as C
import swu_cards as sc

USER_AGENT = "edIAr-swu-decklab/0.1"


def fetch_json(url):
    """Download and decode one JSON document."""
    print(f"Fetching {url}...", file=sys.stderr)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_prices(cache_dir=None):
    """Download both Cardmarket files and return a summary dict."""
    cache_dir = (
        Path(cache_dir)
        if cache_dir is not None
        else sc.get_data_dir() / C.CARDMARKET_CACHE_DIR
    )
    catalog_url = f"{C.CARDMARKET_BASE_URL}/productList/{C.CARDMARKET_CATALOG_FILE}"
    prices_url = f"{C.CARDMARKET_BASE_URL}/priceGuide/{C.CARDMARKET_PRICE_FILE}"

    catalog = fetch_json(catalog_url)
    prices = fetch_json(prices_url)

    if not isinstance(catalog.get("products"), list):
        raise ValueError(f"unexpected catalog payload from {catalog_url}")
    if not isinstance(prices.get("priceGuides"), list):
        raise ValueError(f"unexpected price guide payload from {prices_url}")

    cache_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = cache_dir / C.CARDMARKET_CATALOG_FILE
    prices_path = cache_dir / C.CARDMARKET_PRICE_FILE
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    prices_path.write_text(json.dumps(prices, ensure_ascii=False), encoding="utf-8")

    snapshot = str(prices.get("createdAt", ""))[:10] or "unknown"
    summary = {
        "cache_dir": str(cache_dir),
        "products": len(catalog["products"]),
        "quotes": len(prices["priceGuides"]),
        "catalog_snapshot": str(catalog.get("createdAt", ""))[:10] or "unknown",
        "price_snapshot": snapshot,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    print(
        f"Saved {summary['products']} products and {summary['quotes']} quotes "
        f"to {cache_dir} (price snapshot {snapshot}).",
        file=sys.stderr,
    )
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fetch Cardmarket bulk catalog and price guide for SWU.",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        metavar="PATH",
        help="Destination directory (defaults to data/cm/).",
    )
    args = parser.parse_args(argv)

    try:
        fetch_prices(args.cache_dir)
    except (HTTPError, URLError) as exc:
        print(f"ERROR: download failed: {exc}", file=sys.stderr)
        return 1
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

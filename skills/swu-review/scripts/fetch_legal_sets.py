#!/usr/bin/env python3
"""Fetch the Premier legal-set list from SWU Competitive Hub.

The hub page is server-rendered, so no JavaScript is needed. The authoritative
data is the "Legal in Premier — Today, <date>" block: a list of set codes plus
the announced next change. The per-block lists add release dates, including
sets that already rotated out, so they must never be merged into the legal list.

Integrity checks fail closed: an empty list or a missing date aborts the write
instead of producing a snapshot that would silently legalise or block every
deck.

Usage:

    python3 skills/swu-review/scripts/fetch_legal_sets.py
    python3 skills/swu-review/scripts/fetch_legal_sets.py --dry-run
"""

import argparse
import html as htmllib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).parent))

import constants as C

USER_AGENT = "edIAr-swu-decklab/0.1"

TODAY_RE = re.compile(
    r"Today,\s*([A-Za-z]{3,9}\.?\s+\d{1,2},\s*\d{4})", re.IGNORECASE
)
UL_RE = re.compile(r"<ul\b[^>]*>(.*?)</ul>", re.IGNORECASE | re.DOTALL)
LEGAL_CODE_RE = re.compile(r"<span>\s*([A-Z0-9]{2,4})\s*</span>")
SET_ITEM_RE = re.compile(
    r"<span[^>]*>\s*([A-Z0-9]{2,4})\s*</span>"  # code
    r"([^<]{0,80})</span>\s*"  # name (may be empty)
    r"<span[^>]*>\s*(Release|Legal from)\s*:?\s*([^<]+?)\s*</span>",  # date
    re.IGNORECASE | re.DOTALL,
)
NEXT_CHANGE_RE = re.compile(
    r"Next change:\s*</strong>\s*(.+?)\s+becomes legal on\s+"
    r"([A-Za-z]{3,9}\.?\s+\d{1,2},\s*\d{4})",
    re.IGNORECASE | re.DOTALL,
)

MONTHS = {
    name[:3].lower(): index
    for index, name in enumerate(
        (
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ),
        start=1,
    )
}


class LegalSetsPageError(RuntimeError):
    """The page could not be parsed into the expected structure."""


def fetch(url, timeout=60):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_date(text):
    """Turn ``Nov 12, 2026`` (or ``12 November 2026``) into ``2026-11-12``."""
    match = re.match(
        r"\s*([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s*(\d{4})\s*$", str(text or "")
    )
    if not match:
        match = re.match(
            r"\s*(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\s*$", str(text or "")
        )
        if not match:
            return None
        day, month_name, year = match.groups()
    else:
        month_name, day, year = match.groups()

    month = MONTHS.get(month_name.lower()[:3])
    if month is None:
        return None
    return f"{int(year):04d}-{month:02d}-{int(day):02d}"


def _text(fragment):
    return " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_page(page):
    """Parse the hub page into ``{as_of, legal, next_change, products}``."""
    today = TODAY_RE.search(page)
    if not today:
        raise LegalSetsPageError("No 'Today, <date>' marker found on the page")

    as_of = parse_date(today.group(1))

    legal_list = UL_RE.search(page, today.end())
    if not legal_list:
        raise LegalSetsPageError("No set list found after the 'Today' marker")
    legal = [code.upper() for code in LEGAL_CODE_RE.findall(legal_list.group(1))]

    next_change = None
    upcoming = NEXT_CHANGE_RE.search(page)
    if upcoming:
        next_change = {
            "product": _text(upcoming.group(1)),
            "legal_from": parse_date(upcoming.group(2)),
        }

    products = []
    seen = set()
    for match in SET_ITEM_RE.finditer(page):
        code = match.group(1).upper()
        if code in seen:
            continue
        seen.add(code)
        label = match.group(3).strip().lower()
        product = {
            "code": code,
            "name": _text(match.group(2)),
        }
        # Released sets carry "Release: <date>"; upcoming ones "Legal from <date>".
        product["release" if label == "release" else "legal_from"] = parse_date(
            match.group(4)
        )
        products.append(product)

    return {
        "as_of": as_of,
        "legal": legal,
        "next_change": next_change,
        "products": products,
    }


def check_page(parsed):
    """Raise when the parsed data cannot be a real answer."""
    if not parsed["legal"]:
        raise LegalSetsPageError(
            "No legal set codes parsed; the markup probably changed"
        )
    if len(set(parsed["legal"])) != len(parsed["legal"]):
        raise LegalSetsPageError(
            f"Duplicated set codes parsed: {sorted(parsed['legal'])}"
        )
    if not parsed["as_of"]:
        raise LegalSetsPageError(
            "No usable 'Today, <date>' value; the release-date override would be disabled"
        )


def build_snapshot(parsed, source=None, fetched_at=None):
    return {
        "source": source or C.LEGAL_SETS_HUB_URL,
        "fetched_at": fetched_at
        or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "as_of": parsed["as_of"],
        "legal": parsed["legal"],
        "next_change": parsed["next_change"],
        "products": parsed["products"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=C.LEGAL_SETS_HUB_URL, help="page to fetch")
    parser.add_argument(
        "--out", default=C.LEGAL_SETS_SNAPSHOT_PATH, help="snapshot path"
    )
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true", help="print, do not write")
    args = parser.parse_args(argv)

    try:
        page = fetch(args.url, timeout=args.timeout)
    except (HTTPError, URLError, OSError) as exc:
        print(f"ERROR: could not fetch {args.url}: {exc}", file=sys.stderr)
        return 1

    try:
        parsed = parse_page(page)
        check_page(parsed)
    except LegalSetsPageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    snapshot = build_snapshot(parsed, source=args.url)

    if args.dry_run:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(
        f"Saved {out_path}: {len(snapshot['legal'])} legal sets as of "
        f"{snapshot['as_of']} ({len(snapshot['products'])} release dates)",
        file=sys.stderr,
    )
    print(f"  legal: {', '.join(snapshot['legal'])}", file=sys.stderr)
    if snapshot["next_change"]:
        change = snapshot["next_change"]
        print(f"  next change: {change['product']} on {change['legal_from']}", file=sys.stderr)
    else:
        print("  next change: not announced on the page", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

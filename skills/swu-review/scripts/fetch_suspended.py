#!/usr/bin/env python3
"""Fetch the Premier suspended list from SWU Competitive Hub.

The hub page is server-rendered, so no JavaScript is needed. Each suspended
card is a ``<button aria-label="Name, Subtitle" data-apercu=".../NUMBER_EN_...">``
inside a per-format ``<section>``, and the page states both the number of
suspended cards and its own last-updated date. Those two facts are used as
integrity checks: a mismatch means the markup changed, and the command fails
instead of writing an empty list.

Usage:

    python3 skills/swu-review/scripts/fetch_suspended.py
    python3 skills/swu-review/scripts/fetch_suspended.py --dry-run
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

H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
BUTTON_RE = re.compile(r"<button\b[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(r'(aria-label|data-apercu)="([^"]*)"', re.IGNORECASE)
COUNT_RE = re.compile(
    r"(\d+)\s+cards?\s+(?:are|is)\s+suspended\s+in\s+([A-Za-z ]+?)\s+format",
    re.IGNORECASE,
)
UPDATED_RE = re.compile(
    r"Last Updated\s*:?\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})",
    re.IGNORECASE,
)
IMAGE_NUMBER_RE = re.compile(r"/(\d{8})_EN_", re.IGNORECASE)

MONTHS = {
    name: index
    for index, name in enumerate(
        (
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ),
        start=1,
    )
}


class SuspendedPageError(RuntimeError):
    """The page could not be parsed into the expected structure."""


def fetch(url, timeout=60):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _strip_tags(fragment):
    text = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(htmllib.unescape(text).split())


def _clean(text):
    return " ".join(htmllib.unescape(re.sub(r"<[^>]+>", "", text)).split())


def _number_from_image(url):
    match = IMAGE_NUMBER_RE.search(url or "")
    return match.group(1)[-4:] if match else ""


def parse_last_updated(page):
    match = UPDATED_RE.search(_strip_tags(page))
    if not match:
        return None
    day, month, year = match.groups()
    month_number = MONTHS.get(month.lower())
    if month_number is None:
        return None
    return f"{int(year):04d}-{month_number:02d}-{int(day):02d}"


def parse_page(page):
    """Parse the hub page into ``{"last_updated", "formats"}``."""
    headings = list(H2_RE.finditer(page))
    formats = {}

    for index, match in enumerate(headings):
        name = _clean(match.group(1)).rstrip(" :")
        if not name.lower().endswith("format"):
            continue
        if "history" in name.lower():
            continue

        end = headings[index + 1].start() if index + 1 < len(headings) else len(page)
        body = page[match.end():end]
        body_text = _strip_tags(body)

        label = re.sub(r"\s*format\s*$", "", name, flags=re.IGNORECASE).strip()
        if not label:
            continue

        count_match = COUNT_RE.search(body_text)
        declared = int(count_match.group(1)) if count_match else None

        entries = []
        for tag in BUTTON_RE.finditer(body):
            attrs = {key.lower(): value for key, value in ATTR_RE.findall(tag.group(0))}
            card_label = htmllib.unescape(attrs.get("aria-label", "")).strip()
            if not card_label:
                continue
            image = htmllib.unescape(attrs.get("data-apercu", "")).strip()
            entries.append(
                {"label": card_label, "number": _number_from_image(image), "image": image}
            )

        formats[label] = {"count": declared, "entries": entries}

    if "Premier" not in formats:
        raise SuspendedPageError("No 'Premier Format' section found on the page")

    return {"last_updated": parse_last_updated(page), "formats": formats}


def check_page(parsed, allow_empty=False):
    """Raise when the parsed data looks wrong instead of writing a bad snapshot."""
    premier = parsed["formats"]["Premier"]
    declared = premier.get("count")
    parsed_count = len(premier["entries"])

    if declared is not None and declared != parsed_count:
        raise SuspendedPageError(
            f"Page declares {declared} suspended Premier cards but {parsed_count} "
            "were parsed; the markup probably changed"
        )
    if declared is None and parsed_count == 0:
        raise SuspendedPageError(
            "No suspended Premier cards parsed and no count on the page; the "
            "markup probably changed"
        )
    if parsed_count == 0 and not allow_empty:
        raise SuspendedPageError(
            "Parsed an empty Premier suspended list; pass --allow-empty if FFG "
            "really lifted every suspension"
        )


def build_snapshot(parsed, source=None, fetched_at=None):
    return {
        "source": source or C.SUSPENDED_HUB_URL,
        "fetched_at": fetched_at
        or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "last_updated": parsed.get("last_updated"),
        "formats": parsed["formats"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=C.SUSPENDED_HUB_URL, help="page to fetch")
    parser.add_argument(
        "--out", default=C.SUSPENDED_SNAPSHOT_PATH, help="snapshot path"
    )
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true", help="print, do not write")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="accept an empty Premier list (only if FFG lifted every suspension)",
    )
    args = parser.parse_args(argv)

    try:
        page = fetch(args.url, timeout=args.timeout)
    except (HTTPError, URLError, OSError) as exc:
        print(f"ERROR: could not fetch {args.url}: {exc}", file=sys.stderr)
        return 1

    try:
        parsed = parse_page(page)
        check_page(parsed, allow_empty=args.allow_empty)
    except SuspendedPageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    snapshot = build_snapshot(parsed, source=args.url)
    premier = snapshot["formats"]["Premier"]

    if args.dry_run:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(
        f"Saved {out_path}: {len(premier['entries'])} suspended Premier cards "
        f"(hub last updated {snapshot['last_updated']})",
        file=sys.stderr,
    )
    for entry in premier["entries"]:
        print(f"  - {entry['label']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

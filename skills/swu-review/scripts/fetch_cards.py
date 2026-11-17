#!/usr/bin/env python3
"""
fetch_cards.py - Fetch and normalize card data from swu-db

Downloads Premier sets from https://api.swu-db.com/cards/{SET}
Normalizes to only VariantType == 'Normal', excludes tokens.
Deduplicates by name + subtitle identity.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

sys.path.insert(0, str(Path(__file__).parent))

import constants as C
import swu_cards as sc

CARD_DB_PATH = C.CARD_DB_PATH

API_BASE = "https://api.swu-db.com"
USER_AGENT = "edIAr-swu-decklab/0.1"

# Canonical order for rebuilding the normalised catalogue. A card printed in
# several sets keeps the record of the last set in this order, so the order is
# part of the output: it must be explicit and stable, never the network's.
SET_ORDER = ("JTL", "LOF", "IBH", "SEC", "LAW", "ASH", "HMW")

# Do not retry a set that was checked and found short more often than this: a
# prerelease set is incomplete for weeks and re-downloading it on every analysis
# would cost two requests each time for nothing.
INCOMPLETE_RETRY_HOURS = 6

# Files in the cache directory that are not per-set payloads.
NON_SET_FILES = {"cards_normalized", "meta", "sets_index", "catalogue"}


class FetchError(RuntimeError):
    """The catalogue cannot be built from what the API returned."""


def fetch_set_index(timeout=60):
    """Read ``/sets`` into ``{set_code: metadata}``.

    The endpoint answers with a bare list, not the ``{"data": [...]}`` envelope
    used by ``/cards/{SET}``.
    """
    url = f"{API_BASE}/sets"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, ValueError) as exc:
        raise FetchError(f"could not read {url}: {exc}") from exc

    entries = data.get("data") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise FetchError(f"{url} did not return a list of sets")

    index = {}
    for entry in entries:
        code = str(entry.get("setId") or "").strip().upper()
        if not code:
            continue
        cards = entry.get("numberCards")
        try:
            cards = int(cards)
        except (TypeError, ValueError):
            cards = None
        index[code] = {
            "name": entry.get("fullName") or code,
            "numberCards": cards,
            "releaseDate": entry.get("releaseDate"),
            "isBaseSet": bool(entry.get("isBaseSet")),
            "parentSetId": entry.get("parentSetId"),
        }

    if not index:
        raise FetchError(f"{url} returned no usable sets")
    return index


def select_sets(index, sets=None, include_all=False):
    """Choose which sets to fetch: explicit list, everything, or base sets."""
    if sets:
        codes = []
        for chunk in str(sets).split(","):
            code = chunk.strip().upper()
            if code and code not in codes:
                codes.append(code)
        unknown = [code for code in codes if code not in index]
        if unknown:
            raise FetchError(
                f"unknown set code(s): {', '.join(unknown)}; "
                f"known: {', '.join(sorted(index))}"
            )
        return codes

    if include_all:
        return sorted(index)

    return sorted(code for code, meta in index.items() if meta.get("isBaseSet"))


def fetch_set(set_code):
    """Fetch a set from swu-db API."""
    url = f"{API_BASE}/cards/{set_code}"
    print(f"Fetching {url}...", file=sys.stderr)
    
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode('utf-8'))
        return data
    except HTTPError as e:
        print(f"Error fetching {set_code}: {e}", file=sys.stderr)
        return None
    except URLError as e:
        print(f"Error fetching {set_code}: {e}", file=sys.stderr)
        return None


def normalize_cards(all_cards_data):
    """
    Normalize cards: only VariantType == 'Normal', exclude tokens.
    Deduplicate by name + subtitle.
    """
    cards = {}
    
    for set_code, data in all_cards_data.items():
        if not data or 'data' not in data:
            continue
        
        for row in data['data']:
            # Exclude tokens
            card_type = row.get('Type', '')
            if card_type.startswith('Token') or 'Token' in card_type:
                continue
            
            # Only Normal variants
            if row.get('VariantType') != 'Normal':
                continue
            
            name = row.get('Name', '')
            subtitle = row.get('Subtitle', '') or ''
            key = f"{name}|{subtitle}" if subtitle else name

            # Keep every printing: `docs/rules.md` makes a card legal if any of
            # its printings comes from a Premier-legal product. The surviving
            # `set` stays the last one fetched, for display.
            card_set = row.get('Set', set_code)
            printings = []
            if key in cards:
                printings = list(cards[key].get('printings') or [cards[key]['set']])
            if card_set and card_set not in printings:
                printings.append(card_set)

            record = {
                "name": name,
                "subtitle": subtitle,
                "set": row.get('Set', set_code),
                "number": row.get('Number', ''),
                "type": card_type,
                "aspects": row.get('Aspects', []),
                "traits": row.get('Traits', []),
                "arenas": row.get('Arenas', []),
                "cost": row.get('Cost'),
                "power": row.get('Power'),
                "hp": row.get('HP'),
                "keywords": row.get('Keywords', []),
                "unique": row.get('Unique', False),
                "rarity": row.get('Rarity', ''),
                "frontText": row.get('FrontText', ''),
                "epicAction": row.get('EpicAction'),
                "doubleSided": row.get('DoubleSided', False),
                "marketPriceUsd": row.get('MarketPrice'),
                "lowPriceUsd": row.get('LowPrice'),
                "foilPriceUsd": row.get('FoilPrice'),
                "tcgplayerId": row.get('tcgplayerId'),
                "cid": row.get('cid'),
                "frontArt": row.get('FrontArt'),
                "artist": row.get('Artist')
            }
            if len(printings) > 1:
                record["printings"] = printings
            cards[key] = record
    
    return cards


def set_order_key(code):
    """Sort key that keeps ``SET_ORDER`` first and unknown sets after it."""
    known = SET_ORDER.index(code) if code in SET_ORDER else len(SET_ORDER)
    return (known, code)


def cached_set_codes(sets_dir=None):
    """Return the set codes with a raw payload in the cache, in canonical order."""
    directory = Path(sets_dir) if sets_dir is not None else Path(CARD_DB_PATH).parent
    if not directory.exists():
        return []
    codes = [
        path.stem
        for path in directory.glob("*.json")
        if path.stem not in NON_SET_FILES
    ]
    return sorted(codes, key=set_order_key)


def read_sets_index(sets_dir=None):
    """Read the per-set completeness index (shared with `swu_cards`)."""
    return sc.read_sets_index(sets_dir)


def write_sets_index(index, sets_dir=None):
    """Write the completeness index atomically."""
    directory = Path(sets_dir) if sets_dir is not None else Path(CARD_DB_PATH).parent
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "sets_index.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(index, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    os.replace(tmp, path)
    return path


def is_incomplete(meta):
    """A set is unusable only when it was checked and found short."""
    return bool(meta) and meta.get("complete") is False


def recently_checked(meta, hours=INCOMPLETE_RETRY_HOURS):
    """Whether an incomplete set was already tried within the retry window."""
    stamp = (meta or {}).get("checked_at")
    if not stamp:
        return False
    try:
        checked = datetime.fromisoformat(str(stamp))
    except ValueError:
        return False
    return (datetime.now() - checked).total_seconds() < hours * 3600


def load_cached_sets(sets_dir=None):
    """Read the usable cached payloads into ``{set_code: payload}``, in order."""
    directory = Path(sets_dir) if sets_dir is not None else Path(CARD_DB_PATH).parent
    index = read_sets_index(directory)
    payloads = {}
    for code in cached_set_codes(directory):
        if is_incomplete(index.get(code)):
            continue
        with open(directory / f"{code}.json", "r", encoding="utf-8") as handle:
            payloads[code] = json.load(handle)
    return payloads


def payload_card_count(payload):
    """Number of distinct numbered cards in a set payload."""
    numbers = set()
    for row in payload.get("data") or []:
        if "Token" in str(row.get("Type", "")):
            continue
        if row.get("VariantType") != "Normal":
            continue
        number = str(row.get("Number") or "").strip()
        if number:
            numbers.add(number)
    return len(numbers)


def completeness(payload, expected):
    """Compare a payload with the count the API publishes for the set.

    ``expected is None`` means the set is not described by /sets, so the payload
    cannot be validated: it is usable but not certified.
    """
    received = payload_card_count(payload)
    return {
        "expected": expected,
        "received": received,
        "complete": None if expected is None else received >= expected,
    }


def store_set(code, data, sets_dir=None):
    """Store a raw set payload atomically."""
    directory = Path(sets_dir) if sets_dir is not None else Path(CARD_DB_PATH).parent
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{code}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return path


def ensure_sets(
    codes, sets_dir=None, set_index=None, fetcher=None, out_path=None,
    timeout=60, refresh=False,
):
    """Download the sets that are missing or incomplete.

    ``set_index`` is the metadata from /sets (``{code: {"numberCards": n}}``).
    Returns ``{code: {"status": "cached" | "fetched" | "incomplete" | "failed"}}``.

    A payload that cannot be validated against the published count is never
    stored: a half-downloaded set would look complete to every later run.
    """
    directory = Path(sets_dir) if sets_dir is not None else Path(CARD_DB_PATH).parent
    directory.mkdir(parents=True, exist_ok=True)
    index = read_sets_index(directory)
    metadata = set_index or {}
    if fetcher is None:
        fetcher = lambda code, timeout=timeout: fetch_set(code)  # noqa: E731

    status = {}
    fetched_any = False

    for code in codes:
        expected = (metadata.get(code) or {}).get("numberCards")
        path = directory / f"{code}.json"

        if path.exists() and not refresh:
            meta = index.get(code)
            if meta is None:
                # A cache written before the index existed: measure it instead of
                # trusting it, and repair it here if it turns out short.
                meta = completeness(json.loads(path.read_text(encoding="utf-8")), expected)
                meta["checked_at"] = datetime.now().isoformat()
                index[code] = meta
            if not is_incomplete(meta):
                status[code] = {"status": "cached", **meta}
                continue
            if recently_checked(meta):
                status[code] = {"status": "incomplete", **meta}
                continue

        try:
            data = fetcher(code, timeout=timeout)
        except (HTTPError, URLError, OSError) as exc:
            status[code] = {"status": "failed", "error": str(exc)}
            continue

        if not data or not data.get("data"):
            status[code] = {"status": "failed", "error": "empty payload"}
            continue

        result = completeness(data, expected)
        index[code] = {**result, "checked_at": datetime.now().isoformat()}
        if result["complete"] is False:
            status[code] = {"status": "incomplete", **result}
            continue

        store_set(code, data, directory)
        status[code] = {"status": "fetched", **result}
        fetched_any = True

    write_sets_index(index, directory)
    if fetched_any:
        # The rebuilt catalogue belongs next to the sets it was built from, not
        # to the global cache: a caller working in a temporary directory must not
        # overwrite the real one.
        rebuild_normalized(directory, out_path or (directory / "cards_normalized.json"))
    return status


def write_normalized(cards, out_path=None):
    """Write ``cards`` atomically so an interrupted rebuild cannot corrupt it."""
    target = Path(out_path) if out_path is not None else Path(CARD_DB_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(cards, handle, ensure_ascii=False, indent=2)
    os.replace(tmp, target)
    return target


def rebuild_normalized(sets_dir=None, out_path=None):
    """Rebuild the normalised catalogue from the cached raw set payloads.

    The raw per-set files are the cache of record; the normalised file is
    derived. When ``out_path`` is given the result is written, otherwise it is
    returned for inspection.
    """
    cards = normalize_cards(load_cached_sets(sets_dir))
    if out_path is not None:
        write_normalized(cards, out_path)
    return cards


def read_catalogue(sets_dir=None):
    """Read the set list recorded by the last `main` run."""
    directory = Path(sets_dir) if sets_dir is not None else Path(CARD_DB_PATH).parent
    path = directory / "catalogue.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_catalogue(base_sets, all_sets, sets_dir=None):
    """Record which sets the catalogue is supposed to contain."""
    directory = Path(sets_dir) if sets_dir is not None else Path(CARD_DB_PATH).parent
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "catalogue.json"
    data = {
        "checked_at": datetime.now().isoformat(),
        "base_sets": sorted(base_sets),
        "all_sets": sorted(all_sets),
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return path


def refresh_catalogue(sets_dir=None, timeout=60, fetcher=None):
    """Repair local gaps in the catalogue. Never raises, never invents sets.

    The set list comes from the last `main` run, so this does not discover new
    products on its own: it only downloads base sets that are missing or
    incomplete. With nothing missing it makes no network call at all.
    """
    directory = Path(sets_dir) if sets_dir is not None else Path(CARD_DB_PATH).parent
    catalogue = read_catalogue(directory)
    base_sets = catalogue.get("base_sets") or []
    if not base_sets:
        return {"status": "unknown", "fetched": [], "incomplete": [], "missing": []}

    complete = sc.complete_sets(directory)
    missing = [code for code in base_sets if code not in complete]
    if not missing:
        return {"status": "up-to-date", "fetched": [], "incomplete": [], "missing": []}

    # A set already checked and still short is not retried on every run: the
    # decision needs no request, so no request is made.
    local_index = read_sets_index(directory)
    due = [code for code in missing if not recently_checked(local_index.get(code))]
    if not due:
        return {
            "status": "partial",
            "fetched": [],
            "incomplete": missing,
            "missing": [],
        }

    try:
        index = fetch_set_index(timeout=timeout)
    except FetchError as exc:
        return {
            "status": "failed",
            "fetched": [],
            "incomplete": [],
            "missing": missing,
            "error": str(exc),
        }

    status = ensure_sets(
        missing, sets_dir=directory, set_index=index, fetcher=fetcher, timeout=timeout
    )
    fetched = [code for code, info in status.items() if info.get("status") == "fetched"]
    incomplete = [
        code for code, info in status.items() if info.get("status") == "incomplete"
    ]
    failed = [
        code
        for code, info in status.items()
        if info.get("status") not in {"fetched", "incomplete", "cached"}
    ]
    return {
        "status": "partial" if (incomplete or failed) else "refreshed",
        "fetched": fetched,
        "incomplete": incomplete,
        "missing": failed,
    }


def plan_lines(codes, index, directory, refresh=False):
    """Describe what a run would do, without touching anything."""
    complete = sc.complete_sets(directory)
    local = read_sets_index(directory)
    lines = [f"{len(codes)} set(s) selected"]
    if not local:
        lines.append("  (no sets_index.json: completeness of cached sets is unknown)")
    for code in codes:
        expected = (index.get(code) or {}).get("numberCards")
        exists = (directory / f"{code}.json").exists()
        if exists and not refresh and not is_incomplete(local.get(code)):
            state = "cached"
        elif exists and is_incomplete(local.get(code)) and not refresh:
            state = "incomplete"
        else:
            state = "fetch"
        lines.append(f"  {code:6} {state:11} expected {expected}")
    return lines


def write_meta(directory=None):
    """Record what the catalogue holds, so `db.data_as_of` stays honest."""
    directory = Path(directory) if directory is not None else Path(CARD_DB_PATH).parent
    normalized = directory / "cards_normalized.json"
    cards = json.loads(normalized.read_text(encoding="utf-8")) if normalized.exists() else {}
    local = read_sets_index(directory)
    sets = [code for code in cached_set_codes(directory) if not is_incomplete(local.get(code))]
    meta = {
        "fetched_at": datetime.now().isoformat(),
        "source": "api.swu-db.com",
        "sets": sets,
        "total_unique_cards": len(cards),
    }
    path = directory / "meta.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sets", help="comma separated set codes")
    parser.add_argument(
        "--all", action="store_true", help="every set listed by /sets, promos included"
    )
    parser.add_argument(
        "--base", action="store_true", help="only base sets (this is the default)"
    )
    parser.add_argument("--refresh", action="store_true", help="re-download cached sets")
    parser.add_argument("--dry-run", action="store_true", help="report, do not write")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args(argv)

    directory = Path(CARD_DB_PATH).parent
    try:
        index = fetch_set_index(timeout=args.timeout)
        codes = select_sets(index, sets=args.sets, include_all=args.all)
    except FetchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        for line in plan_lines(codes, index, directory, args.refresh):
            print(line)
        return 0

    print(f"Checking {len(codes)} set(s) against {API_BASE}...", file=sys.stderr)
    status = ensure_sets(
        codes,
        sets_dir=directory,
        set_index=index,
        refresh=args.refresh,
        timeout=args.timeout,
    )
    write_meta(directory)
    base_sets = sorted(code for code, meta in index.items() if meta.get("isBaseSet"))
    write_catalogue(base_sets, sorted(index), directory)

    for code in codes:
        info = status.get(code) or {}
        expected = (index.get(code) or {}).get("numberCards")
        state = info.get("status", "?")
        detail = ""
        if info.get("received") is not None:
            detail = f" ({info['received']}/{expected})"
        print(f"  {code:6} {state:11}{detail}", file=sys.stderr)

    failed = [code for code, info in status.items() if info.get("status") not in {"cached", "fetched"}]
    if failed:
        print(
            f"WARNING: {len(failed)} set(s) still missing or incomplete: "
            f"{', '.join(sorted(failed))}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

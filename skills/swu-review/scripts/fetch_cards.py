#!/usr/bin/env python3
"""
fetch_cards.py - Fetch and normalize card data from swu-db

Downloads Premier sets from https://api.swu-db.com/cards/{SET}
Normalizes to only VariantType == 'Normal', excludes tokens.
Deduplicates by name + subtitle identity.
"""

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

PREMIER_SETS = ["JTL", "LOF", "IBH", "SEC", "LAW", "ASH", "HMW"]
API_BASE = "https://api.swu-db.com"

# Canonical order for rebuilding the normalised catalogue. A card printed in
# several sets keeps the record of the last set in this order, so the order is
# part of the output: it must be explicit and stable, never the network's.
SET_ORDER = ("JTL", "LOF", "IBH", "SEC", "LAW", "ASH", "HMW")

# Files in the cache directory that are not per-set payloads.
NON_SET_FILES = {"cards_normalized", "meta", "sets_index"}


def fetch_set(set_code):
    """Fetch a set from swu-db API."""
    url = f"{API_BASE}/cards/{set_code}"
    print(f"Fetching {url}...", file=sys.stderr)
    
    req = Request(url, headers={"User-Agent": "edIAr-swu-decklab/0.1"})
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


def ensure_sets(codes, sets_dir=None, set_index=None, fetcher=None, out_path=None, timeout=60):
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
        cached = (directory / f"{code}.json").exists()
        if cached and not is_incomplete(index.get(code)):
            status[code] = {"status": "cached", **(index.get(code) or {})}
            continue

        expected = (metadata.get(code) or {}).get("numberCards")
        try:
            data = fetcher(code, timeout=timeout)
        except (HTTPError, URLError, OSError) as exc:
            status[code] = {"status": "failed", "error": str(exc)}
            continue

        if not data or not data.get("data"):
            status[code] = {"status": "failed", "error": "empty payload"}
            continue

        result = completeness(data, expected)
        index[code] = result
        if result["complete"] is False:
            status[code] = {"status": "incomplete", **result}
            continue

        store_set(code, data, directory)
        status[code] = {"status": "fetched", **result}
        fetched_any = True

    write_sets_index(index, directory)
    if fetched_any:
        rebuild_normalized(directory, out_path or C.CARD_DB_PATH)
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


def main():
    # CARD_DB_PATH = "data/swudb/cards_normalized.json" (from constants.py)
    # Ensure the parent directory exists
    swu_db_dir = Path(CARD_DB_PATH).parent
    swu_db_dir.mkdir(parents=True, exist_ok=True)
    
    print("Fetching Premier sets from swu-db...", file=sys.stderr)
    all_data = {}
    
    for set_code in PREMIER_SETS:
        data = fetch_set(set_code)
        if data:
            all_data[set_code] = data
            # Save raw set data
            set_file = Path(CARD_DB_PATH).parent / f"{set_code}.json"
            with open(set_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            print(f"  Saved {set_file} ({len(data.get('data', []))} rows)", file=sys.stderr)
    
    print("\nNormalizing cards...", file=sys.stderr)
    cards = normalize_cards(all_data)
    
    # Save normalized cards
    normalized_file = Path(CARD_DB_PATH)
    with open(normalized_file, 'w', encoding='utf-8') as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {normalized_file} ({len(cards)} unique cards)", file=sys.stderr)
    
    # Save metadata
    meta = {
        "fetched_at": datetime.now().isoformat(),
        "source": "api.swu-db.com",
        "sets": PREMIER_SETS,
        "total_unique_cards": len(cards)
    }
    meta_file = Path(CARD_DB_PATH).parent / "meta.json"
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    
    print(f"Saved {meta_file}", file=sys.stderr)
    print(f"\nDone! {len(cards)} unique Premier cards cached.", file=sys.stderr)


if __name__ == "__main__":
    main()

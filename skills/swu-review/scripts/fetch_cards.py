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

from .constants import CARD_DB_PATH

PREMIER_SETS = ["JTL", "LOF", "IBH", "SEC", "LAW", "ASH", "HMW"]
API_BASE = "https://api.swu-db.com"


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
            
            cards[key] = {
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

#!/usr/bin/env python3
"""Shared constants for the swu-review analysis pipeline.

Single source for values that were previously duplicated across scripts.
A follow-up refactor will make the existing scripts import from here too.
"""

SCHEMA_VERSION = "0.1.0"
TOOL_VERSION = "0.1.0-dev"
RULES_VERSION = "2026-10-26"

PREMIER_SETS = ("JTL", "LOF", "IBH", "SEC", "LAW", "ASH", "HMW")
SUSPENDED = frozenset()

DRAW_HAND = 6
DRAW_PER_REGROUP = 2
DRAW_MAX_ROUND = 6

PRICE_SOURCE = "swu-db"
PRICE_CURRENCY = "USD"

# Cardmarket (EUR). Public bulk downloads, no authentication.
CARDMARKET_GAME_ID = 21
CARDMARKET_BASE_URL = "https://downloads.s3.cardmarket.com/productCatalog"
CARDMARKET_CATALOG_FILE = f"products_singles_{CARDMARKET_GAME_ID}.json"
CARDMARKET_PRICE_FILE = f"price_guide_{CARDMARKET_GAME_ID}.json"
CARDMARKET_CACHE_DIR = "cm"
CARDMARKET_PRICE_SOURCE = "Cardmarket price guide"
CARDMARKET_PRICE_CURRENCY = "EUR"
CARDMARKET_PRICE_BASIS = "cheapest non-foil trend"

# Card DB path - shared between fetch_cards.py and analysis.py
CARD_DB_PATH = "data/swudb/cards_normalized.json"

# One Premier set maps to two Cardmarket expansions: the base set and "Extras".
CARDMARKET_SET_EXPANSIONS = {
    "JTL": (5995, 6074),
    "LOF": (6105, 6188),
    "SEC": (6333, 6364),
    "LAW": (6451, 6452),
    "ASH": (6591, 6642),
    "HMW": (6759, 6788),
    "IBH": (6268,),
}

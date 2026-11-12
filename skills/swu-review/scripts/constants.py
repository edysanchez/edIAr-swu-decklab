#!/usr/bin/env python3
"""Shared constants for the swu-review analysis pipeline.

Single source for values that were previously duplicated across scripts.
A follow-up refactor will make the existing scripts import from here too.
"""

SCHEMA_VERSION = "0.1.0"
TOOL_VERSION = "0.1.0-dev"
RULES_VERSION = "2026-11-09"

PREMIER_SETS = ("JTL", "LOF", "IBH", "SEC", "LAW", "ASH", "HMW")

# Premier suspended list.
#
# FFG publishes suspensions as individual announcements; there is no official
# machine-readable feed. The Comprehensive Event Guide lags behind them (v1.5,
# updated 2026-10-09, still says the Premier list is empty while Cad Bane had
# been announced on 2026-08-24), so every entry below cites the official
# announcement it comes from.
#
# Identities use the local (name, subtitle) key, so "same name, different
# subtitle" printings (e.g. the three Cad Banes) are not confused with each
# other. SWU Competitive Hub is kept only as a dated cross-check for the
# effective dates, never as the authority.
SUSPENDED_AS_OF = "2026-11-09"
SUSPENDED_SOURCES = (
    "https://starwarsunlimited.com/articles/premier-format-update-november-2026",
    "https://starwarsunlimited.com/articles/cad-banned",
)

# Operational source: the hub page is parsed into a local snapshot by
# ``fetch_suspended.py``. The snapshot wins over the registry when present;
# disagreements are surfaced as warnings so the registry can be updated.
SUSPENDED_HUB_URL = "https://www.swu-competitivehub.com/suspended-list/"
SUSPENDED_SNAPSHOT_PATH = "data/swu/suspended.json"
SUSPENDED_SNAPSHOT_MAX_AGE_DAYS = 45
SUSPENDED_CARDS = (
    {
        "identity": ("Cad Bane", "Still Faster Than You"),
        "set": "ASH",
        "number": "011",
        "type": "Leader",
        "announced": "2026-08-24",
        "source": "https://starwarsunlimited.com/articles/cad-banned",
    },
    {
        "identity": ("Chimaera", "A Frightening Reality"),
        "set": "ASH",
        "number": "052",
        "type": "Unit",
        "announced": "2026-11-09",
        "source": "https://starwarsunlimited.com/articles/premier-format-update-november-2026",
    },
    {
        "identity": ("Koska Reeves", "Warrior of Mandalore"),
        "set": "ASH",
        "number": "079",
        "type": "Unit",
        "announced": "2026-11-09",
        "source": "https://starwarsunlimited.com/articles/premier-format-update-november-2026",
    },
    {
        "identity": ("Neel", "The Cutest Boy"),
        "set": "ASH",
        "number": "248",
        "type": "Unit",
        "announced": "2026-11-09",
        "source": "https://starwarsunlimited.com/articles/premier-format-update-november-2026",
    },
    {
        "identity": ("Aggressive Negotiations", ""),
        "set": "SEC",
        "number": "179",
        "type": "Event",
        "announced": "2026-11-09",
        "source": "https://starwarsunlimited.com/articles/premier-format-update-november-2026",
    },
)
SUSPENDED = frozenset(record["identity"] for record in SUSPENDED_CARDS)

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

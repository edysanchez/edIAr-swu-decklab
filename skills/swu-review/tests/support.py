"""Shared test helpers."""

import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parents[1]
CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"

# The catalogue is a local, gitignored cache. Tests that exercise the real data
# cannot run without it, and must say so instead of failing with a traceback.
requires_catalogue = unittest.skipUnless(
    CARD_DB.exists(),
    "local catalogue missing: run fetch_cards.py to create data/swudb/cards_normalized.json",
)

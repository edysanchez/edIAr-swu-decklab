"""Shared test helpers."""

import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
REPO_ROOT = SKILL_DIR.parents[1]

# Real, gitignored catalogue.
CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"

# Checked-in synthetic catalogue: no card text, images or real card data.
SYNTHETIC_DIR = TESTS_DIR / "fixtures" / "synthetic"
SYNTHETIC_CARD_DB = SYNTHETIC_DIR / "cards.json"
SYNTHETIC_DECK = SYNTHETIC_DIR / "deck.json"
SYNTHETIC_ROTATED_DECK = SYNTHETIC_DIR / "deck_rotated.json"
SYNTHETIC_CASE_DECK = SYNTHETIC_DIR / "deck_case.json"
SYNTHETIC_TEXT_DECK = SYNTHETIC_DIR / "deck.txt"

# Tests that exercise the real catalogue skip in a clean checkout.
requires_catalogue = unittest.skipUnless(
    CARD_DB.exists(),
    "local catalogue missing: run fetch_cards.py to create data/swudb/cards_normalized.json",
)

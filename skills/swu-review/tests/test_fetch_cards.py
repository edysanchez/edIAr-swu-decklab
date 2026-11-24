#!/usr/bin/env python3
"""The fetch script must stay importable and use the shared catalogue path."""

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import fetch_cards  # noqa: E402


class FetchCardsTest(unittest.TestCase):
    def test_uses_the_shared_catalogue_path(self):
        self.assertEqual(fetch_cards.CARD_DB_PATH, "data/swudb/cards_normalized.json")

    def test_normalizes_normal_variants_and_deduplicates(self):
        data = {
            "JTL": {
                "data": [
                    {
                        "Name": "Synthetic Card",
                        "Subtitle": "Test",
                        "VariantType": "Normal",
                        "Type": "Unit",
                        "Set": "JTL",
                        "Number": "1",
                    },
                    {
                        "Name": "Synthetic Card",
                        "Subtitle": "Test",
                        "VariantType": "Normal",
                        "Type": "Unit",
                        "Set": "JTL",
                        "Number": "2",
                    },
                    {
                        "Name": "Foil Only",
                        "Subtitle": "",
                        "VariantType": "Foil",
                        "Type": "Unit",
                    },
                    {
                        "Name": "Token",
                        "Subtitle": "",
                        "VariantType": "Normal",
                        "Type": "Token Unit",
                    },
                ]
            }
        }

        cards = fetch_cards.normalize_cards(data)

        self.assertEqual(list(cards), ["Synthetic Card|Test"])
        self.assertEqual(cards["Synthetic Card|Test"]["number"], "2")

#!/usr/bin/env python3
"""Tests for the Cardmarket (EUR) price source.

Run with:

    python3 -m unittest discover -s skills/swu-review/tests -v

The fixtures are synthetic: no network access and no dependency on the local
``data/cm/`` cache, so the suite is deterministic on any machine.
"""

import sys
import unittest
from decimal import Decimal
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
REPO_ROOT = SKILL_DIR.parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import cardmarket  # noqa: E402  (fails first: RED)

FIXTURES_DIR = TESTS_DIR / "fixtures"
CASE = FIXTURES_DIR / "poggle-blue-endor" / "deck.json"
CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"
SCHEMA_PATH = SKILL_DIR / "analysis.schema.json"
FIXED_TIME = "2026-11-03T00:00:00Z"

CATALOG = {
    "version": 1,
    "createdAt": "2026-11-04T13:23:48+0100",
    "products": [
        # Same metacard (100) in the base and the "Extras" expansion.
        {"idProduct": 1, "name": "Yoda, My Ally is the Force",
         "idCategory": 1644, "idExpansion": 6105, "idMetacard": 100},
        # Hyperspace printing: also non-foil, more expensive.
        {"idProduct": 2, "name": "Yoda, My Ally is the Force",
         "idCategory": 1644, "idExpansion": 6105, "idMetacard": 100},
        # Foil-only printing: must never win the "cheapest non-foil" rule.
        {"idProduct": 3, "name": "Yoda, My Ally is the Force",
         "idCategory": 1644, "idExpansion": 6188, "idMetacard": 100},
        # Bases are sold as "<base> // <token>", four token variants.
        {"idProduct": 4, "name": "Chopper Base // Shield Token",
         "idCategory": 1644, "idExpansion": 5995, "idMetacard": 200},
        {"idProduct": 5, "name": "Chopper Base // X-Wing Token",
         "idCategory": 1644, "idExpansion": 5995, "idMetacard": 201},
        # Same name, different set: must not match LOF.
        {"idProduct": 6, "name": "Yoda, My Ally is the Force",
         "idCategory": 1644, "idExpansion": 9999, "idMetacard": 300},
    ],
}

PRICES = {
    "version": 1,
    "createdAt": "2026-11-05T02:50:26+0100",
    "priceGuides": [
        {"idProduct": 1, "avg": 5.35, "low": 3.0, "trend": 4.44},
        {"idProduct": 2, "avg": 7.63, "low": 9.95, "trend": 10.64},
        {"idProduct": 3, "avg": None, "low": None, "trend": 0,
         "avg-foil": None, "low-foil": None, "trend-foil": 10.53},
        {"idProduct": 4, "avg": 0.14, "low": 0.05, "trend": 0.12},
        {"idProduct": 5, "avg": 0.11, "low": 0.04, "trend": 0.09},
        {"idProduct": 6, "avg": 80.0, "low": 70.0, "trend": 99.0},
    ],
}

SET_EXPANSIONS = {"LOF": [6105, 6188], "JTL": [5995]}

CARD_DB_MIN = {
    ("Yoda", "My Ally is the Force"): {"set": "LOF", "type": "Unit"},
    ("Chopper Base", "Atollon"): {"set": "JTL", "type": "Base"},
}


def index():
    return cardmarket.CardmarketIndex(CATALOG, PRICES, SET_EXPANSIONS)


class NormalizeTest(unittest.TestCase):
    def test_ignores_case_punctuation_and_accents(self):
        self.assertEqual(
            cardmarket.normalize("Yoda’s Lightsaber – Édition"),
            cardmarket.normalize("yodas lightsaber edition"),
        )


class QuoteTest(unittest.TestCase):
    def test_returns_cheapest_non_foil_trend(self):
        quote = index().quote("LOF", "Yoda", "My Ally is the Force")
        self.assertEqual(quote["trend"], 4.44)
        self.assertEqual(quote["low"], 3.0)
        self.assertEqual(quote["id_product"], 1)

    def test_foil_only_printing_is_ignored(self):
        quote = index().quote("LOF", "Yoda", "My Ally is the Force")
        self.assertNotEqual(quote["id_product"], 3)

    def test_does_not_mix_sets(self):
        quote = index().quote("LOF", "Yoda", "My Ally is the Force")
        self.assertNotEqual(quote["trend"], 99.0)

    def test_base_matches_double_sided_token_products(self):
        quote = index().quote("JTL", "Chopper Base", "Atollon", "Base")
        self.assertEqual(quote["trend"], 0.09)
        self.assertEqual(quote["id_product"], 5)

    def test_base_also_matches_a_plain_name_product(self):
        catalog = {
            "products": [
                {"idProduct": 10, "name": "Colossus", "idExpansion": 5995,
                 "idMetacard": 400},
            ],
            "createdAt": "2026-11-04T13:23:48+0100",
        }
        prices = {
            "priceGuides": [{"idProduct": 10, "trend": 0.21, "low": 0.02}],
            "createdAt": "2026-11-05T02:50:26+0100",
        }
        idx = cardmarket.CardmarketIndex(catalog, prices, SET_EXPANSIONS)
        quote = idx.quote("JTL", "Colossus", "Castilon", "Base")
        self.assertEqual(quote["trend"], 0.21)
        self.assertEqual(quote["id_product"], 10)

    def test_unknown_card_returns_none(self):
        self.assertIsNone(index().quote("LOF", "Darth Vader", "Might of the Empire"))

    def test_empty_quotes_are_not_reported(self):
        catalog = {
            "products": [
                {"idProduct": 9, "name": "No Price", "idExpansion": 6105,
                 "idMetacard": 900},
            ],
            "createdAt": "2026-11-04T13:23:48+0100",
        }
        prices = {"priceGuides": [{"idProduct": 9, "trend": 0}],
                  "createdAt": "2026-11-05T02:50:26+0100"}
        idx = cardmarket.CardmarketIndex(catalog, prices, SET_EXPANSIONS)
        self.assertIsNone(idx.quote("LOF", "No Price"))


class SnapshotTest(unittest.TestCase):
    def test_snapshot_is_the_price_guide_date(self):
        self.assertEqual(index().snapshot, "2026-11-05")


class DeckPriceTest(unittest.TestCase):
    def test_totals_copies_and_reports_coverage(self):
        result = index().price_deck(
            {
                ("Yoda", "My Ally is the Force"): 2,
                ("Chopper Base", "Atollon"): 1,
            },
            CARD_DB_MIN,
        )
        self.assertEqual(result["currency"], "EUR")
        self.assertEqual(result["total"], 8.97)
        self.assertEqual(result["priced_slots"], 3)
        self.assertEqual(result["coverage_pct"], 100.0)
        self.assertEqual(result["source"], "Cardmarket price guide")
        self.assertEqual(result["snapshot"], "2026-11-05")
        self.assertEqual(result["basis"], "cheapest non-foil trend")

    def test_unpriced_cards_lower_coverage_without_breaking_total(self):
        result = index().price_deck(
            {
                ("Yoda", "My Ally is the Force"): 1,
                ("Missing", ""): 1,
            },
            {
                ("Yoda", "My Ally is the Force"): {"set": "LOF", "type": "Unit"},
                ("Missing", ""): {"set": "LOF", "type": "Unit"},
            },
        )
        self.assertEqual(result["total"], 4.44)
        self.assertEqual(result["priced_slots"], 1)
        self.assertEqual(result["coverage_pct"], 50.0)


class LoadIndexTest(unittest.TestCase):
    def test_returns_none_when_cache_is_absent(self):
        self.assertIsNone(cardmarket.load_index(Path("/nonexistent/cm")))


class FetchScriptTest(unittest.TestCase):
    def test_writes_a_cache_that_load_index_can_read(self):
        import tempfile
        from unittest import mock

        import fetch_prices_cm

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                fetch_prices_cm, "fetch_json", side_effect=[CATALOG, PRICES]
            ):
                summary = fetch_prices_cm.fetch_prices(tmp)

            self.assertEqual(summary["products"], len(CATALOG["products"]))
            self.assertEqual(summary["quotes"], len(PRICES["priceGuides"]))
            self.assertEqual(summary["price_snapshot"], "2026-11-05")

            loaded = cardmarket.load_index(tmp)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.snapshot, "2026-11-05")
            self.assertEqual(
                loaded.quote("LOF", "Yoda", "My Ally is the Force")["trend"],
                4.44,
            )


class AnalysisIntegrationTest(unittest.TestCase):
    def build(self, cm_index):
        import analysis

        return analysis.build_analysis(
            CASE,
            card_db_path=CARD_DB,
            generated_at=FIXED_TIME,
            cm_index=cm_index,
        )

    def test_price_eur_block_is_added_when_index_is_given(self):
        out = self.build(index())
        block = out["composition"]["price_eur"]
        self.assertEqual(block["currency"], "EUR")
        self.assertEqual(block["source"], "Cardmarket price guide")
        self.assertEqual(block["snapshot"], "2026-11-05")
        self.assertEqual(block["priced_slots"], 0)

    def test_no_price_eur_block_without_index(self):
        out = self.build(None)
        self.assertNotIn("price_eur", out["composition"])

    def test_schema_accepts_price_eur(self):
        import json

        import jsonschema

        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=self.build(index()), schema=schema)


if __name__ == "__main__":
    unittest.main()

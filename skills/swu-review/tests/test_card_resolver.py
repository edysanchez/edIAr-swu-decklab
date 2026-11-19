#!/usr/bin/env python3
"""Regression tests for strict card resolution."""

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
from support import SYNTHETIC_CARD_DB  # noqa: E402

SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import swu_cards as sc  # noqa: E402
from card_resolver import CardIndex, UnresolvedCard  # noqa: E402


class CardResolverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sc.load_swu_cards(SYNTHETIC_CARD_DB)
        cls.index = CardIndex(cls.db)

    def test_padded_unpadded_and_lowercase_ids_resolve_to_same_identity(self):
        padded = self.index.resolve({"id": "HMW_001"})
        unpadded = self.index.resolve({"id": "HMW_1"})
        lowercase = self.index.resolve({"id": "hmw_1"})

        self.assertEqual(padded.key, unpadded.key)
        self.assertEqual(padded.key, lowercase.key)
        self.assertEqual(padded.key, ("Synthetic Unit 01", ""))
        self.assertEqual(padded.resolved_by, "id")

    def test_one_digit_numbers_are_normalised(self):
        by_short = self.index.resolve({"id": "HMW_1"})
        by_padded = self.index.resolve({"id": "HMW_001"})
        self.assertEqual(by_short.key, by_padded.key)

    def test_base_with_empty_subtitle_falls_back_to_unique_name(self):
        resolved = self.index.resolve({"name": "Synthetic Base", "subtitle": ""})
        self.assertEqual(resolved.key, ("Synthetic Base", "Endor"))
        self.assertEqual(resolved.resolved_by, "name")

    def test_set_and_number_resolves_before_name_fallback(self):
        resolved = self.index.resolve({
            "name": "Synthetic Base",
            "subtitle": "",
            "set": "HMW",
            "number": 899,
        })
        self.assertEqual(resolved.key, ("Synthetic Base", "Endor"))
        self.assertEqual(resolved.resolved_by, "set_number")

    def test_unknown_card_raises(self):
        with self.assertRaises(UnresolvedCard) as ctx:
            self.index.resolve({"name": "Totally Fake Card"})
        self.assertEqual(ctx.exception.reason, "no matching card in database")

    def test_set_number_mismatch_raises(self):
        with self.assertRaises(UnresolvedCard) as ctx:
            self.index.resolve({
                "name": "Synthetic Unit 01",
                "set": "HMW",
                "number": 899,
            })
        self.assertIn("points to", ctx.exception.reason)

    def test_ambiguous_name_raises(self):
        ambiguous = next(
            name for name, keys in self.index.by_name.items()
            if len(keys) > 1 and all(subtitle for _, subtitle in keys)
        )
        with self.assertRaises(UnresolvedCard) as ctx:
            self.index.resolve({"name": ambiguous, "subtitle": ""})
        self.assertIn("ambiguous", ctx.exception.reason)

    def test_explicit_key_resolves(self):
        resolved = self.index.resolve({"key": ["Synthetic Unit 01", ""]})
        self.assertEqual(resolved.key, ("Synthetic Unit 01", ""))
        self.assertEqual(resolved.resolved_by, "key")


if __name__ == "__main__":
    unittest.main()

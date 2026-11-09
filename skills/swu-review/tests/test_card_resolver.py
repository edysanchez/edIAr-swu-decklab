#!/usr/bin/env python3
"""Regression tests for strict card resolution."""

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
REPO_ROOT = SKILL_DIR.parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import swu_cards as sc  # noqa: E402
from card_resolver import CardIndex, UnresolvedCard  # noqa: E402

CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"


class CardResolverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sc.load_swu_cards(CARD_DB)
        cls.index = CardIndex(cls.db)

    def test_padded_unpadded_and_lowercase_ids_resolve_to_same_identity(self):
        padded = self.index.resolve({"id": "ASH_032"})
        unpadded = self.index.resolve({"id": "ASH_32"})
        lowercase = self.index.resolve({"id": "ash_32"})

        self.assertEqual(padded.key, unpadded.key)
        self.assertEqual(padded.key, lowercase.key)
        self.assertEqual(padded.key, ("Rancor Keeper", ""))
        self.assertEqual(padded.resolved_by, "id")

    def test_one_digit_numbers_are_normalised(self):
        card = next(
            c for c in self.db.values()
            if c.get("set") == "IBH" and str(c.get("number", "")).isdigit()
            and len(str(c["number"])) == 1
        )
        number = card["number"]
        by_short = self.index.resolve({"id": f"IBH_{number}"})
        by_padded = self.index.resolve({"id": f"IBH_{int(number):03d}"})
        self.assertEqual(by_short.key, by_padded.key)

    def test_base_with_empty_subtitle_falls_back_to_unique_name(self):
        resolved = self.index.resolve({"name": "Shield Generator Complex", "subtitle": ""})
        self.assertEqual(resolved.key, ("Shield Generator Complex", "Endor"))
        self.assertEqual(resolved.resolved_by, "name")

    def test_set_and_number_resolves_before_name_fallback(self):
        resolved = self.index.resolve({
            "name": "Shield Generator Complex",
            "subtitle": "",
            "set": "HMW",
            "number": 22,
        })
        self.assertEqual(resolved.key, ("Shield Generator Complex", "Endor"))
        self.assertEqual(resolved.resolved_by, "set_number")

    def test_unknown_card_raises(self):
        with self.assertRaises(UnresolvedCard) as ctx:
            self.index.resolve({"name": "Totally Fake Card"})
        self.assertEqual(ctx.exception.reason, "no matching card in database")

    def test_set_number_mismatch_raises(self):
        with self.assertRaises(UnresolvedCard) as ctx:
            self.index.resolve({
                "name": "Rancor Keeper",
                "set": "HMW",
                "number": 22,
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
        resolved = self.index.resolve({"key": ["Rancor Keeper", ""]})
        self.assertEqual(resolved.key, ("Rancor Keeper", ""))
        self.assertEqual(resolved.resolved_by, "key")


if __name__ == "__main__":
    unittest.main()

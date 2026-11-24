#!/usr/bin/env python3
"""Validator and analysis flags must use the same icon multiplicity."""

import sys
import unittest
from collections import Counter
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SKILL_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

import analysis  # noqa: E402
import validate_deck  # noqa: E402

DOUBLE = ("Synthetic Double Aspect", "")
LEADER = ("Synthetic Leader", "Prime")
BASE = ("Synthetic Base", "Endor")

CARD_DB = {
    LEADER: {"aspects": ["Aggression", "Villainy"], "type": "Leader"},
    BASE: {"aspects": ["Vigilance"], "type": "Base"},
    DOUBLE: {
        "name": "Synthetic Double Aspect",
        "subtitle": "",
        "set": "HMW",
        "number": "19",
        "type": "Unit",
        "aspects": ["Aggression", "Aggression"],
        "arenas": ["Ground"],
        "cost": "2",
        "power": "2",
        "hp": "2",
        "keywords": [],
        "traits": ["TEST"],
        "unique": False,
        "rarity": "Common",
        "frontText": None,
        "epicAction": None,
        "doubleSided": False,
        "marketPriceUsd": "1.00",
    },
}


class AspectPenaltyValidationTest(unittest.TestCase):
    def test_validator_counts_duplicate_icons(self):
        total, maximum = validate_deck.calculate_aspect_penalty(
            LEADER, BASE, {DOUBLE: 3}, CARD_DB
        )
        self.assertEqual(total, 6)
        self.assertEqual(maximum, 2)

    def test_analysis_off_aspect_flag_counts_duplicate_icons(self):
        card = CARD_DB[DOUBLE]
        one_source = analysis._sheet(
            DOUBLE, card, "main", 1, Counter({"Aggression": 1})
        )
        two_sources = analysis._sheet(
            DOUBLE, card, "main", 1, Counter({"Aggression": 2})
        )
        self.assertTrue(one_source["flags"]["off_aspect"])
        self.assertFalse(two_sources["flags"]["off_aspect"])


if __name__ == "__main__":
    unittest.main()

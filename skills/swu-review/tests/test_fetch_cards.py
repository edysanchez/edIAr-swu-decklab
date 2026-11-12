#!/usr/bin/env python3
"""`fetch_cards.normalize_cards` must not lose printings.

The card database keeps one entry per printed name + subtitle, but `rules.md`
says legality follows the card version: a reprint in a Premier-legal product
legalises the card. Collapsing two printings onto one identity without recording
them makes that rule impossible to apply.

These tests feed synthetic API rows, so they never touch the network.
"""

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import fetch_cards  # noqa: E402
import swu_cards as sc  # noqa: E402


def row(set_code, number, name="Adept ARC-170", subtitle="", **overrides):
    data = {
        "Name": name,
        "Subtitle": subtitle,
        "Set": set_code,
        "Number": number,
        "Type": "Unit",
        "VariantType": "Normal",
        "Aspects": ["Command"],
    }
    data.update(overrides)
    return data


class NormalizePrintingsTest(unittest.TestCase):
    def test_single_printing_does_not_ship_a_printings_field(self):
        cards = fetch_cards.normalize_cards({"JTL": {"data": [row("JTL", "114")]}})

        card = cards["Adept ARC-170"]
        self.assertEqual(card["set"], "JTL")
        self.assertNotIn("printings", card)

    def test_duplicate_identity_keeps_every_printing(self):
        cards = fetch_cards.normalize_cards(
            {
                "JTL": {"data": [row("JTL", "114")]},
                "HMW": {"data": [row("HMW", "177")]},
            }
        )

        card = cards["Adept ARC-170"]
        self.assertEqual(card["printings"], ["JTL", "HMW"])
        self.assertEqual(card["set"], "HMW")  # last fetched wins for display

    def test_repeated_printing_is_not_duplicated(self):
        cards = fetch_cards.normalize_cards(
            {
                "JTL": {"data": [row("JTL", "114")]},
                "HMW": {"data": [row("HMW", "177")]},
            }
        )

        self.assertEqual(cards["Adept ARC-170"]["printings"], ["JTL", "HMW"])
        self.assertEqual(len(cards["Adept ARC-170"]["printings"]), 2)

    def test_tokens_and_variants_are_excluded(self):
        cards = fetch_cards.normalize_cards(
            {
                "JTL": {
                    "data": [
                        row("JTL", "001", name="Token Unit", Type="Token Unit"),
                        row("JTL", "002", name="Foil Only", VariantType="Foil"),
                        row("JTL", "003", name="Kept"),
                    ]
                }
            }
        )

        self.assertEqual(sorted(cards), ["Kept"])


class CardPrintingsTest(unittest.TestCase):
    def test_printings_field_wins(self):
        card = {"set": "HMW", "printings": ["JTL", "HMW"]}
        self.assertEqual(sc.card_printings(card), ["JTL", "HMW"])

    def test_falls_back_to_set(self):
        self.assertEqual(sc.card_printings({"set": "JTL"}), ["JTL"])

    def test_empty_when_unknown(self):
        self.assertEqual(sc.card_printings({}), [])


if __name__ == "__main__":
    unittest.main()

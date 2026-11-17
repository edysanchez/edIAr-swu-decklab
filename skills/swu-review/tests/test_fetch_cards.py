#!/usr/bin/env python3
"""`fetch_cards.normalize_cards` must not lose printings.

The card database keeps one entry per printed name + subtitle, but `rules.md`
says legality follows the card version: a reprint in a Premier-legal product
legalises the card. Collapsing two printings onto one identity without recording
them makes that rule impossible to apply.

These tests feed synthetic API rows, so they never touch the network.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import constants as C  # noqa: E402
import fetch_cards  # noqa: E402
import swu_cards as sc  # noqa: E402

SWUDB_DIR = Path(C.CARD_DB_PATH).parent
CACHED_SETS = ["JTL", "LOF", "IBH", "SEC", "LAW", "ASH", "HMW"]


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


class RebuildTest(unittest.TestCase):
    """Rebuilding from the raw set files must not change the catalogue.

    The normalised file is a derived artefact: `cards_normalized.json` should
    always be reproducible from the per-set payloads the fetcher stores. This is
    the guard that lets the fetch flow be reworked without moving every other
    test.
    """

    def setUp(self):
        missing = [
            code for code in CACHED_SETS if not (SWUDB_DIR / f"{code}.json").exists()
        ]
        if missing:
            self.skipTest(f"raw set files not cached: {missing}")

    def test_rebuild_reproduces_the_cached_normalized_file(self):
        rebuilt = fetch_cards.rebuild_normalized()

        current = json.loads(
            (SWUDB_DIR / "cards_normalized.json").read_text(encoding="utf-8")
        )

        self.assertEqual(rebuilt, current)

    def test_rebuild_is_deterministic(self):
        self.assertEqual(fetch_cards.rebuild_normalized(), fetch_cards.rebuild_normalized())


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


def payload(numbers, set_code="IC27"):
    return {
        "total_cards": len(numbers),
        "data": [
            {
                "Name": f"Card {number}",
                "Subtitle": "",
                "Set": set_code,
                "Number": number,
                "Type": "Unit",
                "VariantType": "Normal",
            }
            for number in numbers
        ],
    }


INDEX = {
    "JTL": {"setId": "JTL", "numberCards": 2},
    "IC27": {"setId": "IC27", "numberCards": 3},
}


class EnsureSetsTest(unittest.TestCase):
    """Download only what is missing, and never trust a partial payload."""

    def setUp(self):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.dir = Path(handle.name)
        self.out = self.dir / "cards_normalized.json"

    def write_set(self, code, numbers, set_code=None):
        path = self.dir / f"{code}.json"
        path.write_text(json.dumps(payload(numbers, set_code or code)), encoding="utf-8")
        return path

    def write_index(self, data):
        (self.dir / "sets_index.json").write_text(json.dumps(data), encoding="utf-8")

    def run_ensure(self, codes, fetcher):
        return fetch_cards.ensure_sets(
            codes,
            sets_dir=self.dir,
            set_index=INDEX,
            fetcher=fetcher,
            out_path=self.out,
        )

    def test_downloads_only_the_missing_set(self):
        self.write_set("JTL", ["001", "002"])
        self.write_index({"JTL": {"expected": 2, "received": 2, "complete": True}})
        calls = []

        def fetcher(code, timeout=60):
            calls.append(code)
            return payload(["001", "002", "003"])

        status = self.run_ensure(["JTL", "IC27"], fetcher)

        self.assertEqual(calls, ["IC27"])
        self.assertEqual(status["JTL"]["status"], "cached")
        self.assertEqual(status["IC27"]["status"], "fetched")
        self.assertTrue((self.dir / "IC27.json").exists())

    def test_incomplete_payload_is_not_stored(self):
        def fetcher(code, timeout=60):
            return payload(["001", "002"])  # 2 of 3

        status = self.run_ensure(["IC27"], fetcher)

        self.assertEqual(status["IC27"]["status"], "incomplete")
        self.assertFalse((self.dir / "IC27.json").exists())

    def test_failed_download_leaves_the_set_absent(self):
        def fetcher(code, timeout=60):
            raise OSError("network down")

        status = self.run_ensure(["IC27"], fetcher)

        self.assertEqual(status["IC27"]["status"], "failed")
        self.assertFalse((self.dir / "IC27.json").exists())

    def test_sets_index_records_completeness(self):
        def fetcher(code, timeout=60):
            return payload(["001", "002", "003"])

        self.run_ensure(["IC27"], fetcher)

        index = json.loads((self.dir / "sets_index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["IC27"]["expected"], 3)
        self.assertEqual(index["IC27"]["received"], 3)
        self.assertTrue(index["IC27"]["complete"])

    def test_rebuild_skips_sets_marked_incomplete(self):
        self.write_set("JTL", ["001", "002"])
        self.write_set("IC27", ["001", "002"])
        self.write_index(
            {
                "JTL": {"expected": 2, "received": 2, "complete": True},
                "IC27": {"expected": 3, "received": 2, "complete": False},
            }
        )

        cards = fetch_cards.rebuild_normalized(sets_dir=self.dir)

        self.assertIn("Card 001", cards)
        self.assertEqual(cards["Card 001"]["set"], "JTL")

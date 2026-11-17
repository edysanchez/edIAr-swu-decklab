#!/usr/bin/env python3
"""Query tool over the local catalogue.

The rules under test are the filters, not the dataset: every case runs on a
hand-built card database, so the suite never depends on what is cached.
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import search_cards  # noqa: E402
import swu_cards as sc  # noqa: E402


def card(name, subtitle="", **overrides):
    data = {
        "name": name,
        "subtitle": subtitle,
        "set": "HMW",
        "number": "001",
        "type": "Unit",
        "cost": "2",
        "aspects": ["Vigilance"],
        "arenas": ["Ground"],
        "traits": ["TROOPER"],
        "keywords": [],
        "rarity": "Common",
        "unique": False,
        "frontText": "When Played: draw a card.",
    }
    data.update(overrides)
    return data


CARDS = {
    ("Cheap Trooper", ""): card("Cheap Trooper", cost="1", aspects=["Vigilance"]),
    ("Space Raider", ""): card(
        "Space Raider",
        cost="3",
        aspects=["Aggression", "Villainy"],
        arenas=["Space"],
        frontText="On Attack: deal 1 damage.",
    ),
    ("Big Event", ""): card(
        "Big Event", cost="6", type="Event", arenas=[], frontText="Deal 4 damage."
    ),
    ("No Cost", ""): card("No Cost", cost=None, frontText="Nothing to pay."),
    ("Free Base", "Endor"): card(
        "Free Base",
        "Endor",
        type="Base",
        cost=None,
        arenas=[],
        aspects=["Command"],
        frontText="",
    ),
    ("Old Printing", ""): card("Old Printing", set="SOR"),
}


class FilterTest(unittest.TestCase):
    def names(self, **kwargs):
        return [item["name"] for item in search_cards.search(CARDS, search_cards.Filters(**kwargs))]

    def test_no_filter_returns_everything_sorted_by_cost(self):
        self.assertEqual(
            self.names(),
            ["Cheap Trooper", "Old Printing", "Space Raider", "Big Event", "Free Base", "No Cost"],
        )

    def test_aspect_filter(self):
        self.assertEqual(self.names(aspects=("villainy",)), ["Space Raider"])

    def test_type_and_arena_filter(self):
        self.assertEqual(self.names(types=("Unit",), arena="space"), ["Space Raider"])

    def test_cost_range_excludes_cards_without_cost(self):
        self.assertEqual(self.names(cost_max=2), ["Cheap Trooper", "Old Printing"])

    def test_text_filter(self):
        self.assertEqual(self.names(text="WHEN PLAYED"), ["Cheap Trooper", "Old Printing"])

    def test_set_filter(self):
        self.assertEqual(self.names(sets=("sor",)), ["Old Printing"])

    def test_set_filter_sees_every_printing(self):
        cards = {
            ("Reprinted", ""): card(
                "Reprinted",
                set="SOR",
                printings=[
                    {"set": "JTL", "number": "258"},
                    {"set": "SOR", "number": "250"},
                ],
            )
        }

        found = search_cards.search(cards, search_cards.Filters(sets=("JTL",)))

        self.assertEqual([item["name"] for item in found], ["Reprinted"])

    def test_unique_filter(self):
        self.assertEqual(self.names(unique=True), [])

    def test_no_matches(self):
        self.assertEqual(self.names(name="nothing"), [])

    def test_legal_filter_uses_printings(self):
        class OnlyHMW:
            def is_legal_any(self, printings, on=None):
                return any(code in {"HMW", "SOR"} for code in printings)

        filters = search_cards.Filters(legal=OnlyHMW())
        found = search_cards.search(CARDS, filters)

        self.assertIn("Old Printing", [item["name"] for item in found])
        self.assertEqual(len(found), len(CARDS))

    def test_illegal_card_is_excluded(self):
        class Nothing:
            def is_legal_any(self, printings, on=None):
                return False

        self.assertEqual(search_cards.search(CARDS, search_cards.Filters(legal=Nothing())), [])

    def test_row_shape(self):
        item = search_cards.search(CARDS, search_cards.Filters(name="Cheap"))[0]

        self.assertEqual(item["identity"], "Cheap Trooper")
        self.assertEqual(item["cost"], 1)
        self.assertEqual(item["aspects"], ["Vigilance"])
        self.assertIn("When Played", item["text"])


class MainTest(unittest.TestCase):
    def setUp(self):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.path = Path(handle.name) / "cards_normalized.json"
        payload = {
            (key[0] if not key[1] else f"{key[0]}|{key[1]}"): value
            for key, value in CARDS.items()
        }
        self.path.write_text(json.dumps(payload), encoding="utf-8")

    def run_cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out), mock.patch("sys.stderr", io.StringIO()):
            code = search_cards.main(["--card-db", str(self.path), *args])
        return code, out.getvalue()

    def test_json_output(self):
        code, out = self.run_cli("--json", "--type", "Unit")

        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(all(item["type"] == "Unit" for item in data))
        self.assertTrue(data)

    def test_table_output(self):
        code, out = self.run_cli("--name", "Cheap")

        self.assertEqual(code, 0)
        self.assertIn("Cheap Trooper", out)
        self.assertIn("1 card(s)", out)

    def test_limit_keeps_the_first_matches(self):
        code, out = self.run_cli("--json", "--limit", "1")

        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out)), 1)

    def test_missing_database_is_an_error(self):
        with mock.patch("sys.stderr", io.StringIO()):
            code = search_cards.main(["--card-db", str(self.path.with_name("nope.json"))])

        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

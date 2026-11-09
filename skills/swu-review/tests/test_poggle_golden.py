#!/usr/bin/env python3
"""Golden tests for the Poggle Blue Endor case.

These tests pin the card-analysis contract before the implementation exists.
Run with:

    python3 -m unittest discover -s skills/swu-review/tests -v
"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
REPO_ROOT = SKILL_DIR.parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import analysis  # noqa: E402  (fails first: RED)

FIXTURES_DIR = TESTS_DIR / "fixtures"
CASE = FIXTURES_DIR / "poggle-blue-endor" / "deck.json"
CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"
SCHEMA_PATH = SKILL_DIR / "analysis.schema.json"
REGISTRY_PATH = SKILL_DIR / "reference" / "findings.md"

FIXED_TIME = "2026-11-03T00:00:00Z"


def build():
    return analysis.build_analysis(
        CASE,
        card_db_path=CARD_DB,
        generated_at=FIXED_TIME,
    )


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_with_fake_card():
    with open(CASE, "r", encoding="utf-8") as f:
        deck = json.load(f)

    fake = copy.deepcopy(deck["mainDeck"][0])
    fake["card"]["title"] = "Totally Fake Card"
    fake["card"]["subtitle"] = ""
    fake["card"]["cardNumber"] = 999
    fake["card"]["expansion"]["code"] = "HMW"
    deck["mainDeck"].append(fake)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fake.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(deck, f)
        return analysis.build_analysis(
            path,
            card_db_path=CARD_DB,
            generated_at=FIXED_TIME,
        )


class PoggleGoldenTest(unittest.TestCase):
    def test_composition_matches_case_readme(self):
        out = build()
        comp = out["composition"]

        self.assertEqual(comp["n"], 50)
        self.assertEqual(
            comp["curve"],
            {"1": 2, "2": 18, "3": 12, "4": 8, "5": 6, "6": 2, "7": 2},
        )
        self.assertEqual(
            comp["curve_pct"],
            {"1": 4.0, "2": 36.0, "3": 24.0, "4": 16.0, "5": 12.0, "6": 4.0, "7": 4.0},
        )
        self.assertEqual(comp["types"], {"Unit": 39, "Event": 9, "Upgrade": 2})
        self.assertEqual(comp["arenas"]["ground"], 37)
        self.assertEqual(comp["arenas"]["space"], 2)
        self.assertEqual(comp["arenas"]["both"], 0)
        self.assertEqual(comp["arenas"]["unit_slots"], 39)
        self.assertEqual(comp["arenas"]["space_pct"], 5.1)
        self.assertEqual(comp["distinct"], 18)
        self.assertEqual(comp["unique_slots"], 20)
        self.assertEqual(comp["mean_cost"]["value"], 3.24)
        self.assertEqual(comp["mean_cost"]["denominator"], 50)
        self.assertEqual(comp["price"]["total"], 28.19)
        self.assertEqual(comp["price"]["priced_slots"], 50)
        self.assertEqual(comp["price"]["coverage_pct"], 100.0)

    def test_main_deck_copies_sum_to_n(self):
        out = build()
        main = [c for c in out["cards"] if c["zone"] == "main"]
        self.assertEqual(sum(c["copies"] for c in main), out["composition"]["n"])

    def test_base_resolves_despite_empty_subtitle(self):
        out = build()
        self.assertEqual(
            out["deck"]["base"]["identity"],
            "Shield Generator Complex|Endor",
        )
        self.assertEqual(out["deck"]["base"]["resolved_by"], "set_number")

    def test_leader_resolves(self):
        out = build()
        self.assertEqual(
            out["deck"]["leader"]["identity"],
            "Poggle the Lesser|Let the Executions Begin",
        )

    def test_leader_and_base_have_card_sheets(self):
        out = build()
        self.assertEqual(len(out["cards"]), 20)
        self.assertEqual(sum(1 for c in out["cards"] if c["zone"] == "leader"), 1)
        self.assertEqual(sum(1 for c in out["cards"] if c["zone"] == "base"), 1)
        self.assertEqual(sum(1 for c in out["cards"] if c["zone"] == "main"), 18)

    def test_legality_is_ok(self):
        out = build()
        self.assertTrue(out["legality"]["ok"], out["legality"]["errors"])
        self.assertEqual(out["legality"]["errors"], [])
        self.assertEqual(out["deck"]["unresolved"], [])

    def test_fake_card_is_unresolved_and_illegal(self):
        out = build_with_fake_card()
        self.assertFalse(out["legality"]["ok"])
        self.assertEqual(len(out["deck"]["unresolved"]), 1)
        self.assertEqual(out["deck"]["unresolved"][0]["zone"], "main")
        self.assertEqual(out["deck"]["unresolved"][0]["reason"], "no matching card in database")

    def test_findings_are_documented_in_registry(self):
        out = build()
        registry = REGISTRY_PATH.read_text(encoding="utf-8")
        for finding in out["findings"]:
            self.assertIn(f"`{finding['id']}`", registry)
        self.assertIn("`arena-imbalance`", registry)

    def test_arena_finding_has_evidence(self):
        out = build()
        by_id = {f["id"]: f for f in out["findings"]}
        self.assertIn("arena-imbalance", by_id)
        finding = by_id["arena-imbalance"]
        self.assertEqual(finding["severity"], "warning")
        self.assertEqual(finding["evidence"]["value"], 2)
        self.assertEqual(finding["evidence"]["denominator"], 39)
        self.assertEqual(finding["evidence"]["pct"], 5.1)
        self.assertEqual(sum(c["copies"] for c in finding["evidence"]["cards"]), 2)
        self.assertEqual(
            [c["identity"] for c in finding["evidence"]["cards"]],
            ["Starlit Purrgil"],
        )

    def test_limitations_cover_known_gaps(self):
        out = build()
        ids = {lim["id"] for lim in out["limitations"]}
        expected = {
            "data-snapshot",
            "premier-only-db",
            "price-snapshot",
            "draw-goldfish",
            "no-rules-engine",
            "rules-version",
            "sideboard-legal-only",
            "heuristic-thresholds",
            "text-semantics-not-analyzed",
        }
        self.assertTrue(expected.issubset(ids), expected - ids)

    def test_draw_odds_shape(self):
        out = build()
        odds = out["draw_odds"]
        self.assertEqual(odds["n"], 50)
        self.assertEqual(odds["hand"], 6)
        self.assertEqual(odds["draw_per_regroup"], 2)
        self.assertEqual(odds["rounds"], [0, 1, 2, 3, 4, 5, 6])
        self.assertEqual(len(odds["per_card"]), 18)
        self.assertTrue(odds["assumptions"])

        rancor = next(c for c in odds["per_card"] if c["identity"] == "Rancor Keeper")
        self.assertEqual(rancor["copies"], 3)
        self.assertEqual(rancor["p"][0], 32.4)
        self.assertEqual(len(rancor["p"]), 7)

    def test_output_is_deterministic(self):
        first = json.dumps(build(), sort_keys=True)
        second = json.dumps(build(), sort_keys=True)
        self.assertEqual(first, second)

    def test_schema_validates(self):
        try:
            import jsonschema
        except ImportError:
            self.fail("jsonschema is required to run the contract test")

        jsonschema.validate(instance=build(), schema=load_schema())


if __name__ == "__main__":
    unittest.main()

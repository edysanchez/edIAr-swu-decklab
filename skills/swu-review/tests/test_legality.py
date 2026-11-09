#!/usr/bin/env python3
"""Focused legality tests for the new analysis pipeline.

``validate_deck.load_deck`` collapses leader and base entries, so the analysis
layer inspects the raw JSON to enforce "exactly one leader, exactly one base".
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

import analysis  # noqa: E402

FIXTURES_DIR = TESTS_DIR / "fixtures"
CASE = FIXTURES_DIR / "poggle-blue-endor" / "deck.json"
CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"
FIXED_TIME = "2026-11-03T00:00:00Z"


def build_from(deck):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "deck.json"
        path.write_text(json.dumps(deck), encoding="utf-8")
        return analysis.build_analysis(
            path,
            card_db_path=CARD_DB,
            generated_at=FIXED_TIME,
        )


def load_case():
    return json.loads(CASE.read_text(encoding="utf-8"))


def entry_of_type(deck, type_name):
    return next(
        entry for entry in deck["mainDeck"]
        if entry["card"]["type"]["name"] == type_name
    )


class LegalityTest(unittest.TestCase):
    def assert_illegal(self, out, needle):
        self.assertFalse(out["legality"]["ok"])
        errors = " ".join(out["legality"]["errors"]).lower()
        self.assertIn(needle, errors, out["legality"]["errors"])

    def test_duplicate_leader_entry_is_illegal(self):
        deck = load_case()
        deck["mainDeck"].append(copy.deepcopy(entry_of_type(deck, "Leader")))
        self.assert_illegal(build_from(deck), "leader")

    def test_leader_count_two_is_illegal(self):
        deck = load_case()
        entry_of_type(deck, "Leader")["count"] = 2
        self.assert_illegal(build_from(deck), "leader")

    def test_duplicate_base_entry_is_illegal(self):
        deck = load_case()
        deck["mainDeck"].append(copy.deepcopy(entry_of_type(deck, "Base")))
        self.assert_illegal(build_from(deck), "base")

    def test_base_count_two_is_illegal(self):
        deck = load_case()
        entry_of_type(deck, "Base")["count"] = 2
        self.assert_illegal(build_from(deck), "base")

    def test_leader_count_two_is_not_reported_as_one_copy(self):
        deck = load_case()
        entry_of_type(deck, "Leader")["count"] = 2
        out = build_from(deck)
        self.assertEqual(out["deck"]["leader"]["count"], 2)
        sheet = next(c for c in out["cards"] if c["zone"] == "leader")
        self.assertEqual(sheet["copies"], 2)

    def test_swudb_json_duplicate_leader_is_illegal(self):
        deck = {
            "leader": {"id": "HMW_012", "count": 2},
            "base": {"id": "HMW_022", "count": 1},
            "deck": [{"id": "ASH_032", "count": 3}],
            "sideboard": [],
        }
        self.assert_illegal(build_from(deck), "leader")

    def test_text_format_still_loads(self):
        deck = (
            "Leader\n1 | Poggle the Lesser | Let the Executions Begin\n\n"
            "Base\n1 | Shield Generator Complex | Endor\n\n"
            "MainDeck\n3 | Rancor Keeper\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.txt"
            path.write_text(deck, encoding="utf-8")
            out = analysis.build_analysis(
                path,
                card_db_path=CARD_DB,
                generated_at=FIXED_TIME,
            )
        self.assertIn("legality", out)
        self.assertEqual(out["input"]["format"], "text")


if __name__ == "__main__":
    unittest.main()

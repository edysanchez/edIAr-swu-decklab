#!/usr/bin/env python3
"""Aspect penalty must reflect off-aspect cards.

Leader Poggle provides Aggression + Villainy, base Shield Generator provides
Vigilance. Adept ARC-170 is Command, so each copy costs 2 extra resources.

The deck is deliberately tiny: the test only inspects ``aspect_penalty``, and
legality errors about the 50-card minimum are expected and irrelevant here.
"""

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

CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"
FIXED_TIME = "2026-11-03T00:00:00Z"

DECK = {
    "leader": {"id": "HMW_012", "count": 1},  # Poggle: Aggression, Villainy
    "base": {"id": "HMW_022", "count": 1},  # Shield Generator Complex: Vigilance
    "deck": [{"id": "JTL_114", "count": 3}],  # Adept ARC-170: Command
    "sideboard": [],
}


def analyse():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "deck.json"
        path.write_text(json.dumps(DECK), encoding="utf-8")
        return analysis.build_analysis(
            path, card_db_path=CARD_DB, generated_at=FIXED_TIME
        )


class AspectPenaltyTest(unittest.TestCase):
    def test_off_aspect_card_is_penalised(self):
        penalty = analyse()["legality"]["aspect_penalty"]

        self.assertGreater(penalty["total"], 0, penalty)
        self.assertEqual(penalty["total"], 6, penalty)  # 2 per copy x 3 copies
        self.assertEqual(penalty["max"], 2, penalty)

    def test_per_card_entry_matches_the_schema(self):
        entry = analyse()["legality"]["aspect_penalty"]["per_card"][0]

        # analysis.schema.json requires a string, not the (name, subtitle) tuple
        self.assertIsInstance(entry["identity"], str)
        self.assertEqual(entry["identity"], "Adept ARC-170")
        self.assertEqual(entry["missing_aspects"], ["Command"])
        self.assertEqual(entry["copies"], 3)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FACTORY_DIR))

import oracle  # noqa: E402


class OracleMutationTests(unittest.TestCase):
    def deck(self) -> dict:
        return {
            "mainDeck": [
                {"count": 1, "card": {"type": {"name": "Leader"}}},
                {"count": 3, "card": {"type": {"name": "Unit"}}},
            ],
            "sideboard": [],
        }

    def test_set_leader_count(self) -> None:
        deck = oracle.apply_mutation(
            self.deck(), {"type": "set_leader_count", "value": 2}
        )
        self.assertEqual(deck["mainDeck"][0]["count"], 2)

    def test_unit_in_leader_slot(self) -> None:
        deck = oracle.apply_mutation(self.deck(), {"type": "unit_in_leader_slot"})
        self.assertEqual(deck["mainDeck"][0]["card"]["type"]["name"], "Unit")

    def test_leader_in_sideboard(self) -> None:
        deck = oracle.apply_mutation(self.deck(), {"type": "leader_in_sideboard"})
        self.assertEqual(len(deck["mainDeck"]), 1)
        self.assertEqual(len(deck["sideboard"]), 1)
        self.assertEqual(deck["sideboard"][0]["card"]["type"]["name"], "Leader")

    def test_add_secondleader(self) -> None:
        deck = oracle.apply_mutation(
            self.deck(), {"type": "add_secondleader", "value": "ASH_011"}
        )
        self.assertEqual(deck["secondleader"], {"id": "ASH_011"})

    def test_unknown_mutation_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            oracle.apply_mutation(self.deck(), {"type": "not-a-mutation"})


if __name__ == "__main__":
    unittest.main()

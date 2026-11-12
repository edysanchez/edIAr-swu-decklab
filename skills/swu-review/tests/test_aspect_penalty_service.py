#!/usr/bin/env python3
"""Unit tests for AspectPenaltyService.

The service is exercised in isolation: an `InMemoryCardRepository` with six
cards, no files, no card database. The integration counterpart (real database,
full pipeline) is `test_aspect_penalty_integration.py`.

Rule under test (`docs/rules.md`): a card whose aspects are not provided by the
leader or the base costs 2 additional resources per missing aspect icon.
"""

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SKILL_DIR))

from domain.services.aspect_penalty_service import AspectPenaltyService  # noqa: E402
from infrastructure.in_memory_card_repository import InMemoryCardRepository  # noqa: E402

LEADER = ("Poggle the Lesser", "Let the Executions Begin")  # Aggression, Villainy
BASE = ("Shield Generator Complex", "Endor")  # Vigilance
OFF_ASPECT = ("Adept ARC-170", "")  # Command
ON_ASPECT = ("Adamant Ewoks", "")  # Aggression
VIGILANCE_CARD = ("Batcher", "")  # Vigilance
TWO_MISSING = ("Double Off", "")  # Command, Heroism
NO_ASPECTS = ("Attack Run", "")  # no icons at all

CARDS = {
    LEADER: {"aspects": ["Aggression", "Villainy"]},
    BASE: {"aspects": ["Vigilance"]},
    OFF_ASPECT: {"aspects": ["Command"]},
    ON_ASPECT: {"aspects": ["Aggression"]},
    VIGILANCE_CARD: {"aspects": ["Vigilance"]},
    TWO_MISSING: {"aspects": ["Command", "Heroism"]},
    NO_ASPECTS: {"aspects": []},
}

EMPTY = {"total": 0, "max": 0, "per_card": []}


class AspectPenaltyServiceTest(unittest.TestCase):
    def penalty(self, main_counts, leader=LEADER, base=BASE):
        service = AspectPenaltyService(InMemoryCardRepository(CARDS))
        return service.calculate_penalty(leader, base, main_counts)

    def test_off_aspect_card_costs_two_per_copy(self):
        out = self.penalty({OFF_ASPECT: 1})

        self.assertEqual(out["total"], 2)
        self.assertEqual(out["max"], 2)
        self.assertEqual(
            out["per_card"],
            [
                {
                    "identity": "Adept ARC-170",
                    "copies": 1,
                    "penalty": 2,
                    "missing_aspects": ["Command"],
                }
            ],
        )

    def test_copies_multiply_the_penalty(self):
        out = self.penalty({OFF_ASPECT: 3})

        self.assertEqual(out["total"], 6)
        self.assertEqual(out["max"], 2)  # max is per card, not per copy

    def test_each_missing_aspect_costs_two(self):
        out = self.penalty({TWO_MISSING: 1})

        self.assertEqual(out["total"], 4)
        self.assertEqual(out["max"], 4)
        self.assertEqual(out["per_card"][0]["missing_aspects"], ["Command", "Heroism"])

    def test_card_matching_the_deck_is_free(self):
        self.assertEqual(self.penalty({ON_ASPECT: 3}), EMPTY)

    def test_leader_provides_its_aspects(self):
        self.assertEqual(self.penalty({ON_ASPECT: 1})["total"], 0)
        self.assertEqual(self.penalty({ON_ASPECT: 1}, leader=None)["total"], 2)

    def test_base_provides_its_aspects(self):
        self.assertEqual(self.penalty({VIGILANCE_CARD: 1})["total"], 0)
        self.assertEqual(self.penalty({VIGILANCE_CARD: 1}, base=None)["total"], 2)

    def test_card_without_aspects_is_never_penalised(self):
        self.assertEqual(self.penalty({NO_ASPECTS: 4}), EMPTY)

    def test_total_sums_cards_and_max_takes_the_worst(self):
        out = self.penalty({OFF_ASPECT: 2, TWO_MISSING: 1})

        self.assertEqual(out["total"], 2 * 2 + 4)
        self.assertEqual(out["max"], 4)
        self.assertEqual(
            [entry["identity"] for entry in out["per_card"]],
            ["Adept ARC-170", "Double Off"],
        )


if __name__ == "__main__":
    unittest.main()

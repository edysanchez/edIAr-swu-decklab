#!/usr/bin/env python3
"""Aspect penalty must count every icon, not every aspect name."""

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SKILL_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from domain.services.aspect_penalty_service import AspectPenaltyService  # noqa: E402
from infrastructure.in_memory_card_repository import InMemoryCardRepository  # noqa: E402

DOUBLE = ("Synthetic Double Aspect", "")
SINGLE = ("Single Aspect", "")
LEADER = ("Synthetic Leader", "Prime")
BASE = ("Synthetic Base", "Endor")
AGGRESSION_LEADER = ("Aggression Leader", "")
AGGRESSION_BASE = ("Aggression Base", "")


class AspectPenaltyServiceTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryCardRepository({
            LEADER: {"aspects": ["Aggression", "Villainy"]},
            BASE: {"aspects": ["Vigilance"]},
            AGGRESSION_LEADER: {"aspects": ["Aggression", "Villainy"]},
            AGGRESSION_BASE: {"aspects": ["Aggression"]},
            DOUBLE: {"aspects": ["Aggression", "Aggression"]},
            SINGLE: {"aspects": ["Aggression"]},
        })
        self.service = AspectPenaltyService(self.repo)

    def test_double_icon_covered_once(self):
        result = self.service.calculate_penalty(LEADER, BASE, {DOUBLE: 3})
        self.assertEqual(result["total"], 6)
        self.assertEqual(result["max"], 2)
        self.assertEqual(result["affected_slots"], 3)
        self.assertEqual(result["total_per_slot"], 2.0)
        self.assertEqual(result["per_card"][0]["identity"], "Synthetic Double Aspect")
        self.assertEqual(result["per_card"][0]["missing_aspects"], ["Aggression"])

    def test_double_icon_covered_twice(self):
        result = self.service.calculate_penalty(
            AGGRESSION_LEADER, AGGRESSION_BASE, {DOUBLE: 3}
        )
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["max"], 0)
        self.assertEqual(result["affected_slots"], 0)
        self.assertEqual(result["total_per_slot"], 0.0)
        self.assertEqual(result["per_card"], [])

    def test_double_icon_without_source(self):
        result = self.service.calculate_penalty(None, None, {DOUBLE: 3})
        self.assertEqual(result["total"], 12)
        self.assertEqual(result["max"], 4)
        self.assertEqual(result["affected_slots"], 3)
        self.assertEqual(result["total_per_slot"], 4.0)
        self.assertEqual(
            result["per_card"][0]["missing_aspects"],
            ["Aggression", "Aggression"],
        )

    def test_single_icon_is_unchanged(self):
        result = self.service.calculate_penalty(LEADER, BASE, {SINGLE: 3})
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["max"], 0)
        self.assertEqual(result["affected_slots"], 0)
        self.assertEqual(result["total_per_slot"], 0.0)
        self.assertEqual(result["per_card"], [])


if __name__ == "__main__":
    unittest.main()

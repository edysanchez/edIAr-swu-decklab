#!/usr/bin/env python3
"""Contract for the dynamic Premier legal-set check.

These tests mirror `docs/rules.md`:

- the legal set list is a dated snapshot, not a constant;
- a snapshot wins over the built-in registry, and disagreements are reported;
- freshness is not only "how many days old": a `next_change` date that has
  already passed makes the snapshot suspect even if it was fetched yesterday.

No network is used here: snapshots are written to a temporary directory.
"""

import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import constants as C  # noqa: E402
import legal_sets  # noqa: E402

FAR_PAST = "2000-01-01"
FAR_FUTURE = "2099-01-01"
RECENT = "2026-11-12T00:00:00Z"
RECENT_DAY = "2026-11-12"


def snapshot(**overrides):
    base = {
        "source": "https://example.invalid/premier-format-and-rotation/",
        "fetched_at": RECENT,
        "as_of": RECENT_DAY,
        "legal": ["JTL", "LOF"],
        "next_change": {"product": "IC27", "legal_from": FAR_FUTURE},
        "products": [
            {"code": "JTL", "name": "Jump to Lightspeed", "release": "2024-12-13"},
            {"code": "LOF", "name": "Legends of the Force", "release": "2025-03-14"},
        ],
    }
    base.update(overrides)
    return base


class LegalSetsTest(unittest.TestCase):
    def write(self, **overrides):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        path = Path(handle.name) / "legal-sets.json"
        path.write_text(json.dumps(snapshot(**overrides)), encoding="utf-8")
        return path

    def load(self, **overrides):
        return legal_sets.load(snapshot_path=self.write(**overrides))

    def test_snapshot_wins_over_the_builtin_registry(self):
        result = self.load()

        self.assertEqual(result.codes, frozenset({"JTL", "LOF"}))
        self.assertEqual(result.source, "hub-snapshot")
        self.assertEqual(result.as_of, RECENT_DAY)

    def test_missing_snapshot_falls_back_to_the_registry(self):
        result = legal_sets.load(snapshot_path=Path("/nonexistent/legal-sets.json"))

        self.assertEqual(result.codes, frozenset(C.PREMIER_SETS))
        self.assertEqual(result.source, "builtin-registry")

    def test_old_snapshot_is_reported(self):
        result = self.load(fetched_at="2020-01-01T00:00:00Z", as_of="2020-01-01")

        self.assertTrue(
            any("day" in warning.lower() for warning in result.warnings),
            result.warnings,
        )

    def test_next_change_in_the_past_is_reported(self):
        result = self.load(
            next_change={"product": "IC27", "legal_from": FAR_PAST},
            fetched_at="2020-01-01T00:00:00Z",
            as_of="2020-01-01",
        )

        self.assertTrue(
            any("IC27" in warning for warning in result.warnings), result.warnings
        )

    def test_disagreement_with_the_registry_is_reported(self):
        result = self.load(legal=["JTL", "IC27"])

        self.assertEqual(result.codes, frozenset({"JTL", "IC27"}))
        warnings = " ".join(result.warnings)
        self.assertIn("IC27", warnings)  # listed by the snapshot, not by the registry
        self.assertIn("LOF", warnings)  # listed by the registry, not by the snapshot

    def test_empty_list_is_treated_as_corrupt(self):
        result = self.load(
            legal=[],
            products=[{"code": "SOR", "name": "Spark of Rebellion", "release": "2023-11-17"}],
        )

        # No source can answer "no set is legal": fall back to the registry and say so.
        self.assertEqual(result.source, "builtin-registry")
        self.assertEqual(result.codes, frozenset(C.PREMIER_SETS))
        self.assertTrue(
            any("snapshot" in warning.lower() for warning in result.warnings),
            result.warnings,
        )
        self.assertFalse(result.is_legal("SOR"))  # rotated, still refused

    def test_snapshot_without_as_of_does_not_grant_legality(self):
        result = self.load(
            as_of=None,
            legal=["JTL"],
            products=[{"code": "IC27", "name": "Icons 2027", "release": "2026-11-01"}],
        )

        self.assertFalse(result.is_legal("IC27"))
        self.assertTrue(
            any("date" in warning.lower() for warning in result.warnings),
            result.warnings,
        )

    def test_a_set_legal_by_release_date_is_checked_for_coverage(self):
        today = date.today()
        result = legal_sets.load(
            snapshot_path=self.write(
                as_of=(today - timedelta(days=1)).isoformat(),
                products=[
                    {"code": "IC27", "name": "Icons 2027", "legal_from": today.isoformat()}
                ],
            ),
            known_sets={"JTL", "LOF"},
        )

        self.assertTrue(result.is_legal("IC27"))  # legal through the date window
        self.assertTrue(
            any("IC27" in warning and "fetch_cards" in warning for warning in result.warnings),
            result.warnings,
        )

    def test_a_legal_set_without_cards_is_reported(self):
        result = legal_sets.load(
            snapshot_path=self.write(
                legal=["JTL", "HMW"], products=[]
            ),
            known_sets={"JTL"},
        )

        warnings = " ".join(result.warnings)
        self.assertIn("HMW", warnings)
        self.assertIn("fetch_cards", warnings)

    def test_no_coverage_warning_when_every_legal_set_has_cards(self):
        result = legal_sets.load(
            snapshot_path=self.write(legal=["JTL"], products=[]),
            known_sets={"JTL", "HMW"},
        )

        self.assertFalse(
            any("fetch_cards" in warning for warning in result.warnings),
            result.warnings,
        )

    def test_any_legal_printing_makes_the_card_legal(self):
        # `docs/rules.md`: a reprint in a Premier-legal product legalises the card.
        result = self.load(legal=["HMW"])

        self.assertTrue(result.is_legal_any(["SOR", "HMW"]))
        self.assertFalse(result.is_legal_any(["SOR", "SHD"]))
        self.assertFalse(result.is_legal_any([]))

    def test_legal_from_is_used_for_upcoming_products(self):
        # Unreleased sets carry "legal_from" instead of "release".
        result = self.load(
            legal=["JTL"],
            products=[
                {"code": "IC27", "name": "Icons 2027", "legal_from": "2026-11-13"}
            ],
        )

        self.assertFalse(result.is_legal("IC27", date(2026, 11, 12)))
        self.assertTrue(result.is_legal("IC27", date(2026, 11, 13)))


if __name__ == "__main__":
    unittest.main()

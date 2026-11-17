#!/usr/bin/env python3
"""The pipeline must read the dated legal-set list, not the constants tuple.

`constants.PREMIER_SETS` is the fallback, not the source. These tests drop a set
from the snapshot and expect both entry points to reject a card from it: with
the old hardcoded check that could never happen, because the card database only
contains Premier sets.

They also check that the snapshot's freshness warnings reach the analysis, and
that the registry still applies when no snapshot exists.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
REPO_ROOT = SKILL_DIR.parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import analysis  # noqa: E402
import constants as C  # noqa: E402
import validate_deck as vd  # noqa: E402

CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"
FIXED_TIME = "2026-11-03T00:00:00Z"

ALL_SETS = ["JTL", "LOF", "IBH", "SEC", "LAW", "ASH", "HMW"]
WITHOUT_JTL = ["LOF", "IBH", "SEC", "LAW", "ASH", "HMW"]

# Poggle (HMW) + Shield Generator (HMW) + 3x Adept ARC-170 (JTL).
DECK = {
    "leader": {"id": "HMW_012", "count": 1},
    "base": {"id": "HMW_022", "count": 1},
    "deck": [{"id": "JTL_114", "count": 3}],
    "sideboard": [],
}

# A JTL leader and a JTL base with an otherwise HMW deck: the set pool applies
# to the leader and base slots too (`docs/rules.md`).
JTL_LEADER_DECK = {
    "leader": {"id": "JTL_016", "count": 1},  # Admiral Ackbar
    "base": {"id": "HMW_022", "count": 1},
    "deck": [{"id": "HMW_177", "count": 50}],
    "sideboard": [],
}

JTL_BASE_DECK = {
    "leader": {"id": "HMW_012", "count": 1},
    "base": {"id": "JTL_024", "count": 1},  # Data Vault, Scarif
    "deck": [{"id": "HMW_177", "count": 50}],
    "sideboard": [],
}


def snapshot(legal, fetched_at="2026-11-12T00:00:00Z", as_of="2026-11-12"):
    return {
        "source": "test",
        "fetched_at": fetched_at,
        "as_of": as_of,
        "legal": legal,
        "next_change": None,
        "products": [],
    }


class RunMixin:
    def write_deck(self, deck=None):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        path = Path(handle.name) / "deck.json"
        path.write_text(json.dumps(deck or DECK), encoding="utf-8")
        return path

    def use_snapshot(self, **overrides):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        path = Path(handle.name) / "legal-sets.json"
        path.write_text(json.dumps(snapshot(**overrides)), encoding="utf-8")
        patcher = mock.patch.object(C, "LEGAL_SETS_SNAPSHOT_PATH", str(path))
        patcher.start()
        self.addCleanup(patcher.stop)
        return path

    def analyse(self, deck=None):
        return analysis.build_analysis(
            self.write_deck(deck),
            card_db_path=CARD_DB,
            generated_at=FIXED_TIME,
        )


class ValidateDeckLegalSetsTest(RunMixin, unittest.TestCase):
    def test_rejects_a_set_the_snapshot_drops(self):
        self.use_snapshot(legal=WITHOUT_JTL)

        _ok, errors, _warnings = vd.validate_deck(self.write_deck(), verbose=False)

        self.assertTrue(
            any("non-Premier set JTL" in error for error in errors), errors
        )

    def test_accepts_the_set_when_the_snapshot_lists_it(self):
        self.use_snapshot(legal=ALL_SETS)

        _ok, errors, _warnings = vd.validate_deck(self.write_deck(), verbose=False)

        self.assertFalse(any("non-Premier" in error for error in errors), errors)

    def test_rejects_a_leader_from_a_dropped_set(self):
        self.use_snapshot(legal=WITHOUT_JTL)

        _ok, errors, _warnings = vd.validate_deck(
            self.write_deck(JTL_LEADER_DECK), verbose=False
        )

        self.assertTrue(
            any("non-Premier set JTL" in error for error in errors), errors
        )

    def test_rejects_a_base_from_a_dropped_set(self):
        self.use_snapshot(legal=WITHOUT_JTL)

        _ok, errors, _warnings = vd.validate_deck(
            self.write_deck(JTL_BASE_DECK), verbose=False
        )

        self.assertTrue(
            any("non-Premier set JTL" in error for error in errors), errors
        )

    def test_warns_about_a_legal_set_without_cards(self):
        # IBH is legal in the snapshot but the database has no IBH cards.
        # IBH is used because no cached card has an IBH printing, so the set is
        # genuinely absent rather than covered by another printing.
        self.use_snapshot(legal=ALL_SETS)
        card_db = {
            key: card
            for key, card in vd.sc.load_swu_cards().items()
            if card.get("set") != "IBH"
        }

        with mock.patch.object(vd.sc, "load_swu_cards", return_value=card_db):
            _ok, _errors, warnings = vd.validate_deck(
                self.write_deck(), verbose=False
            )

        self.assertTrue(
            any("IBH" in warning and "fetch_cards" in warning for warning in warnings),
            warnings,
        )

    def test_accepts_a_card_reprinted_in_a_legal_set(self):
        # The deck entry points at JTL, which the snapshot drops, but the card
        # also exists in HMW: `docs/rules.md` makes it legal.
        self.use_snapshot(legal=WITHOUT_JTL)
        card_db = dict(vd.sc.load_swu_cards())
        key = ("Adept ARC-170", "")
        card_db[key] = dict(card_db[key], printings=["JTL", "HMW"])

        with mock.patch.object(vd.sc, "load_swu_cards", return_value=card_db):
            _ok, errors, _warnings = vd.validate_deck(
                self.write_deck(), verbose=False
            )

        self.assertFalse(any("non-Premier" in error for error in errors), errors)

    def test_rejects_a_card_without_a_legal_printing(self):
        self.use_snapshot(legal=WITHOUT_JTL)
        card_db = dict(vd.sc.load_swu_cards())
        key = ("Adept ARC-170", "")
        card_db[key] = dict(card_db[key], printings=["JTL"])

        with mock.patch.object(vd.sc, "load_swu_cards", return_value=card_db):
            _ok, errors, _warnings = vd.validate_deck(
                self.write_deck(), verbose=False
            )

        self.assertTrue(
            any("non-Premier set JTL" in error for error in errors), errors
        )

    def test_without_a_snapshot_the_registry_applies(self):
        with mock.patch.object(C, "LEGAL_SETS_SNAPSHOT_PATH", "/nonexistent/legal.json"):
            _ok, errors, _warnings = vd.validate_deck(self.write_deck(), verbose=False)

        self.assertFalse(any("non-Premier" in error for error in errors), errors)


class AnalysisLegalSetsTest(RunMixin, unittest.TestCase):
    def premier_sets_check(self, out):
        return next(c for c in out["legality"]["checks"] if c["id"] == "premier_sets")

    def test_analysis_follows_the_snapshot(self):
        self.use_snapshot(legal=WITHOUT_JTL)

        check = self.premier_sets_check(self.analyse())

        self.assertFalse(check["ok"], check)
        self.assertIn("JTL", check["detail"])

    def test_analysis_accepts_the_set_when_the_snapshot_lists_it(self):
        self.use_snapshot(legal=ALL_SETS)

        check = self.premier_sets_check(self.analyse())

        self.assertTrue(check["ok"], check)

    def test_analysis_flags_a_leader_from_a_dropped_set(self):
        self.use_snapshot(legal=WITHOUT_JTL)

        check = self.premier_sets_check(self.analyse(JTL_LEADER_DECK))

        self.assertFalse(check["ok"], check)
        self.assertIn("Admiral Ackbar", check["detail"])

    def test_analysis_flags_a_base_from_a_dropped_set(self):
        self.use_snapshot(legal=WITHOUT_JTL)

        check = self.premier_sets_check(self.analyse(JTL_BASE_DECK))

        self.assertFalse(check["ok"], check)
        self.assertIn("JTL", check["detail"])

    def test_analysis_warns_about_a_legal_set_without_cards(self):
        self.use_snapshot(legal=ALL_SETS)
        card_db = {
            key: card
            for key, card in analysis.sc.load_swu_cards().items()
            if card.get("set") != "IBH"
        }

        with mock.patch.object(analysis.sc, "load_swu_cards", return_value=card_db):
            out = self.analyse()

        self.assertTrue(
            any(
                "IBH" in warning and "fetch_cards" in warning
                for warning in out["legality"]["warnings"]
            ),
            out["legality"]["warnings"],
        )

    def test_stale_snapshot_warning_reaches_the_analysis(self):
        self.use_snapshot(legal=ALL_SETS, fetched_at="2020-01-01T00:00:00Z", as_of="2020-01-01")

        out = self.analyse()

        self.assertTrue(
            any("days" in warning.lower() for warning in out["legality"]["warnings"]),
            out["legality"]["warnings"],
        )


if __name__ == "__main__":
    unittest.main()

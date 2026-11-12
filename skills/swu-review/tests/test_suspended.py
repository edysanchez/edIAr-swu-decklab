#!/usr/bin/env python3
"""Suspended-list regressions.

The Premier suspended list is small but decisive: a deck that plays a suspended
card is illegal, so both entry points (`swu_analyze.py` and `validate_deck.py`)
must reject it. These tests also pin the leader case, because the analysis
pipeline used to look only at draw-deck and sideboard counts.

Source of truth: `docs/rules.md` and `constants.SUSPENDED_CARDS`.
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
import constants as C  # noqa: E402
import swu_cards as sc  # noqa: E402
import validate_deck as vd  # noqa: E402

FIXTURES_DIR = TESTS_DIR / "fixtures"
CASE = FIXTURES_DIR / "poggle-blue-endor" / "deck.json"
CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"
FIXED_TIME = "2026-11-03T00:00:00Z"

EXPECTED_SUSPENDED = {
    ("Cad Bane", "Still Faster Than You"),
    ("Chimaera", "A Frightening Reality"),
    ("Koska Reeves", "Warrior of Mandalore"),
    ("Neel", "The Cutest Boy"),
    ("Aggressive Negotiations", ""),
}


def card_id(card):
    number = card["cardNumber"]
    suffix = f"{int(number):03d}" if str(number).isdigit() else str(number)
    return f"{card['expansion']['code']}_{suffix}"


def build_swudb_deck():
    """Convert the Poggle fixture to SWUDB JSON (leader/base + 50-card deck)."""
    case = json.loads(CASE.read_text(encoding="utf-8"))
    leader = base = None
    main = []
    for entry in case["mainDeck"]:
        card = entry["card"]
        if card["type"]["name"] == "Leader":
            leader = card_id(card)
        elif card["type"]["name"] == "Base":
            base = card_id(card)
        else:
            main.append({"id": card_id(card), "count": entry["count"]})
    return {
        "leader": {"id": leader, "count": 1},
        "base": {"id": base, "count": 1},
        "deck": main,
        "sideboard": [],
    }


def deck_with_suspended(record):
    """Return a copy of the fixture with one suspended card swapped in."""
    deck = build_swudb_deck()
    cid = f"{record['set']}_{record['number']}"
    if record["type"] == "Leader":
        deck["leader"] = {"id": cid, "count": 1}
    else:
        # Keep the total at 50 cards and the copy limit untouched.
        deck["deck"][0] = {"id": cid, "count": deck["deck"][0]["count"]}
    return deck


class RunMixin:
    def write_deck(self, deck):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        path = Path(handle.name) / "deck.json"
        path.write_text(json.dumps(deck), encoding="utf-8")
        return path

    def analyse(self, deck):
        return analysis.build_analysis(
            self.write_deck(deck),
            card_db_path=CARD_DB,
            generated_at=FIXED_TIME,
        )

    def validate(self, deck):
        return vd.validate_deck(self.write_deck(deck), verbose=False)


class SuspendedRegistryTest(unittest.TestCase):
    def test_registry_contains_exactly_the_five_suspended_cards(self):
        self.assertEqual(set(C.SUSPENDED), EXPECTED_SUSPENDED)

    def test_registry_records_are_consistent(self):
        for record in C.SUSPENDED_CARDS:
            with self.subTest(card=record["identity"]):
                self.assertIn(record["identity"], C.SUSPENDED)
                self.assertEqual(len(record["number"]), 3)
                self.assertIn(record["type"], {"Leader", "Unit", "Event", "Upgrade"})
                self.assertRegex(record["announced"], r"^\d{4}-\d{2}-\d{2}$")

    def test_every_entry_cites_an_official_announcement(self):
        for record in C.SUSPENDED_CARDS:
            with self.subTest(card=record["identity"]):
                self.assertTrue(
                    record["source"].startswith("https://starwarsunlimited.com/"),
                    record["source"],
                )
                self.assertIn(record["source"], C.SUSPENDED_SOURCES)

    def test_every_suspended_card_is_in_the_card_database(self):
        db = sc.load_swu_cards(CARD_DB)
        for record in C.SUSPENDED_CARDS:
            with self.subTest(card=record["identity"]):
                self.assertIn(record["identity"], db)
                card = db[record["identity"]]
                self.assertEqual(card["set"], record["set"])
                self.assertEqual(card["number"], record["number"])
                self.assertEqual(card["type"], record["type"])


class AnalysisSuspendedTest(RunMixin, unittest.TestCase):
    def suspended_check(self, out):
        return next(c for c in out["legality"]["checks"] if c["id"] == "suspended")

    def test_control_deck_passes_the_suspended_check(self):
        out = self.analyse(build_swudb_deck())
        check = self.suspended_check(out)
        self.assertTrue(check["ok"], check)
        self.assertEqual(check["detail"], "No suspended cards")

    def test_suspended_main_deck_cards_are_illegal(self):
        for record in C.SUSPENDED_CARDS:
            if record["type"] == "Leader":
                continue
            with self.subTest(card=record["identity"]):
                out = self.analyse(deck_with_suspended(record))
                check = self.suspended_check(out)
                self.assertFalse(check["ok"], check)
                name, subtitle = record["identity"]
                label = f"{name}|{subtitle}" if subtitle else name
                self.assertIn("Suspended cards:", check["detail"])
                self.assertIn(label, check["detail"])
                self.assertFalse(out["legality"]["ok"])

    def test_suspended_leader_is_illegal(self):
        record = next(r for r in C.SUSPENDED_CARDS if r["type"] == "Leader")
        out = self.analyse(deck_with_suspended(record))
        check = self.suspended_check(out)
        self.assertFalse(check["ok"], check)
        self.assertIn("Cad Bane|Still Faster Than You", check["detail"])
        self.assertFalse(out["legality"]["ok"])


class ValidateDeckSuspendedTest(RunMixin, unittest.TestCase):
    def test_control_deck_is_valid(self):
        ok, errors, _warnings = self.validate(build_swudb_deck())
        self.assertTrue(ok, errors)

    def test_every_suspended_card_is_rejected(self):
        for record in C.SUSPENDED_CARDS:
            with self.subTest(card=record["identity"]):
                ok, errors, _warnings = self.validate(deck_with_suspended(record))
                self.assertFalse(ok, errors)
                self.assertTrue(
                    any("is suspended in Premier" in e for e in errors), errors
                )

    def test_error_names_the_specific_printing(self):
        record = next(r for r in C.SUSPENDED_CARDS if r["type"] == "Leader")
        ok, errors, _warnings = self.validate(deck_with_suspended(record))
        self.assertFalse(ok)
        message = next(e for e in errors if "is suspended" in e)
        self.assertIn("Cad Bane - Still Faster Than You", message)
        self.assertIn("ASH 011", message)


if __name__ == "__main__":
    unittest.main()

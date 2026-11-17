#!/usr/bin/env python3
"""A deck may reference any printing of a card, not the canonical one.

`docs/rules.md`: legality follows the card version, and the identity is the
printed name plus subtitle. The catalogue keeps one record per identity, so the
record's `set`/`number` is only the canonical printing; resolution must still
accept every known printing.

The SWUDB id-only export (`{"id": "JTL_258"}`) carries no name, so a miss here is
not recoverable: the deck is reported as having unresolved cards.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
from support import requires_catalogue  # noqa: E402
SKILL_DIR = TESTS_DIR.parent
REPO_ROOT = SKILL_DIR.parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import analysis  # noqa: E402
import card_resolver  # noqa: E402
import constants as C  # noqa: E402
import swu_cards as sc  # noqa: E402
import validate_deck as vd  # noqa: E402

CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"
FIXED_TIME = "2026-11-03T00:00:00Z"

# Corellian Freighter is printed in JTL (Premier) and SOR (rotated). The
# catalogue's canonical record points at SOR, so a deck that references the JTL
# printing used to be unresolvable.
REPRINTED = ("Corellian Freighter", "")
FILLER = ("Adamant Ewoks", "")  # HMW 177

DECK = {
    "leader": {"id": "HMW_012", "count": 1},
    "base": {"id": "HMW_022", "count": 1},
    "deck": [
        {"id": "JTL_258", "count": 3},
        {"id": "HMW_177", "count": 47},
    ],
    "sideboard": [],
}


@requires_catalogue
class ResolutionPrintingsTest(unittest.TestCase):
    def setUp(self):
        self.card_db = sc.load_swu_cards(CARD_DB)
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.path = Path(handle.name) / "deck.json"
        self.path.write_text(json.dumps(DECK), encoding="utf-8")

    def test_the_fixture_card_really_is_a_reprint(self):
        card = self.card_db[REPRINTED]
        printings = [entry["set"] if isinstance(entry, dict) else entry for entry in card.get("printings") or []]

        self.assertIn("JTL", printings)
        self.assertIn("SOR", printings)

    def test_index_resolves_the_premier_printing(self):
        index = card_resolver.CardIndex(self.card_db)

        resolved = index.resolve({"set": "JTL", "number": "258", "id": "JTL_258"})

        self.assertEqual(resolved.key, REPRINTED)
        self.assertEqual(resolved.resolved_by, "set_number")

    def test_validator_resolves_the_premier_printing(self):
        resolved = vd.resolve_card(
            {"set": "JTL", "number": "258", "id": "JTL_258", "count": 3},
            self.card_db,
        )

        self.assertEqual(resolved, REPRINTED)

    def test_analysis_has_no_unresolved_cards(self):
        out = analysis.build_analysis(
            self.path, card_db_path=CARD_DB, generated_at=FIXED_TIME
        )

        self.assertEqual(out["deck"]["unresolved"], [])


if __name__ == "__main__":
    unittest.main()


class ResolveCardTest(unittest.TestCase):
    """`validate_deck` resolves like `CardIndex`: unknown stays unknown."""

    def setUp(self):
        self.card_db = sc.load_swu_cards(CARD_DB)

    def test_an_unknown_name_is_not_resolved(self):
        self.assertIsNone(
            vd.resolve_card({"name": "Totally Fake Card", "subtitle": ""}, self.card_db)
        )

    def test_a_typo_is_reported_instead_of_silently_corrected(self):
        card = self.card_db[FILLER]
        ref = {
            "name": "Totally Fake Card",
            "subtitle": "",
            "set": card["set"],
            "number": card["number"],
        }

        self.assertIsNone(vd.resolve_card(ref, self.card_db))

    def test_a_missing_subtitle_falls_back_to_set_and_number(self):
        ref = {
            "name": "Shield Generator Complex",
            "subtitle": "",
            "set": "HMW",
            "number": "022",
        }

        self.assertEqual(
            vd.resolve_card(ref, self.card_db),
            ("Shield Generator Complex", "Endor"),
        )

    def test_ids_are_normalised(self):
        ref = {"set": "JTL", "number": "58", "id": "JTL_58"}

        self.assertEqual(vd.resolve_card(ref, self.card_db), ("Academy Graduate", ""))

    def test_an_unknown_card_makes_the_deck_illegal(self):
        case = json.loads(
            (TESTS_DIR / "fixtures" / "poggle-blue-endor" / "deck.json").read_text(
                encoding="utf-8"
            )
        )
        case["mainDeck"][0]["card"]["title"] = "Totally Fake Card"
        case["mainDeck"][0]["card"]["subtitle"] = ""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.json"
            path.write_text(json.dumps(case), encoding="utf-8")
            ok, errors, _warnings = vd.validate_deck(path, verbose=False)

        self.assertFalse(ok)
        self.assertTrue(any("Could not resolve" in error for error in errors), errors)

    def test_a_leader_in_the_draw_deck_is_rejected(self):
        deck = {
            "leader": {"id": "HMW_012", "count": 1},
            "base": {"id": "HMW_022", "count": 1},
            "deck": [{"id": "HMW_177", "count": 50}, {"id": "HMW_012", "count": 1}],
            "sideboard": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.json"
            path.write_text(json.dumps(deck), encoding="utf-8")
            ok, errors, _warnings = vd.validate_deck(path, verbose=False)

        self.assertFalse(ok)
        self.assertTrue(
            any("cannot be in the draw deck" in error for error in errors), errors
        )

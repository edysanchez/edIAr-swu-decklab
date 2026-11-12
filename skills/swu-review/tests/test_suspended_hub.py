#!/usr/bin/env python3
"""SWU Competitive Hub suspended-list integration.

`fetch_suspended.py` parses the hub page into `data/swu/suspended.json`; the
rest of the skill consumes that snapshot through `suspended_list.load()`. These
tests use a synthetic fixture that mirrors the real page markup, so they never
touch the network.
"""

import contextlib
import io
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
sys.path.insert(0, str(TESTS_DIR))

import analysis  # noqa: E402
import constants as C  # noqa: E402
import fetch_suspended  # noqa: E402
import suspended_list  # noqa: E402
import swu_cards as sc  # noqa: E402
import validate_deck as vd  # noqa: E402
from test_suspended import build_swudb_deck, deck_with_suspended  # noqa: E402

FIXTURE = TESTS_DIR / "fixtures" / "competitivehub" / "suspended-list.html"
CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"
FIXED_TIME = "2026-11-03T00:00:00Z"

CAD_BANE = ("Cad Bane", "Still Faster Than You")
CHIMAERA = ("Chimaera", "A Frightening Reality")
NEGOTIATIONS = ("Aggressive Negotiations", "")
RANCOR_KEEPER = ("Rancor Keeper", "")


def snapshot_dict(entries, last_updated="2026-11-09", declared=None):
    return {
        "source": C.SUSPENDED_HUB_URL,
        "fetched_at": "2026-11-10T00:00:00Z",
        "last_updated": last_updated,
        "formats": {
            "Premier": {
                "count": len(entries) if declared is None else declared,
                "entries": entries,
            }
        },
    }


def entry(label, number=""):
    return {"label": label, "number": number}


class ParserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = FIXTURE.read_text(encoding="utf-8")
        cls.parsed = fetch_suspended.parse_page(cls.page)

    def test_reads_the_hub_last_updated_date(self):
        self.assertEqual(self.parsed["last_updated"], "2026-11-09")

    def test_reads_all_five_premier_cards(self):
        premier = self.parsed["formats"]["Premier"]
        self.assertEqual(premier["count"], 5)
        self.assertEqual(len(premier["entries"]), 5)
        fetch_suspended.check_page(self.parsed)

    def test_keeps_labels_and_card_numbers_verbatim(self):
        by_number = {
            e["number"]: e["label"] for e in self.parsed["formats"]["Premier"]["entries"]
        }
        self.assertEqual(by_number["0052"], "Chimaera, A Frightening Reality")
        self.assertEqual(by_number["0011"], "Cad Bane, Still Faster than You")

    def test_history_sections_are_ignored(self):
        self.assertEqual(set(self.parsed["formats"]), {"Premier", "Eternal"})
        labels = [e["label"] for e in self.parsed["formats"]["Premier"]["entries"]]
        self.assertNotIn("Boba Fett, Collecting the Bounty", labels)

    def test_integrity_check_rejects_a_count_mismatch(self):
        broken = self.page.replace(
            "5 cards are suspended in Premier Format",
            "6 cards are suspended in Premier Format",
        )
        with self.assertRaises(fetch_suspended.SuspendedPageError):
            fetch_suspended.check_page(fetch_suspended.parse_page(broken))

    def test_integrity_check_rejects_an_empty_list_by_default(self):
        parsed = {"last_updated": "2026-11-09", "formats": {"Premier": {"count": 0, "entries": []}}}
        with self.assertRaises(fetch_suspended.SuspendedPageError):
            fetch_suspended.check_page(parsed)


class ResolveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sc.load_swu_cards(CARD_DB)

    def test_hub_labels_resolve_case_insensitively(self):
        entries = [
            entry("Cad Bane, Still Faster than You", "0011"),
            entry("Chimaera, A Frightening Reality", "0052"),
        ]
        resolved, unresolved = suspended_list.resolve_entries(entries, self.db)
        self.assertEqual(resolved, {CAD_BANE, CHIMAERA})
        self.assertEqual(unresolved, [])

    def test_card_number_is_the_fallback_when_the_subtitle_changes(self):
        resolved, unresolved = suspended_list.resolve_entries(
            [entry("Cad Bane, Some Renamed Subtitle", "0011")], self.db
        )
        self.assertEqual(resolved, {CAD_BANE})
        self.assertEqual(unresolved, [])

    def test_unknown_cards_stay_unresolved(self):
        resolved, unresolved = suspended_list.resolve_entries(
            [entry("Not A Real Card, Nope", "9999")], self.db
        )
        self.assertEqual(resolved, set())
        self.assertEqual(len(unresolved), 1)


class PrecedenceTest(unittest.TestCase):
    def setUp(self):
        self.db = sc.load_swu_cards(CARD_DB)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.snapshot_path = Path(self.tmp.name) / "suspended.json"

    def write_snapshot(self, entries, **kwargs):
        self.snapshot_path.write_text(
            json.dumps(snapshot_dict(entries, **kwargs)), encoding="utf-8"
        )
        return self.snapshot_path

    def test_missing_snapshot_falls_back_to_the_builtin_registry(self):
        suspended = suspended_list.load(self.db, snapshot_path=self.snapshot_path)
        self.assertEqual(suspended.source, "builtin-registry")
        self.assertEqual(set(suspended.identities), set(C.SUSPENDED))
        self.assertTrue(any("not found" in w for w in suspended.warnings))

    def test_corrupt_snapshot_falls_back_to_the_builtin_registry(self):
        self.snapshot_path.write_text("{not json", encoding="utf-8")
        suspended = suspended_list.load(self.db, snapshot_path=self.snapshot_path)
        self.assertEqual(suspended.source, "builtin-registry")
        self.assertTrue(any("Could not read" in w for w in suspended.warnings))

    def test_snapshot_without_a_premier_section_falls_back(self):
        self.snapshot_path.write_text(
            json.dumps({"formats": {"Eternal": {"entries": []}}}), encoding="utf-8"
        )
        suspended = suspended_list.load(self.db, snapshot_path=self.snapshot_path)
        self.assertEqual(suspended.source, "builtin-registry")
        self.assertEqual(set(suspended.identities), set(C.SUSPENDED))
        self.assertTrue(any("no Premier section" in w for w in suspended.warnings))

    def test_snapshot_wins_over_the_registry(self):
        self.write_snapshot([entry("Rancor Keeper", "")])
        suspended = suspended_list.load(self.db, snapshot_path=self.snapshot_path)
        self.assertEqual(suspended.source, "hub-snapshot")
        self.assertEqual(set(suspended.identities), {RANCOR_KEEPER})
        self.assertTrue(any("missing from the built-in registry" in w for w in suspended.warnings))

    def test_unsuspension_is_reported_not_applied_silently(self):
        entries = [
            entry("Cad Bane, Still Faster than You", "0011"),
            entry("Koska Reeves, Warrior of Mandalore", "0079"),
        ]
        self.write_snapshot(entries)
        suspended = suspended_list.load(self.db, snapshot_path=self.snapshot_path)
        self.assertIn(CAD_BANE, suspended.identities)
        self.assertNotIn(CHIMAERA, suspended.identities)
        self.assertTrue(any("no longer lists" in w for w in suspended.warnings))

    def test_stale_snapshot_is_flagged(self):
        self.write_snapshot([entry("Chimaera, A Frightening Reality", "0052")],
                            last_updated="2020-01-01")
        suspended = suspended_list.load(self.db, snapshot_path=self.snapshot_path)
        self.assertTrue(any("days old" in w for w in suspended.warnings))

    def test_unresolvable_entry_is_flagged(self):
        self.write_snapshot([entry("Not A Real Card, Nope", "9999")])
        suspended = suspended_list.load(self.db, snapshot_path=self.snapshot_path)
        self.assertEqual(suspended.identities, frozenset())
        self.assertTrue(any("could not be resolved" in w for w in suspended.warnings))


class EntryPointsUseTheSnapshotTest(unittest.TestCase):
    """A card added to the snapshot must be enforced by both tools."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.snapshot_path = Path(self.tmp.name) / "suspended.json"
        self.snapshot_path.write_text(
            json.dumps(snapshot_dict([
                entry("Rancor Keeper", ""),
                entry("Cad Bane, Still Faster than You", "0011"),
            ])),
            encoding="utf-8",
        )
        patcher = mock.patch.object(
            C, "SUSPENDED_SNAPSHOT_PATH", str(self.snapshot_path)
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_deck(self, deck):
        path = Path(self.tmp.name) / "deck.json"
        path.write_text(json.dumps(deck), encoding="utf-8")
        return path

    def test_analysis_blocks_a_card_only_the_snapshot_lists(self):
        out = analysis.build_analysis(
            self.write_deck(build_swudb_deck()),
            card_db_path=CARD_DB,
            generated_at=FIXED_TIME,
        )
        check = next(c for c in out["legality"]["checks"] if c["id"] == "suspended")
        self.assertFalse(check["ok"], check)
        self.assertIn("Rancor Keeper", check["detail"])

    def test_validate_deck_blocks_a_card_only_the_snapshot_lists(self):
        ok, errors, _warnings = vd.validate_deck(
            self.write_deck(build_swudb_deck()), verbose=False
        )
        self.assertFalse(ok, errors)
        self.assertTrue(any("Rancor Keeper" in e for e in errors), errors)

    def test_suspended_leader_from_the_snapshot_is_blocked(self):
        record = next(r for r in C.SUSPENDED_CARDS if r["type"] == "Leader")
        ok, errors, _warnings = vd.validate_deck(
            self.write_deck(deck_with_suspended(record)), verbose=False
        )
        self.assertFalse(ok, errors)
        self.assertTrue(any("Cad Bane" in e for e in errors), errors)


class ValidateDeckWarningOutputTest(unittest.TestCase):
    """Snapshot warnings must be visible in the default text output."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        missing = Path(self.tmp.name) / "no-such-snapshot.json"
        patcher = mock.patch.object(C, "SUSPENDED_SNAPSHOT_PATH", str(missing))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.deck = Path(self.tmp.name) / "deck.json"
        self.deck.write_text(json.dumps(build_swudb_deck()), encoding="utf-8")

    def test_verbose_output_prints_the_snapshot_warning(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            ok, errors, warnings = vd.validate_deck(self.deck, verbose=True)
        self.assertTrue(ok, errors)
        self.assertTrue(any("snapshot not found" in w for w in warnings), warnings)
        output = buffer.getvalue()
        self.assertIn("WARNINGS", output)
        self.assertIn("snapshot not found", output)

    def test_quiet_output_stays_silent(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            vd.validate_deck(self.deck, verbose=False)
        self.assertEqual(buffer.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

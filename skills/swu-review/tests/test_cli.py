#!/usr/bin/env python3
"""End-to-end tests for the ``swu_analyze.py`` CLI."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
REPO_ROOT = SKILL_DIR.parents[1]
SCRIPT = SKILL_DIR / "scripts" / "swu_analyze.py"
FIXTURES_DIR = TESTS_DIR / "fixtures"
CASE = FIXTURES_DIR / "poggle-blue-endor" / "deck.json"
CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"


def run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


class CliTest(unittest.TestCase):
    def test_json_to_stdout_is_pure_json(self):
        result = run(CASE, "--card-db", CARD_DB, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

        data = json.loads(result.stdout)
        self.assertEqual(data["schema_version"], "0.1.0")
        self.assertEqual(data["composition"]["n"], 50)

    def test_writes_json_and_report_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "analysis.json"
            report_path = Path(tmp) / "report.md"
            result = run(
                CASE,
                "--card-db", CARD_DB,
                "--json", json_path,
                "--report", report_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json_path.exists())
            self.assertTrue(report_path.exists())

            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["input"]["n"], 50)

            report = report_path.read_text(encoding="utf-8")
            self.assertIn("## Provenance", report)
            self.assertIn("## Draw odds", report)

    def test_max_round_limits_draw_odds(self):
        result = run(CASE, "--card-db", CARD_DB, "--json", "--max-round", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["draw_odds"]["rounds"], [0, 1, 2])
        self.assertEqual(len(data["draw_odds"]["per_card"][0]["p"]), 3)

    def test_illegal_deck_still_produces_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck = json.loads(CASE.read_text(encoding="utf-8"))
            deck["mainDeck"][0]["card"]["title"] = "Totally Fake Card"
            deck["mainDeck"][0]["card"]["subtitle"] = ""
            deck["mainDeck"][0]["card"]["cardNumber"] = 999
            path = Path(tmp) / "fake.json"
            path.write_text(json.dumps(deck), encoding="utf-8")

            result = run(path, "--card-db", CARD_DB, "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertFalse(data["legality"]["ok"])
            self.assertEqual(len(data["deck"]["unresolved"]), 1)

    def test_missing_deck_fails_cleanly(self):
        result = run(REPO_ROOT / "does-not-exist.json", "--card-db", CARD_DB, "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("does-not-exist.json", result.stderr)

    def test_both_streams_to_stdout_is_rejected(self):
        result = run(CASE, "--card-db", CARD_DB, "--json", "--report")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stdout", result.stderr)


if __name__ == "__main__":
    unittest.main()

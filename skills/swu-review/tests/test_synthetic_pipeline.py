#!/usr/bin/env python3
"""Pipeline tests against the checked-in synthetic catalogue.

These tests do not read ``data/`` and do not contain real card text or images.
They are the coverage that survives a clean checkout.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
from support import (  # noqa: E402
    SYNTHETIC_CARD_DB,
    SYNTHETIC_DECK,
    SYNTHETIC_ROTATED_DECK,
)

SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import analysis  # noqa: E402
import render_report  # noqa: E402

FIXED_TIME = "2026-01-01T00:00:00Z"

try:
    import jsonschema
except ImportError:  # pragma: no cover - clean checkout may not have it
    jsonschema = None


class SyntheticPipelineTest(unittest.TestCase):
    def build(self, deck=SYNTHETIC_DECK):
        return analysis.build_analysis(
            deck,
            card_db_path=SYNTHETIC_CARD_DB,
            generated_at=FIXED_TIME,
        )

    def test_legal_deck_is_green(self):
        out = self.build()
        self.assertTrue(out["legality"]["ok"], out["legality"]["errors"])
        self.assertEqual(out["input"]["n"], 50)
        self.assertEqual(out["deck"]["unresolved"], [])

    def test_rotated_set_is_illegal(self):
        out = self.build(SYNTHETIC_ROTATED_DECK)
        self.assertFalse(out["legality"]["ok"])
        self.assertTrue(
            any("SOR" in error or "non-premier" in error.lower() for error in out["legality"]["errors"]),
            out["legality"]["errors"],
        )

    def test_report_is_generated(self):
        text = render_report.render_report(self.build())
        self.assertIn("## Legality", text)
        self.assertIn("### Aspect penalty", text)

    def test_fixture_has_no_card_text(self):
        out = self.build()
        self.assertTrue(all(card.get("text") is None for card in out["cards"]))

    @unittest.skipUnless(jsonschema is not None, "jsonschema not installed")
    def test_schema_validates(self):
        schema = json.loads((SKILL_DIR / "analysis.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(instance=self.build(), schema=schema)


class SyntheticCliTest(unittest.TestCase):
    def test_cli_reads_the_synthetic_catalogue(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "swu_analyze.py"),
                str(SYNTHETIC_DECK),
                "--card-db",
                str(SYNTHETIC_CARD_DB),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertTrue(out["legality"]["ok"], out["legality"]["errors"])
        self.assertEqual(out["input"]["n"], 50)

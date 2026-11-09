#!/usr/bin/env python3
"""Tests for the Markdown renderer.

The renderer is a pure view over ``analysis.json``. These tests pin two
properties that matter more than layout:

1. every section exists, in a fixed order;
2. no number is recomputed — mutating the JSON must change the report.
"""

import copy
import json
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
REPO_ROOT = SKILL_DIR.parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import analysis  # noqa: E402
import render_report  # noqa: E402  (fails first: RED)

FIXTURES_DIR = TESTS_DIR / "fixtures"
CASE = FIXTURES_DIR / "poggle-blue-endor" / "deck.json"
CARD_DB = REPO_ROOT / "data" / "swudb" / "cards_normalized.json"
FIXED_TIME = "2026-11-03T00:00:00Z"

SECTIONS = [
    "## Provenance",
    "## Legality",
    "## Composition snapshot",
    "## Card sheets",
    "## Draw odds",
    "## Findings",
    "## Limitations",
]


def build():
    return analysis.build_analysis(
        CASE,
        card_db_path=CARD_DB,
        generated_at=FIXED_TIME,
    )


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.analysis = build()
        self.report = render_report.render_report(self.analysis)

    def test_sections_appear_in_order(self):
        positions = [self.report.index(heading) for heading in SECTIONS]
        self.assertEqual(positions, sorted(positions), positions)

    def test_title_names_the_leader(self):
        self.assertIn("# SWU Review", self.report)
        self.assertIn("Poggle the Lesser", self.report)

    def test_provenance_is_reported_verbatim(self):
        self.assertIn(self.analysis["generated_at"], self.report)
        self.assertIn(self.analysis["db"]["data_as_of"], self.report)
        self.assertIn(self.analysis["db"]["schema_hash"], self.report)
        self.assertIn(self.analysis["input"]["sha256"], self.report)
        self.assertIn(self.analysis["rules_version"], self.report)

    def test_legality_errors_are_listed(self):
        broken = copy.deepcopy(self.analysis)
        broken["legality"]["ok"] = False
        broken["legality"]["errors"] = ["Draw deck must be at least 50 cards (found: 49)"]
        report = render_report.render_report(broken)
        self.assertIn("Draw deck must be at least 50 cards (found: 49)", report)

    def test_composition_numbers_come_from_json(self):
        mutated = copy.deepcopy(self.analysis)
        mutated["composition"]["n"] = 49
        mutated["composition"]["arenas"]["space_pct"] = 12.3
        mutated["composition"]["price"]["total"] = 99.99
        report = render_report.render_report(mutated)

        self.assertIn("| Main deck | 49 |", report)
        self.assertIn("12.3", report)
        self.assertIn("99.99", report)

    def test_curve_uses_json_percentages(self):
        mutated = copy.deepcopy(self.analysis)
        mutated["composition"]["curve_pct"]["2"] = 36.0
        report = render_report.render_report(mutated)
        self.assertIn("36.0", report)

    def test_card_sheets_include_text_and_flags(self):
        self.assertIn("Poggle the Lesser", self.report)
        self.assertIn("Shield Generator Complex", self.report)
        self.assertIn("Rancor Keeper", self.report)

        sheet = next(c for c in self.analysis["cards"] if c["identity"] == "Rancor Keeper")
        if sheet["text"]:
            self.assertIn(sheet["text"], self.report)

    def test_missing_text_is_explicit_and_never_invented(self):
        mutated = copy.deepcopy(self.analysis)
        card = next(c for c in mutated["cards"] if c["zone"] == "main")
        card["text"] = None
        card["text_status"] = "missing"
        report = render_report.render_report(mutated)

        self.assertIn("Text missing from local database", report)
        self.assertNotIn("frontText", report)

    def test_empty_text_is_explicit(self):
        mutated = copy.deepcopy(self.analysis)
        card = next(c for c in mutated["cards"] if c["zone"] == "main")
        card["text"] = ""
        card["text_status"] = "present"
        report = render_report.render_report(mutated)

        self.assertIn("No card text in local database", report)
        self.assertNotIn("> \n", report)

    def test_card_sheets_nest_under_zone_headings(self):
        self.assertIn("### Leader", self.report)
        self.assertIn("#### Poggle the Lesser", self.report)
        self.assertIn("#### Rancor Keeper", self.report)

    def test_missing_numeric_stats_render_as_dash(self):
        mutated = copy.deepcopy(self.analysis)
        base = next(c for c in mutated["cards"] if c["zone"] == "base")
        base["cost"] = None
        base["power"] = None
        report = render_report.render_report(mutated)
        self.assertIn("| Cost | — |", report)
        self.assertIn("| Power | — |", report)

    def test_draw_odds_table_uses_json_values(self):
        mutated = copy.deepcopy(self.analysis)
        mutated["draw_odds"]["per_card"][0]["p"][0] = 11.1
        report = render_report.render_report(mutated)
        self.assertIn("11.1", report)

    def test_finding_evidence_is_rendered(self):
        self.assertIn("arena-imbalance", self.report)
        self.assertIn("Starlit Purrgil", self.report)
        self.assertIn("5.1", self.report)

    def test_limitations_section_lists_every_id(self):
        for limitation in self.analysis["limitations"]:
            self.assertIn(limitation["id"], self.report)

    def test_out_of_scope_is_listed(self):
        self.assertIn("## Out of scope", self.report)
        for item in self.analysis["out_of_scope"]:
            self.assertIn(item["id"], self.report)

    def test_data_health_banner_precedes_sections(self):
        self.assertIn("Data health", self.report)
        self.assertLess(self.report.index("Data health"), self.report.index("## Provenance"))

    def test_blocking_limitation_is_called_out(self):
        mutated = copy.deepcopy(self.analysis)
        mutated["limitations"].append({
            "id": "synthetic-blocker",
            "category": "data",
            "impact": "blocking",
            "statement": "Synthetic blocking limitation.",
            "affects": ["composition"],
            "detail": "",
            "mitigation": "",
        })
        report = render_report.render_report(mutated)
        self.assertIn("synthetic-blocker", report)
        self.assertIn("blocking", report)

    def test_render_is_deterministic(self):
        first = render_report.render_report(self.analysis)
        second = render_report.render_report(copy.deepcopy(self.analysis))
        self.assertEqual(first, second)

    def test_render_does_not_mutate_input(self):
        before = json.dumps(self.analysis, sort_keys=True)
        render_report.render_report(self.analysis)
        after = json.dumps(self.analysis, sort_keys=True)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""SWU Competitive Hub legal-set page: parser and freshness snapshot.

`fetch_legal_sets.py` turns the hub page into `data/swu/legal-sets.json`, which
`legal_sets.py` consumes. These tests use a synthetic fixture that mirrors the
live markup, so they never touch the network.

The contract that matters: the legal list is the `Today` list, never the union
of the blocks. A rotated set appears in its block (with a release date) but must
not become legal.
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(TESTS_DIR))

import fetch_legal_sets  # noqa: E402  (fails first: RED)
import legal_sets  # noqa: E402

FIXTURE = TESTS_DIR / "fixtures" / "competitivehub" / "premier-format-and-rotation.html"
LEGAL = ["ASH", "HMW", "IBH", "JTL", "LAW", "LOF", "SEC"]


def page():
    return FIXTURE.read_text(encoding="utf-8")


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.parsed = fetch_legal_sets.parse_page(page())

    def test_reads_the_legal_list(self):
        self.assertEqual(sorted(self.parsed["legal"]), LEGAL)

    def test_reads_the_page_date_as_as_of(self):
        self.assertEqual(self.parsed["as_of"], "2026-11-12")

    def test_rotated_sets_are_not_legal_but_keep_their_release(self):
        self.assertNotIn("SOR", self.parsed["legal"])
        releases = {
            p["code"]: p.get("release") or p.get("legal_from")
            for p in self.parsed["products"]
        }
        self.assertEqual(releases["SOR"], "2024-03-08")

    def test_reads_the_next_change(self):
        self.assertEqual(
            self.parsed["next_change"],
            {"product": "Icons 2027 Edition", "legal_from": "2026-11-20"},
        )

    def test_reads_release_dates(self):
        releases = {p["code"]: p.get("release") for p in self.parsed["products"]}
        self.assertEqual(releases["JTL"], "2025-03-14")
        self.assertEqual(releases["ASH"], "2026-07-17")

    def test_upcoming_set_carries_a_legal_from_date(self):
        # Unreleased sets say "Legal from <date>", not "Release: <date>".
        products = {p["code"]: p for p in self.parsed["products"]}
        self.assertEqual(products["IC27"].get("legal_from"), "2026-11-20")
        self.assertNotIn("release", products["IC27"])

    def test_products_are_deduplicated(self):
        codes = [p["code"] for p in self.parsed["products"]]
        self.assertEqual(len(codes), len(set(codes)))


class IntegrityTest(unittest.TestCase):
    def test_rejects_an_empty_legal_list(self):
        parsed = {
            "as_of": "2026-11-12",
            "legal": [],
            "next_change": None,
            "products": [],
        }

        with self.assertRaises(fetch_legal_sets.LegalSetsPageError):
            fetch_legal_sets.check_page(parsed)

    def test_rejects_a_page_without_a_date(self):
        parsed = {
            "as_of": None,
            "legal": ["JTL"],
            "next_change": None,
            "products": [],
        }

        with self.assertRaises(fetch_legal_sets.LegalSetsPageError):
            fetch_legal_sets.check_page(parsed)

    def test_rejects_a_duplicated_code(self):
        parsed = {
            "as_of": "2026-11-12",
            "legal": ["JTL", "JTL"],
            "next_change": None,
            "products": [],
        }

        with self.assertRaises(fetch_legal_sets.LegalSetsPageError):
            fetch_legal_sets.check_page(parsed)


class EntryPointTest(unittest.TestCase):
    def test_dry_run_prints_the_snapshot_and_writes_nothing(self):
        out = io.StringIO()
        with mock.patch.object(fetch_legal_sets, "fetch", return_value=page()):
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                code = fetch_legal_sets.main(["--dry-run"])

        self.assertEqual(code, 0)
        snapshot = json.loads(out.getvalue())
        self.assertEqual(sorted(snapshot["legal"]), LEGAL)

    def test_written_snapshot_round_trips_through_legal_sets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legal-sets.json"
            with mock.patch.object(fetch_legal_sets, "fetch", return_value=page()):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    code = fetch_legal_sets.main(["--out", str(path)])

            self.assertEqual(code, 0)
            result = legal_sets.load(snapshot_path=path)

        self.assertEqual(result.source, "hub-snapshot")
        self.assertEqual(sorted(result.codes), LEGAL)
        self.assertFalse(result.is_legal("SOR"))
        self.assertTrue(result.is_legal("HMW"))


if __name__ == "__main__":
    unittest.main()

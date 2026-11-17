#!/usr/bin/env python3
"""`fetch_cards.normalize_cards` must not lose printings.

The card database keeps one entry per printed name + subtitle, but `rules.md`
says legality follows the card version: a reprint in a Premier-legal product
legalises the card. Collapsing two printings onto one identity without recording
them makes that rule impossible to apply.

These tests feed synthetic API rows, so they never touch the network.
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

import constants as C  # noqa: E402
import fetch_cards  # noqa: E402
import swu_cards as sc  # noqa: E402

SWUDB_DIR = Path(C.CARD_DB_PATH).parent
CACHED_SETS = ["JTL", "LOF", "IBH", "SEC", "LAW", "ASH", "HMW"]


def row(set_code, number, name="Adept ARC-170", subtitle="", **overrides):
    data = {
        "Name": name,
        "Subtitle": subtitle,
        "Set": set_code,
        "Number": number,
        "Type": "Unit",
        "VariantType": "Normal",
        "Aspects": ["Command"],
    }
    data.update(overrides)
    return data


class NormalizePrintingsTest(unittest.TestCase):
    def test_single_printing_does_not_ship_a_printings_field(self):
        cards = fetch_cards.normalize_cards({"JTL": {"data": [row("JTL", "114")]}})

        card = cards["Adept ARC-170"]
        self.assertEqual(card["set"], "JTL")
        self.assertNotIn("printings", card)

    def test_duplicate_identity_keeps_every_printing(self):
        cards = fetch_cards.normalize_cards(
            {
                "JTL": {"data": [row("JTL", "114")]},
                "HMW": {"data": [row("HMW", "177")]},
            }
        )

        card = cards["Adept ARC-170"]
        self.assertEqual(card["printings"], ["JTL", "HMW"])
        self.assertEqual(card["set"], "HMW")  # last fetched wins for display

    def test_repeated_printing_is_not_duplicated(self):
        cards = fetch_cards.normalize_cards(
            {
                "JTL": {"data": [row("JTL", "114")]},
                "HMW": {"data": [row("HMW", "177")]},
            }
        )

        self.assertEqual(cards["Adept ARC-170"]["printings"], ["JTL", "HMW"])
        self.assertEqual(len(cards["Adept ARC-170"]["printings"]), 2)

    def test_tokens_and_variants_are_excluded(self):
        cards = fetch_cards.normalize_cards(
            {
                "JTL": {
                    "data": [
                        row("JTL", "001", name="Token Unit", Type="Token Unit"),
                        row("JTL", "002", name="Foil Only", VariantType="Foil"),
                        row("JTL", "003", name="Kept"),
                    ]
                }
            }
        )

        self.assertEqual(sorted(cards), ["Kept"])


class RebuildTest(unittest.TestCase):
    """Rebuilding from the raw set files must not change the catalogue.

    The normalised file is a derived artefact: `cards_normalized.json` should
    always be reproducible from the per-set payloads the fetcher stores. This is
    the guard that lets the fetch flow be reworked without moving every other
    test.
    """

    def setUp(self):
        missing = [
            code for code in CACHED_SETS if not (SWUDB_DIR / f"{code}.json").exists()
        ]
        if missing:
            self.skipTest(f"raw set files not cached: {missing}")

    def test_rebuild_reproduces_the_cached_normalized_file(self):
        rebuilt = fetch_cards.rebuild_normalized()

        current = json.loads(
            (SWUDB_DIR / "cards_normalized.json").read_text(encoding="utf-8")
        )

        self.assertEqual(rebuilt, current)

    def test_rebuild_is_deterministic(self):
        self.assertEqual(fetch_cards.rebuild_normalized(), fetch_cards.rebuild_normalized())


class CardPrintingsTest(unittest.TestCase):
    def test_printings_field_wins(self):
        card = {"set": "HMW", "printings": ["JTL", "HMW"]}
        self.assertEqual(sc.card_printings(card), ["JTL", "HMW"])

    def test_falls_back_to_set(self):
        self.assertEqual(sc.card_printings({"set": "JTL"}), ["JTL"])

    def test_empty_when_unknown(self):
        self.assertEqual(sc.card_printings({}), [])


if __name__ == "__main__":
    unittest.main()


def payload(numbers, set_code="IC27"):
    return {
        "total_cards": len(numbers),
        "data": [
            {
                "Name": f"Card {number}",
                "Subtitle": "",
                "Set": set_code,
                "Number": number,
                "Type": "Unit",
                "VariantType": "Normal",
            }
            for number in numbers
        ],
    }


INDEX = {
    "JTL": {"setId": "JTL", "numberCards": 2},
    "IC27": {"setId": "IC27", "numberCards": 3},
}


class EnsureSetsTest(unittest.TestCase):
    """Download only what is missing, and never trust a partial payload."""

    def setUp(self):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.dir = Path(handle.name)
        self.out = self.dir / "cards_normalized.json"

    def write_set(self, code, numbers, set_code=None):
        path = self.dir / f"{code}.json"
        path.write_text(json.dumps(payload(numbers, set_code or code)), encoding="utf-8")
        return path

    def write_index(self, data):
        (self.dir / "sets_index.json").write_text(json.dumps(data), encoding="utf-8")

    def run_ensure(self, codes, fetcher):
        return fetch_cards.ensure_sets(
            codes,
            sets_dir=self.dir,
            set_index=INDEX,
            fetcher=fetcher,
            out_path=self.out,
        )

    def test_downloads_only_the_missing_set(self):
        self.write_set("JTL", ["001", "002"])
        self.write_index({"JTL": {"expected": 2, "received": 2, "complete": True}})
        calls = []

        def fetcher(code, timeout=60):
            calls.append(code)
            return payload(["001", "002", "003"])

        status = self.run_ensure(["JTL", "IC27"], fetcher)

        self.assertEqual(calls, ["IC27"])
        self.assertEqual(status["JTL"]["status"], "cached")
        self.assertEqual(status["IC27"]["status"], "fetched")
        self.assertTrue((self.dir / "IC27.json").exists())

    def test_incomplete_payload_is_not_stored(self):
        def fetcher(code, timeout=60):
            return payload(["001", "002"])  # 2 of 3

        status = self.run_ensure(["IC27"], fetcher)

        self.assertEqual(status["IC27"]["status"], "incomplete")
        self.assertFalse((self.dir / "IC27.json").exists())

    def test_failed_download_leaves_the_set_absent(self):
        def fetcher(code, timeout=60):
            raise OSError("network down")

        status = self.run_ensure(["IC27"], fetcher)

        self.assertEqual(status["IC27"]["status"], "failed")
        self.assertFalse((self.dir / "IC27.json").exists())

    def test_sets_index_records_completeness(self):
        def fetcher(code, timeout=60):
            return payload(["001", "002", "003"])

        self.run_ensure(["IC27"], fetcher)

        index = json.loads((self.dir / "sets_index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["IC27"]["expected"], 3)
        self.assertEqual(index["IC27"]["received"], 3)
        self.assertTrue(index["IC27"]["complete"])

    def test_rebuild_skips_sets_marked_incomplete(self):
        self.write_set("JTL", ["001", "002"])
        self.write_set("IC27", ["001", "002"])
        self.write_index(
            {
                "JTL": {"expected": 2, "received": 2, "complete": True},
                "IC27": {"expected": 3, "received": 2, "complete": False},
            }
        )

        cards = fetch_cards.rebuild_normalized(sets_dir=self.dir)

        self.assertIn("Card 001", cards)
        self.assertEqual(cards["Card 001"]["set"], "JTL")


class CompleteSetsTest(unittest.TestCase):
    """A set counts as present only when it is complete and on disk."""

    def setUp(self):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.dir = Path(handle.name)

    def write_set(self, code, numbers=("001",)):
        (self.dir / f"{code}.json").write_text(
            json.dumps(payload(numbers, code)), encoding="utf-8"
        )

    def write_index(self, data):
        (self.dir / "sets_index.json").write_text(json.dumps(data), encoding="utf-8")

    def test_complete_set_with_a_file_counts(self):
        self.write_set("JTL", ("001", "002"))
        self.write_index({"JTL": {"expected": 2, "received": 2, "complete": True}})

        self.assertEqual(sc.complete_sets(self.dir), {"JTL"})

    def test_incomplete_set_does_not_count(self):
        self.write_set("IC27", ("001",))
        self.write_index({"IC27": {"expected": 3, "received": 1, "complete": False}})

        self.assertEqual(sc.complete_sets(self.dir), set())

    def test_complete_entry_without_the_file_does_not_count(self):
        self.write_index({"LOF": {"expected": 2, "received": 2, "complete": True}})

        self.assertEqual(sc.complete_sets(self.dir), set())

    def test_unknown_completeness_does_not_count(self):
        self.write_set("JTL", ("001",))
        self.write_index({"JTL": {"expected": None, "received": 1, "complete": None}})

        self.assertEqual(sc.complete_sets(self.dir), set())

    def test_absent_index_is_empty_not_an_error(self):
        self.write_set("JTL", ("001",))

        self.assertEqual(sc.complete_sets(self.dir), set())


class FakeResponse:
    def __init__(self, data):
        self._data = json.dumps(data).encode("utf-8")

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


SETS_PAYLOAD = [
    {"setId": "JTL", "fullName": "Jump To Lightspeed", "numberCards": 262, "isBaseSet": True},
    {"setId": "IC27", "fullName": "Icons 2027", "numberCards": 194, "isBaseSet": True},
    {"setId": "JTLOP", "fullName": "JTL OP Promo", "numberCards": 40, "parentSetId": "JTL"},
]


class SetIndexTest(unittest.TestCase):
    def test_reads_the_bare_list_response(self):
        with mock.patch.object(fetch_cards, "urlopen", return_value=FakeResponse(SETS_PAYLOAD)):
            index = fetch_cards.fetch_set_index()

        self.assertEqual(sorted(index), ["IC27", "JTL", "JTLOP"])
        self.assertEqual(index["JTL"]["numberCards"], 262)
        self.assertTrue(index["JTL"]["isBaseSet"])
        self.assertFalse(index["JTLOP"]["isBaseSet"])
        self.assertEqual(index["JTLOP"]["parentSetId"], "JTL")

    def test_empty_response_is_an_error(self):
        with mock.patch.object(fetch_cards, "urlopen", return_value=FakeResponse([])):
            with self.assertRaises(fetch_cards.FetchError):
                fetch_cards.fetch_set_index()

    def test_default_selection_is_base_sets(self):
        index = {"JTL": {"isBaseSet": True}, "IC27": {"isBaseSet": True}, "JTLOP": {"isBaseSet": False}}

        self.assertEqual(fetch_cards.select_sets(index), ["IC27", "JTL"])

    def test_all_includes_promos(self):
        index = {"JTL": {"isBaseSet": True}, "JTLOP": {"isBaseSet": False}}

        self.assertEqual(fetch_cards.select_sets(index, include_all=True), ["JTL", "JTLOP"])

    def test_explicit_selection_is_normalised(self):
        index = {"JTL": {"isBaseSet": True}, "IC27": {"isBaseSet": True}}

        self.assertEqual(fetch_cards.select_sets(index, sets=" jtl , IC27 "), ["JTL", "IC27"])

    def test_unknown_code_is_rejected(self):
        with self.assertRaises(fetch_cards.FetchError):
            fetch_cards.select_sets({"JTL": {}}, sets="JTL,SOR")


class MainTest(unittest.TestCase):
    def setUp(self):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.dir = Path(handle.name)
        patcher = mock.patch.object(
            fetch_cards, "CARD_DB_PATH", str(self.dir / "cards_normalized.json")
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def patch_index(self, index=None):
        patcher = mock.patch.object(
            fetch_cards, "fetch_set_index", return_value=index or {"JTL": {"numberCards": 2, "isBaseSet": True}}
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_dry_run_writes_nothing(self):
        self.patch_index()
        fetcher = mock.Mock()
        with mock.patch.object(fetch_cards, "fetch_set", fetcher):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = fetch_cards.main(["--dry-run"])

        self.assertEqual(code, 0)
        fetcher.assert_not_called()
        self.assertEqual(list(self.dir.iterdir()), [])

    def test_downloads_and_writes_meta(self):
        self.patch_index()
        with mock.patch.object(
            fetch_cards, "fetch_set", side_effect=lambda code: payload(["001", "002"], code)
        ):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = fetch_cards.main([])

        self.assertEqual(code, 0)
        self.assertTrue((self.dir / "JTL.json").exists())
        meta = json.loads((self.dir / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["sets"], ["JTL"])
        self.assertEqual(meta["total_unique_cards"], 2)

    def test_incomplete_set_makes_the_run_fail(self):
        self.patch_index({"JTL": {"numberCards": 3, "isBaseSet": True}})
        with mock.patch.object(
            fetch_cards, "fetch_set", side_effect=lambda code: payload(["001"], code)
        ):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = fetch_cards.main([])

        self.assertEqual(code, 1)
        self.assertFalse((self.dir / "JTL.json").exists())

    def test_refresh_downloads_a_cached_set_again(self):
        (self.dir / "JTL.json").write_text(
            json.dumps(payload(["001", "002"], "JTL")), encoding="utf-8"
        )
        calls = []

        def fetcher(code, timeout=60):
            calls.append(code)
            return payload(["001", "002"], code)

        status = fetch_cards.ensure_sets(
            ["JTL"],
            sets_dir=self.dir,
            set_index={"JTL": {"numberCards": 2}},
            fetcher=fetcher,
            refresh=True,
        )

        self.assertEqual(calls, ["JTL"])
        self.assertEqual(status["JTL"]["status"], "fetched")


class IsolationTest(unittest.TestCase):
    """A fetch into a temporary directory must not touch the real cache."""

    def test_ensure_sets_writes_the_catalogue_next_to_the_sets(self):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        tmp = Path(handle.name)

        with mock.patch.object(fetch_cards, "fetch_set", side_effect=lambda code: payload(["001"], code)):
            fetch_cards.ensure_sets(
                ["IC27"],
                sets_dir=tmp,
                set_index={"IC27": {"numberCards": 1}},
            )

        self.assertTrue((tmp / "cards_normalized.json").exists())
        self.assertEqual((tmp / "cards_normalized.json").parent, tmp)

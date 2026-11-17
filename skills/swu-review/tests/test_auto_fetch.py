#!/usr/bin/env python3
"""The CLIs repair local catalogue gaps; the library never touches the network.

`refresh_catalogue` only works from the set list recorded by the last
`fetch_cards.py` run, so it cannot discover new products on its own: it repairs
what the catalogue is supposed to contain. With nothing missing it makes no
network call.
"""

import json
import sys
from datetime import datetime
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
from support import requires_catalogue  # noqa: E402
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import fetch_cards  # noqa: E402
import swu_analyze  # noqa: E402
import validate_deck as vd  # noqa: E402

DECK = TESTS_DIR / "fixtures" / "poggle-blue-endor" / "deck.json"


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


class RefreshCatalogueTest(unittest.TestCase):
    def setUp(self):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.dir = Path(handle.name)

    def write_json(self, name, data):
        (self.dir / name).write_text(json.dumps(data), encoding="utf-8")

    def write_set(self, code, numbers=("001",)):
        self.write_json(f"{code}.json", payload(numbers, code))

    def test_without_a_catalogue_file_nothing_is_downloaded(self):
        network = mock.Mock(side_effect=AssertionError("no network expected"))
        with mock.patch.object(fetch_cards, "fetch_set_index", network):
            result = fetch_cards.refresh_catalogue(sets_dir=self.dir)

        self.assertEqual(result["status"], "unknown")
        network.assert_not_called()

    def test_up_to_date_catalogue_makes_no_request(self):
        self.write_json("catalogue.json", {"base_sets": ["JTL"]})
        self.write_set("JTL")
        self.write_json("sets_index.json", {"JTL": {"expected": 1, "received": 1, "complete": True}})
        network = mock.Mock(side_effect=AssertionError("no network expected"))

        with mock.patch.object(fetch_cards, "fetch_set_index", network):
            result = fetch_cards.refresh_catalogue(sets_dir=self.dir)

        self.assertEqual(result["status"], "up-to-date")
        network.assert_not_called()

    def test_missing_set_is_downloaded(self):
        self.write_json("catalogue.json", {"base_sets": ["JTL", "IC27"]})
        self.write_set("JTL")
        self.write_json("sets_index.json", {"JTL": {"expected": 1, "received": 1, "complete": True}})

        index = {"JTL": {"numberCards": 1}, "IC27": {"numberCards": 2}}
        with mock.patch.object(fetch_cards, "fetch_set_index", return_value=index), \
                mock.patch.object(fetch_cards, "fetch_set", side_effect=lambda code: payload(["001", "002"], code)):
            result = fetch_cards.refresh_catalogue(sets_dir=self.dir)

        self.assertEqual(result["status"], "refreshed")
        self.assertEqual(result["fetched"], ["IC27"])
        self.assertTrue((self.dir / "IC27.json").exists())

    def test_incomplete_download_is_reported_not_stored(self):
        self.write_json("catalogue.json", {"base_sets": ["IC27"]})
        index = {"IC27": {"numberCards": 3}}

        with mock.patch.object(fetch_cards, "fetch_set_index", return_value=index), \
                mock.patch.object(fetch_cards, "fetch_set", side_effect=lambda code: payload(["001"], code)):
            result = fetch_cards.refresh_catalogue(sets_dir=self.dir)

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["incomplete"], ["IC27"])
        self.assertEqual(result["missing"], [])
        self.assertFalse((self.dir / "IC27.json").exists())

    def test_a_recently_checked_incomplete_set_is_not_retried(self):
        self.write_json("catalogue.json", {"base_sets": ["IC27"]})
        self.write_json(
            "sets_index.json",
            {
                "IC27": {
                    "expected": 194,
                    "received": 57,
                    "complete": False,
                    "checked_at": datetime.now().isoformat(),
                }
            },
        )
        network = mock.Mock(side_effect=AssertionError("no network expected"))

        with mock.patch.object(fetch_cards, "fetch_set_index", network):
            result = fetch_cards.refresh_catalogue(sets_dir=self.dir)

        self.assertEqual(result["incomplete"], ["IC27"])
        network.assert_not_called()

    def test_network_failure_is_reported_not_raised(self):
        self.write_json("catalogue.json", {"base_sets": ["IC27"]})

        with mock.patch.object(
            fetch_cards, "fetch_set_index", side_effect=fetch_cards.FetchError("down")
        ):
            result = fetch_cards.refresh_catalogue(sets_dir=self.dir)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["missing"], ["IC27"])


@requires_catalogue
class EntryPointTest(unittest.TestCase):
    def test_validate_deck_does_not_fetch_by_default(self):
        with mock.patch.object(fetch_cards, "refresh_catalogue") as refresh:
            vd.validate_deck(DECK, verbose=False)

        refresh.assert_not_called()

    def test_validate_deck_fetches_when_asked(self):
        with mock.patch.object(
            fetch_cards,
            "refresh_catalogue",
            return_value={"fetched": [], "missing": []},
        ) as refresh:
            vd.validate_deck(DECK, verbose=False, auto_fetch=True)

        refresh.assert_called_once()

    def test_swu_analyze_skips_the_refresh_with_no_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "analysis.json"
            with mock.patch.object(fetch_cards, "refresh_catalogue") as refresh:
                with mock.patch("sys.stderr"):
                    code = swu_analyze.main([str(DECK), "--json", str(out), "--no-fetch"])

        self.assertEqual(code, 0)
        refresh.assert_not_called()

    def test_swu_analyze_refreshes_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "analysis.json"
            with mock.patch.object(
                fetch_cards,
                "refresh_catalogue",
                return_value={"fetched": [], "missing": []},
            ) as refresh:
                code = swu_analyze.main([str(DECK), "--json", str(out)])

        self.assertEqual(code, 0)
        refresh.assert_called_once()


if __name__ == "__main__":
    unittest.main()

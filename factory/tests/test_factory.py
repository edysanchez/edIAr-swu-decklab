from __future__ import annotations

import contextlib
import io
import os
import sys
import unittest
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FACTORY_DIR))

import factory  # noqa: E402

EXAMPLE_BACKLOG = FACTORY_DIR / "backlog.example.json"


class BacklogTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_backlog = os.environ.get("FACTORY_BACKLOG")
        os.environ["FACTORY_BACKLOG"] = str(EXAMPLE_BACKLOG)
        self.data = factory.load_backlog()

    def tearDown(self) -> None:
        if self._old_backlog is None:
            os.environ.pop("FACTORY_BACKLOG", None)
        else:
            os.environ["FACTORY_BACKLOG"] = self._old_backlog

    def test_ids_are_unique(self) -> None:
        ids = [item["id"] for item in self.data["items"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_render_list_contains_example(self) -> None:
        text = factory.render_list(self.data)
        self.assertIn("EXAMPLE-1", text)
        self.assertIn("WIP:", text)

    def test_item_has_acceptance(self) -> None:
        item = factory.find_item(self.data, "EXAMPLE-1")
        text = factory.render_item(item)
        self.assertIn("Acceptance", text)

    def test_packet_without_checks(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = factory.main(["packet", "EXAMPLE-1", "--no-check"])
        self.assertEqual(code, 0)
        text = buf.getvalue()
        self.assertIn("Review packet — EXAMPLE-1", text)
        self.assertIn("Human gates", text)


if __name__ == "__main__":
    unittest.main()

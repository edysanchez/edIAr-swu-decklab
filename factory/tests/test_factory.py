from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FACTORY_DIR))

import factory  # noqa: E402

EXAMPLE_BACKLOG = FACTORY_DIR / "backlog.example.json"


def make_item(item_id: str, **overrides: object) -> dict:
    item = {
        "id": item_id,
        "title": f"Title for {item_id}",
        "status": "ready",
        "priority": "next",
        "risk": "T1",
        "data_touch": False,
        "milestone": None,
        "scope": "Example scope.",
        "acceptance": ["The example passes."],
        "oracle": [],
        "source": "test",
        "notes": "",
    }
    item.update(overrides)
    return item


def make_backlog(*items: dict) -> dict:
    return {"wip_limit": 1, "items": list(items)}


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
        self.assertIn("example-path-config", text)
        self.assertIn("WIP:", text)

    def test_find_item_resolves_legacy_id(self) -> None:
        item = factory.find_item(self.data, "EXAMPLE-1")
        self.assertEqual(item["id"], "example-path-config")

    def test_item_has_acceptance(self) -> None:
        item = factory.find_item(self.data, "example-path-config")
        text = factory.render_item(item)
        self.assertIn("Acceptance", text)

    def test_item_has_no_f1_boolean(self) -> None:
        item = factory.find_item(self.data, "example-path-config")
        text = factory.render_item(item)
        self.assertNotIn("F1: False", text)
        self.assertIn("Milestone:", text)
        self.assertIn("Process:", text)

    def test_packet_without_checks(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = factory.main(["packet", "example-path-config", "--no-check"])
        self.assertEqual(code, 0)
        text = buf.getvalue()
        self.assertIn("Review packet — example-path-config", text)
        self.assertIn("Human gates", text)


class BacklogValidationTests(unittest.TestCase):
    def test_render_list_sorts_by_priority(self) -> None:
        data = make_backlog(
            make_item("later-item", priority="later"),
            make_item("now-item", priority="now"),
            make_item("next-item", priority="next"),
        )
        text = factory.render_list(data)
        self.assertLess(text.index("now-item"), text.index("next-item"))
        self.assertLess(text.index("next-item"), text.index("later-item"))

    def test_render_list_hides_non_ready_by_default(self) -> None:
        data = make_backlog(
            make_item("ready-item"),
            make_item("doing-item", status="doing"),
        )
        self.assertNotIn("doing-item", factory.render_list(data))
        self.assertIn("doing-item", factory.render_list(data, show_all=True))

    def test_render_item_shows_process_and_milestone(self) -> None:
        item = make_item(
            "rules-item",
            risk="T3",
            data_touch=True,
            milestone="functional-core",
        )
        text = factory.render_item(item)
        self.assertIn("domain sign-off (T3) + data", text)
        self.assertIn("functional core (F1)", text)

    def test_validate_rejects_invalid_priority(self) -> None:
        with self.assertRaises(SystemExit):
            factory.validate_backlog(
                make_backlog(make_item("bad-priority", priority="urgent"))
            )

    def test_validate_rejects_invalid_status(self) -> None:
        with self.assertRaises(SystemExit):
            factory.validate_backlog(
                make_backlog(make_item("bad-status", status="Doing"))
            )

    def test_validate_rejects_invalid_id(self) -> None:
        with self.assertRaises(SystemExit):
            factory.validate_backlog(make_backlog(make_item("Bad ID")))

    def test_validate_rejects_duplicate_alias_case_insensitive(self) -> None:
        data = make_backlog(
            make_item("legality-parity", legacy_id="P0-2"),
            make_item("other-item", legacy_id="p0-2"),
        )
        with self.assertRaises(SystemExit):
            factory.validate_backlog(data)

    def test_t3_without_oracle_warns(self) -> None:
        data = make_backlog(make_item("rules-item", risk="T3", oracle=[]))
        warnings = factory.backlog_warnings(data)
        self.assertTrue(warnings)
        self.assertIn("T3 ready without oracle", warnings[0])

    def test_validate_accepts_a_valid_item(self) -> None:
        data = make_backlog(make_item("valid-item"))
        self.assertEqual(factory.validate_backlog(data), data)


class MarkdownTests(unittest.TestCase):
    def test_markdown_targets_ignores_fenced_and_inline_code(self) -> None:
        text = (
            "`[inline](inline.md)`\n"
            "```\n[fenced](fenced.md)\n```\n"
            "[real](real.md)\n"
            "[reference]: reference.md\n"
        )
        targets = factory.markdown_targets(text)
        self.assertIn("real.md", targets)
        self.assertIn("reference.md", targets)
        self.assertNotIn("inline.md", targets)
        self.assertNotIn("fenced.md", targets)


class WorktreeValidationTests(unittest.TestCase):
    def test_require_worktree_accepts_the_checkout(self) -> None:
        factory.require_worktree(FACTORY_DIR.parent)

    def test_require_worktree_rejects_missing_path(self) -> None:
        with self.assertRaises(SystemExit):
            factory.require_worktree(Path("/tmp/opencode/no-such-worktree"))

    def test_require_worktree_rejects_non_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                factory.require_worktree(Path(tmp))

    def test_check_data_guard_fails_on_non_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = factory.check_data_guard(Path(tmp))
            self.assertEqual(result["status"], "FAIL")

    def test_check_links_fails_on_non_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = factory.check_links(Path(tmp))
            self.assertEqual(result["status"], "FAIL")

    def test_check_rejects_non_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                factory.main(["check", "--worktree", tmp])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Unit tests for the domain policy: is a set Premier-legal on a date?

Pure logic, no files. The application-level freshness rules live in
`test_legal_sets.py`; this file covers the rule from `docs/rules.md` only.

The release-date override is **scoped to the lag window** (`as_of < release <=
on`). A product released years before the list was published and absent from it
is not legal: the list excluded it on purpose (rotation). Widening the window to
"any past release" would legalise every rotated set the moment the list is
truncated.
"""

import sys
import unittest
from datetime import date
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

from domain.legal_set_policy import LegalSetPolicy  # noqa: E402

TODAY = date(2026, 11, 12)
LIST_DAY = date(2026, 11, 1)
IC27_DAY = date(2026, 11, 20)


def policy(codes=("JTL",), effective_from=None, as_of=LIST_DAY):
    return LegalSetPolicy(
        codes=frozenset(codes), effective_from=effective_from or {}, as_of=as_of
    )


class LegalSetPolicyTest(unittest.TestCase):
    def test_listed_set_is_legal(self):
        self.assertTrue(policy().is_legal("JTL", TODAY))

    def test_rotated_set_is_not_legal_when_the_list_omits_it(self):
        # Spark of Rebellion was released long before the list was published.
        rule = policy(codes=(), effective_from={"SOR": date(2023, 11, 17)})

        self.assertFalse(rule.is_legal("SOR", TODAY))

    def test_product_released_after_the_list_is_legal(self):
        rule = policy(codes=("JTL",), effective_from={"IC27": IC27_DAY})

        self.assertFalse(rule.is_legal("IC27", TODAY))  # not released yet
        self.assertTrue(rule.is_legal("IC27", date(2026, 11, 21)))

    def test_product_released_on_the_list_day_is_not_legal_by_lag(self):
        rule = policy(codes=(), effective_from={"LOF": LIST_DAY})

        self.assertFalse(rule.is_legal("LOF", TODAY))

    def test_unknown_set_is_not_legal(self):
        self.assertFalse(policy().is_legal("SOR", TODAY))

    def test_available_but_unlisted_only_reports_the_lag_window(self):
        rule = policy(
            codes=("JTL",),
            effective_from={"SOR": date(2023, 11, 17), "LOF": date(2026, 11, 5)},
        )

        self.assertEqual(rule.available_but_unlisted(TODAY), ["LOF"])


if __name__ == "__main__":
    unittest.main()

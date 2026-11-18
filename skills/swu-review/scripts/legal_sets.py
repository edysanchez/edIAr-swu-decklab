#!/usr/bin/env python3
"""Effective Premier legal-set list for a given date.

Application layer: it wires the domain policy (`domain.legal_set_policy`) to the
infrastructure reader (`infrastructure.legal_sets_snapshot`) and adds the
freshness policy. It performs no I/O itself beyond delegating to the reader.

Precedence
----------
1. A readable snapshot wins, even when it disagrees with the built-in registry.
2. With no snapshot, `constants.PREMIER_SETS` is used.

Three freshness rules, because days alone are not enough:

- the snapshot is older than `LEGAL_SETS_SNAPSHOT_MAX_AGE_DAYS`;
- the snapshot announces a change (`next_change`) whose date has already passed,
  which makes it suspect even if it was fetched yesterday;
- a product with a release date in the past is missing from the list, which
  `docs/rules.md` resolves in favour of the release date.

Disagreements and freshness problems are reported as warnings, never applied
silently, so the registry can be updated deliberately.
"""

import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import constants as C
from domain.legal_set_policy import LegalSetPolicy
from infrastructure import legal_sets_snapshot


@dataclass
class LegalSets:
    """Legal set codes plus provenance and the policy behind them."""

    codes: frozenset
    source: str
    as_of: Optional[str] = None
    fetched_at: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    policy: Optional[LegalSetPolicy] = None

    def effective_codes(self, on=None) -> set:
        """Set codes legal today: the list plus anything legal by release date."""
        codes = set(self.codes)
        if self.policy is not None:
            codes |= set(self.policy.available_but_unlisted(on or date.today()))
        return codes

    def is_legal_any(self, set_codes, on=None) -> bool:
        """Return whether any printing of a card is legal as of this snapshot.

        `rules.md`: a card reprinted in a Premier-legal product is legal even if
        the player uses an older printing.
        """
        return any(self.is_legal(code, on) for code in set_codes or ())

    def is_legal(self, set_code: str, on=None) -> bool:
        """Return whether ``set_code`` is Premier-legal as of this snapshot."""
        if self.policy is not None:
            return self.policy.is_legal(set_code, on or date.today())
        return set_code in self.codes


def _parse_date(value):
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _age_days(fetched_at):
    then = _parse_date(fetched_at)
    return None if then is None else (date.today() - then).days


def _registry_fallback(warnings, reason=None):
    if reason:
        warnings.append(reason)
    return LegalSets(
        codes=frozenset(C.PREMIER_SETS),
        source="builtin-registry",
        as_of=None,
        warnings=warnings,
        policy=LegalSetPolicy(
            codes=frozenset(C.PREMIER_SETS), effective_from={}, as_of=None
        ),
    )


def _coverage_warnings(codes, known_sets):
    """Report legal sets the card database has no cards from.

    A legal answer needs data. Without this check a deck from a newly legal set
    reports every card as unresolved, which reads like a deck problem instead of
    a stale cache.
    """
    if known_sets is None:
        return []
    missing = sorted(set(codes) - set(known_sets))
    if not missing:
        return []
    return [
        "The legal-set list includes sets with no complete cards in the "
        "card database: "
        f"{', '.join(missing)}. Decks using them will report unresolved cards. "
        "Run fetch_cards.py."
    ]


def load(snapshot_path=None, known_sets=None):
    """Return the effective :class:`LegalSets` for the Premier format.

    ``known_sets`` is the set of set codes present in the loaded card database;
    when given, legal sets with no cards are reported as warnings.
    """
    result = _load(snapshot_path)
    result.warnings.extend(_coverage_warnings(result.effective_codes(), known_sets))
    return result


def _load(snapshot_path=None):
    """Resolve the snapshot (or the registry) without the coverage check."""
    path = (
        Path(snapshot_path)
        if snapshot_path is not None
        else Path(C.LEGAL_SETS_SNAPSHOT_PATH)
    )
    warnings = []

    try:
        snapshot = legal_sets_snapshot.read(path)
    except legal_sets_snapshot.SnapshotError as exc:
        return _registry_fallback(
            warnings, f"Unusable legal-set snapshot ({exc}); using the built-in registry."
        )

    if snapshot is None:
        return _registry_fallback(warnings)

    codes = frozenset(str(code).strip().upper() for code in snapshot["legal"] if str(code).strip())
    as_of = str(snapshot.get("as_of") or "") or None
    fetched_at = snapshot.get("fetched_at")

    effective_from = {}
    for product in snapshot.get("products") or []:
        code = str(product.get("code") or "").strip().upper()
        # An unreleased product carries "legal_from" instead of "release".
        available = _parse_date(product.get("legal_from") or product.get("release"))
        if code and available is not None:
            effective_from[code] = available

    policy = LegalSetPolicy(
        codes=codes, effective_from=effective_from, as_of=_parse_date(as_of)
    )

    age = _age_days(fetched_at)
    if age is None:
        warnings.append("The legal-set snapshot has no usable fetch date.")
    elif age > C.LEGAL_SETS_SNAPSHOT_MAX_AGE_DAYS:
        warnings.append(
            f"The legal-set snapshot was fetched {age} days ago; re-run "
            "fetch_legal_sets.py to refresh it."
        )

    if policy.as_of is None:
        warnings.append(
            "The legal-set snapshot has no usable date (as_of); the release-date "
            "override is disabled, so only listed sets count as legal."
        )

    next_change = snapshot.get("next_change") or {}
    change_date = _parse_date(next_change.get("legal_from"))
    if change_date is not None and change_date <= date.today():
        product = str(next_change.get("product") or "a product")
        warnings.append(
            f"The legal-set snapshot announces {product} becoming legal on "
            f"{change_date.isoformat()}, a date that has passed; re-run "
            "fetch_legal_sets.py."
        )

    registry = set(C.PREMIER_SETS)
    only_snapshot = codes - registry
    only_registry = registry - codes
    if only_snapshot:
        warnings.append(
            "The legal-set snapshot lists sets missing from the built-in registry: "
            f"{', '.join(sorted(only_snapshot))}. Update constants.PREMIER_SETS."
        )
    if only_registry:
        warnings.append(
            "The built-in registry lists sets the snapshot does not: "
            f"{', '.join(sorted(only_registry))}. Verify the official Premier page."
        )

    unlisted = policy.available_but_unlisted(date.today())
    if unlisted:
        warnings.append(
            f"Already released but missing from the legal-set snapshot: "
            f"{', '.join(unlisted)}. A product is legal from its release date "
            "(docs/rules.md)."
        )

    return LegalSets(
        codes=codes,
        source="hub-snapshot",
        as_of=as_of,
        fetched_at=fetched_at,
        warnings=warnings,
        policy=policy,
    )

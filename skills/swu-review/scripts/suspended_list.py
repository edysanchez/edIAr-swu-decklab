#!/usr/bin/env python3
"""Effective Premier suspended list.

The SWU Competitive Hub page is the operational source: it is one
server-rendered page, kept in sync with FFG's announcements, and it also records
when a card leaves the list. ``fetch_suspended.py`` parses that page into a
local snapshot; this module loads the snapshot and resolves its labels against
the local card database.

Precedence
----------
1. A readable snapshot wins, even if it disagrees with the built-in registry.
2. With no snapshot, ``constants.SUSPENDED_CARDS`` is used.

Disagreements are reported as warnings, never resolved silently, so the
registry — which carries the official announcement URL for every card — can be
updated deliberately.
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

import constants as C


@dataclass
class SuspendedList:
    """Resolved suspended identities plus provenance."""

    identities: frozenset
    source: str
    last_updated: Optional[str] = None
    fetched_at: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


def format_identity(key):
    """Render a ``(name, subtitle)`` key as ``Name|Subtitle``."""
    name, subtitle = key
    return f"{name}|{subtitle}" if subtitle else name


def _normalise(text):
    return " ".join(str(text or "").split()).strip().lower().rstrip(",")


def _number(value):
    text = str(value or "").strip()
    return text.zfill(4) if text.isdigit() else text


def _lookup_tables(card_db):
    by_label = {}
    by_name_number = {}
    for key, card in card_db.items():
        name, subtitle = key
        label = f"{name}, {subtitle}" if subtitle else name
        by_label[_normalise(label)] = key
        by_name_number[(_normalise(name), _number(card.get("number")))] = key
    return by_label, by_name_number


def resolve_entries(entries, card_db):
    """Resolve hub ``{"label", "number"}`` entries to ``(name, subtitle)`` keys.

    Matching is case-insensitive and whitespace-insensitive on the full
    "Name, Subtitle" label; when that fails, the card number from the image URL
    is used as a fallback.
    """
    by_label, by_name_number = _lookup_tables(card_db)
    resolved = set()
    unresolved = []
    for entry in entries:
        label = str(entry.get("label") or "")
        number = _number(entry.get("number"))
        key = by_label.get(_normalise(label))
        if key is None and "," in label:
            name = label.split(",", 1)[0]
            key = by_name_number.get((_normalise(name), number))
        if key is None:
            unresolved.append(dict(entry))
        else:
            resolved.add(key)
    return resolved, unresolved


def _read_snapshot(path, warnings):
    if not path.exists():
        warnings.append(
            f"Suspended-list snapshot not found ({path}); using the built-in "
            "registry. Run fetch_suspended.py to refresh it from SWU Competitive Hub."
        )
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            snapshot = json.load(handle)
    except (OSError, ValueError) as exc:
        warnings.append(
            f"Could not read suspended-list snapshot ({path}: {exc}); using the "
            "built-in registry."
        )
        return None
    if not isinstance(snapshot, dict) or "formats" not in snapshot:
        warnings.append(
            f"Suspended-list snapshot has an unexpected shape ({path}); using the "
            "built-in registry."
        )
        return None
    return snapshot


def _age_days(value):
    try:
        then = datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    return (date.today() - then).days


def load(card_db, snapshot_path=None):
    """Return the effective :class:`SuspendedList` for a card database."""
    path = Path(snapshot_path) if snapshot_path is not None else Path(C.SUSPENDED_SNAPSHOT_PATH)
    warnings = []
    snapshot = _read_snapshot(path, warnings)

    if snapshot is None:
        return SuspendedList(
            identities=frozenset(C.SUSPENDED),
            source="builtin-registry",
            last_updated=C.SUSPENDED_AS_OF,
            warnings=warnings,
        )

    premier = (snapshot.get("formats") or {}).get("Premier") or {}
    if not isinstance(premier, dict) or "entries" not in premier:
        warnings.append(
            "Suspended-list snapshot has no Premier section; using the built-in "
            "registry. Re-run fetch_suspended.py."
        )
        return SuspendedList(
            identities=frozenset(C.SUSPENDED),
            source="builtin-registry",
            last_updated=C.SUSPENDED_AS_OF,
            warnings=warnings,
        )
    entries = premier.get("entries") or []
    resolved, unresolved = resolve_entries(entries, card_db)

    for entry in unresolved:
        warnings.append(
            "Suspended entry from SWU Competitive Hub could not be resolved "
            f"against the card database: {entry.get('label')!r} "
            f"(number {entry.get('number')!r}). Refresh the card database."
        )

    declared = premier.get("count")
    if isinstance(declared, int) and declared != len(entries):
        warnings.append(
            f"SWU Competitive Hub declares {declared} suspended Premier cards but "
            f"{len(entries)} were parsed; the page markup may have changed."
        )

    last_updated = snapshot.get("last_updated")
    age = _age_days(last_updated)
    if last_updated is None:
        warnings.append("Suspended-list snapshot has no last-updated date.")
    elif age is not None and age > C.SUSPENDED_SNAPSHOT_MAX_AGE_DAYS:
        warnings.append(
            f"Suspended-list snapshot is {age} days old (hub last updated "
            f"{last_updated}); re-check SWU Competitive Hub."
        )

    registry = set(C.SUSPENDED)
    only_hub = resolved - registry
    only_registry = registry - resolved
    if only_hub:
        names = ", ".join(sorted(format_identity(k) for k in only_hub))
        warnings.append(
            f"SWU Competitive Hub lists suspended cards missing from the built-in "
            f"registry: {names}. Update constants.SUSPENDED_CARDS with the official "
            "announcement."
        )
    if only_registry:
        names = ", ".join(sorted(format_identity(k) for k in only_registry))
        warnings.append(
            f"The built-in registry lists suspended cards the hub no longer lists: "
            f"{names}. Possible un-suspension: verify the official announcement and "
            "update constants.SUSPENDED_CARDS."
        )

    return SuspendedList(
        identities=frozenset(resolved),
        source="hub-snapshot",
        last_updated=last_updated,
        fetched_at=snapshot.get("fetched_at"),
        warnings=warnings,
    )

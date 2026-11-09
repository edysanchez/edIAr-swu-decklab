#!/usr/bin/env python3
"""Strict resolution of deck card references against the local card database.

Resolution order:

1. explicit ``key`` (name, subtitle);
2. explicit ``set`` + ``number`` (numbers normalised to 3 digits);
3. ``id`` in ``SET_NUMBER`` form (padded or not, any case);
4. exact ``name`` + ``subtitle`` identity;
5. unique ``name`` fallback (used by the Poggle base, whose deck subtitle is empty).

Anything else raises :class:`UnresolvedCard`. The resolver never invents a card.
"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple


class UnresolvedCard(Exception):
    """A deck reference that cannot be matched to the local card database."""

    def __init__(self, ref: Any, reason: str):
        self.ref = ref
        self.reason = reason
        super().__init__(f"{reason}: {ref!r}")


@dataclass(frozen=True)
class Resolved:
    key: Tuple[str, str]
    card: Dict[str, Any]
    resolved_by: str


def normalize_set(value: Any) -> str:
    """Normalise a set code to upper case."""
    return str(value or "").strip().upper()


def normalize_number(value: Any) -> str:
    """Normalise a card number: digits are zero-padded to three places."""
    text = str(value if value is not None else "").strip()
    if text.isdigit():
        return text.zfill(3)
    return text.upper()


def parse_card_id(card_id: Any):
    """Parse ``SET_NUMBER`` into a normalised ``(set, number)`` pair."""
    if not isinstance(card_id, str) or "_" not in card_id:
        return None
    set_code, number = card_id.split("_", 1)
    return normalize_set(set_code), normalize_number(number)


class CardIndex:
    """Lookup index over the normalised card database."""

    def __init__(self, card_db: Dict[Tuple[str, str], Dict[str, Any]]):
        self.by_identity = dict(card_db)
        self.by_set_number: Dict[Tuple[str, str], Tuple[str, str]] = {}
        self.by_name: Dict[str, list] = {}

        for key, card in self.by_identity.items():
            name, _subtitle = key
            self.by_name.setdefault(name, []).append(key)

            set_code = normalize_set(card.get("set"))
            number = normalize_number(card.get("number"))
            if set_code and number:
                self.by_set_number[(set_code, number)] = key

    def resolve(self, ref: Any) -> Resolved:
        if not isinstance(ref, dict):
            raise UnresolvedCard(ref, "reference is not an object")

        if "key" in ref:
            key = tuple(ref["key"])
            if len(key) == 1:
                key = (key[0], "")
            if key in self.by_identity:
                return Resolved(key, self.by_identity[key], "key")
            raise UnresolvedCard(ref, "identity not in card database")

        name = str(ref.get("name", "")).strip() if "name" in ref else None

        set_code = normalize_set(ref.get("set"))
        number = normalize_number(ref.get("number"))
        if set_code and number:
            key = self.by_set_number.get((set_code, number))
            if key:
                self._check_name(ref, key, name)
                return Resolved(key, self.by_identity[key], "set_number")

        parsed = parse_card_id(ref.get("id"))
        if parsed:
            key = self.by_set_number.get(parsed)
            if key:
                self._check_name(ref, key, name)
                return Resolved(key, self.by_identity[key], "id")

        if name is not None:
            key = (name, str(ref.get("subtitle") or "").strip())
            if key in self.by_identity:
                return Resolved(key, self.by_identity[key], "identity")

            matches = self.by_name.get(name, [])
            if len(matches) == 1:
                key = matches[0]
                return Resolved(key, self.by_identity[key], "name")
            if len(matches) > 1:
                raise UnresolvedCard(ref, "ambiguous name; add a subtitle or set/number")

        raise UnresolvedCard(ref, "no matching card in database")

    def _check_name(self, ref: Dict[str, Any], key: Tuple[str, str], name):
        """Reject a set/number that points to a different card than the title."""
        if name is not None and name != key[0]:
            raise UnresolvedCard(
                ref,
                f"set/number points to {key[0]!r}, not {name!r}",
            )

"""Read-only CardRepository over the normalised card database.

``card_db`` is the dict returned by :func:`swu_cards.load_swu_cards`, keyed by
``(name, subtitle)`` tuples. This adapter exposes it through the
``CardRepository`` protocol **without copying it**: the analysis pipeline already
holds the data, so the repository is a view, not a second copy.

A copy is a second source of truth that can drift. That is exactly how
``InMemoryCardRepository()`` — created empty and passed to the aspect-penalty
service — silently reported a penalty of 0 for every deck.
"""

from typing import Dict, List, Optional

from infrastructure.card_repository import CardRepository, Identity


class CardDBRepository(CardRepository):
    """Adapter for the normalised card database loaded from JSON."""

    def __init__(self, card_db: Dict[Identity, dict]):
        self._cards = card_db

    def get_card(self, key: Identity) -> Optional[dict]:
        """Get a card by its ``(name, subtitle)`` identity key."""
        return self._cards.get(key)

    def get_aspects(self, key: Identity) -> List[str]:
        """Get the aspects for a card; an unknown card has no aspects."""
        card = self._cards.get(key) or {}
        return list(card.get("aspects") or [])

    def has_aspect(self, key: Identity, aspect: str) -> bool:
        """Check if a card has a specific aspect."""
        return aspect in self.get_aspects(key)

    def load_cards(self) -> Dict[Identity, dict]:
        """Return a shallow copy of the cards, as the protocol requires."""
        return dict(self._cards)

    def get_all_cards(self) -> List[dict]:
        """Get all cards as a list."""
        return list(self._cards.values())

    def card_exists(self, key: Identity) -> bool:
        """Check if a card exists in the database."""
        return key in self._cards

    def get_keys(self) -> List[Identity]:
        """Get all card identity keys."""
        return list(self._cards.keys())

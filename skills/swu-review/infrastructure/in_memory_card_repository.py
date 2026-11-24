"""In-memory implementation of CardRepository for testing purposes.

This allows unit tests to run without requiring the actual card database file,
making tests faster and more reliable.
"""

from typing import Dict, List, Optional

from infrastructure.card_repository import CardData, CardRepository, Identity


class InMemoryCardRepository(CardRepository):
    """In-memory implementation of CardRepository.

    Stores cards in memory and is ideal for unit testing.
    Can be pre-populated with test data or started empty.
    """

    def __init__(self, initial_cards: Optional[Dict[Identity, CardData]] = None):
        """Initialize with optional pre-loaded cards.

        Args:
            initial_cards: Dictionary mapping ``(name, subtitle)`` identity keys
                           to card dicts.
        """
        self._cards: Dict[Identity, CardData] = initial_cards or {}
        self._load_order: List[Identity] = []

    def get_card(self, key: Identity) -> Optional[CardData]:
        """Get a card by its ``(name, subtitle)`` identity key."""
        return self._cards.get(key)

    def get_aspects(self, key: Identity) -> List[str]:
        """Get the aspects for a card."""
        card = self.get_card(key)
        if not card:
            return []
        aspects = card.get("aspects")
        if not isinstance(aspects, list):
            return []
        return [aspect for aspect in aspects if isinstance(aspect, str)]

    def has_aspect(self, key: Identity, aspect: str) -> bool:
        """Check if a card has a specific aspect."""
        return aspect in self.get_aspects(key)

    def load_cards(self) -> Dict[Identity, CardData]:
        """Load all cards as a dictionary."""
        return self._cards.copy()

    def add_card(self, key: Identity, card: CardData) -> None:
        """Add a card to the repository."""
        self._cards[key] = card
        if key not in self._load_order:
            self._load_order.append(key)

    def get_all_cards(self) -> List[CardData]:
        """Get all cards as a list."""
        return list(self._cards.values())

    def card_exists(self, key: Identity) -> bool:
        """Check if a card exists in the repository."""
        return key in self._cards

    def get_keys(self) -> List[Identity]:
        """Get all card keys."""
        return list(self._cards.keys())

    def clear(self) -> None:
        """Clear all cards from the repository."""
        self._cards = {}
        self._load_order = []

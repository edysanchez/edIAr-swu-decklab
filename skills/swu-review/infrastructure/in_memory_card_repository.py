"""In-memory implementation of CardRepository for testing purposes.

This allows unit tests to run without requiring the actual card database file,
making tests faster and more reliable.
"""

from typing import Dict, List, Optional, Any
from infrastructure.card_repository import CardRepository


class InMemoryCardRepository(CardRepository):
    """In-memory implementation of CardRepository.
    
    Stores cards in memory and is ideal for unit testing.
    Can be pre-populated with test data or started empty.
    """
    
    def __init__(self, initial_cards: Dict[str, dict] = None):
        """Initialize with optional pre-loaded cards.
        
        Args:
            initial_cards: Dictionary mapping card keys to card dicts.
                           Key format: "name|subtitle" or just "name"
        """
        self._cards: Dict[str, dict] = initial_cards or {}
        self._load_order: List[str] = []
    
    def get_card(self, key: str) -> Optional[dict]:
        """Get a card by its identity key."""
        # Try exact match first
        card = self._cards.get(key)
        if card:
            return card
        
        # Try normalized key (handle name|subtitle format)
        # If key contains "|", try without it and vice versa
        if "|" in key:
            plain_key = key.split("|")[0]
            card = self._cards.get(plain_key)
            if card:
                return card
        
        return None
    
    def get_aspects(self, key: str) -> List[str]:
        """Get the aspects for a card."""
        card = self.get_card(key)
        if card and "aspects" in card:
            return card["aspects"]
        return []
    
    def has_aspect(self, key: str, aspect: str) -> bool:
        """Check if a card has a specific aspect."""
        return aspect in self.get_aspects(key)
    
    def load_cards(self) -> Dict[str, dict]:
        """Load all cards as a dictionary."""
        return self._cards.copy()
    
    def add_card(self, key: str, card: dict) -> None:
        """Add a card to the repository."""
        self._cards[key] = card
        if key not in self._load_order:
            self._load_order.append(key)
    
    def get_all_cards(self) -> List[dict]:
        """Get all cards as a list."""
        return list(self._cards.values())
    
    def card_exists(self, key: str) -> bool:
        """Check if a card exists in the repository."""
        return key in self._cards
    
    def get_keys(self) -> List[str]:
        """Get all card keys."""
        return list(self._cards.keys())
    
    def clear(self) -> None:
        """Clear all cards from the repository."""
        self._cards = {}
        self._load_order = []
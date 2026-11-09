"""Protocol/Interface for Card Repository.

Defines the contract that both in-memory and real implementations must follow.
This enables dependency injection and loose coupling between domain logic
and data access implementation.
"""

from typing import Protocol, Dict, List, Optional, Any


class CardRepository(Protocol):
    """Protocol defining the card database interface."""
    
    def get_card(self, key: str) -> Optional[dict]:
        """Get a card by its identity key (name|subtitle)."""
        ...
    
    def get_aspects(self, key: str) -> List[str]:
        """Get the aspects listed for a card."""
        ...
    
    def has_aspect(self, key: str, aspect: str) -> bool:
        """Check if a card has a specific aspect."""
        ...
    
    def load_cards(self) -> Dict[str, dict]:
        """Load all cards from the data source."""
        ...
    
    def get_all_cards(self) -> List[dict]:
        """Get all cards as a list."""
        ...
    
    def card_exists(self, key: str) -> bool:
        """Check if a card exists in the repository."""
        ...
    
    def get_keys(self) -> List[str]:
        """Get all card keys stored."""
        ...
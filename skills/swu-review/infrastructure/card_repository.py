"""Protocol/Interface for Card Repository.

Defines the contract that both in-memory and real implementations must follow.
This enables dependency injection and loose coupling between domain logic
and data access implementation.
"""

from typing import Dict, List, Optional, Protocol, Tuple, TypedDict

# Card identity is the same (name, subtitle) tuple used by the catalogue.
Identity = Tuple[str, str]


class CardData(TypedDict, total=False):
    """Normalised card record from the local catalogue.

    ``total=False`` because the source JSON does not guarantee every field on
    every printing. The infrastructure boundary normalises API values to these
    canonical types before the domain sees them.
    """

    name: str
    subtitle: str
    set: str
    number: str
    type: str
    aspects: List[str]
    traits: List[str]
    arenas: List[str]
    cost: Optional[int]
    power: Optional[int]
    hp: Optional[int]
    keywords: List[str]
    unique: bool
    rarity: str
    frontText: Optional[str]
    epicAction: Optional[str]
    doubleSided: bool
    marketPriceUsd: Optional[str]
    lowPriceUsd: Optional[str]
    foilPriceUsd: Optional[str]
    tcgplayerId: Optional[str]
    cid: Optional[str]
    frontArt: Optional[str]
    artist: Optional[str]
    upgradePower: Optional[int]
    upgradeHp: Optional[int]


class CardRepository(Protocol):
    """Protocol defining the card database interface."""

    def get_card(self, key: Identity) -> Optional[CardData]:
        """Get a card by its ``(name, subtitle)`` identity key."""
        ...

    def get_aspects(self, key: Identity) -> List[str]:
        """Get the aspects listed for a card."""
        ...

    def has_aspect(self, key: Identity, aspect: str) -> bool:
        """Check if a card has a specific aspect."""
        ...

    def load_cards(self) -> Dict[Identity, CardData]:
        """Load all cards from the data source."""
        ...

    def get_all_cards(self) -> List[CardData]:
        """Get all cards as a list."""
        ...

    def card_exists(self, key: Identity) -> bool:
        """Check if a card exists in the repository."""
        ...

    def get_keys(self) -> List[Identity]:
        """Get all card keys stored."""
        ...

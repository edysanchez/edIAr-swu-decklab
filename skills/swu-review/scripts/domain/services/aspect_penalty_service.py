"""Domain service for calculating aspect penalty in SWU decks.

This service depends on the CardRepository protocol, not on a specific
implementation. This allows for easy testing with InMemoryCardRepository
and easy substitution of the data source in production.
"""

from typing import Dict, List, Optional, Set
from infrastructure.card_repository import CardRepository


class AspectPenaltyService:
    """Domain service that calculates aspect penalty for SWU Premier decks.
    
    Responsibility: Calculate the penalty for cards missing aspects
    provided by the leader and base cards.
    
    Dependencies:
        - CardRepository: Protocol for accessing card data
    
    This is a pure domain service - it knows nothing about files, JSON,
    or where the cards come from. It only knows how to calculate penalties
    given card data.
    """
    
    def __init__(self, card_repository: CardRepository):
        """Inject the card repository via constructor.
        
        Args:
            card_repository: An implementation of the CardRepository protocol.
                           Can be InMemoryCardRepository for testing
                           or SWUJSONRepository for production use.
        """
        self.card_repository = card_repository
    
    def calculate_penalty(
        self,
        leader_key: Optional[str],
        base_key: Optional[str],
        main_counts: Dict[str, int]
    ) -> dict:
        """Calculate the aspect penalty for all main-deck cards.
        
        Args:
            leader_key: Identity key of the leader card (e.g., "HMW_012")
                       or None if no leader
            base_key: Identity key of the base card or None
            main_counts: Dictionary mapping card keys to copy counts
            
        Returns:
            Dictionary with keys: total, max, per_card
            - total: Total penalty across all cards
            - max: Maximum penalty on a single card
            - per_card: List of dicts with per-card penalty details
        """
        # Step 1: Collect provided aspects from leader and base
        provided: Set[str] = set()
        
        if leader_key:
            leader_aspects = self.card_repository.get_aspects(leader_key)
            provided.update(leader_aspects)
        
        if base_key:
            base_aspects = self.card_repository.get_aspects(base_key)
            provided.update(base_aspects)
        
        # Step 2: Calculate penalty for each main-deck card
        total = 0
        maximum = 0
        per_card = []
        
        for key, copies in sorted(main_counts.items()):
            # Get the card's aspects from the repository
            card_aspects = self.card_repository.get_aspects(key)
            
            # Find missing aspects
            missing = [a for a in card_aspects if a not in provided]
            
            # Calculate penalty: 2 * number of missing aspects
            penalty = 2 * len(missing)
            
            # Accumulate total
            total += penalty * copies
            
            # Track maximum per-card penalty
            if penalty > maximum:
                maximum = penalty
            
            # Add to per_card if there are missing aspects
            if penalty:
                # Format identity key display
                identity = key  # In a full implementation, would format name|subtitle
                
                per_card.append({
                    "identity": identity,
                    "copies": copies,
                    "penalty": penalty,
                    "missing_aspects": missing,
                })
        
        return {
            "total": total,
            "max": maximum,
            "per_card": per_card
        }
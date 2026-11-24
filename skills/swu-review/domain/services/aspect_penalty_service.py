"""Domain service for calculating aspect penalty in SWU decks.

This service depends on the CardRepository protocol, not on a specific
implementation. This allows for easy testing with InMemoryCardRepository
and easy substitution of the data source in production.
"""

from collections import Counter
from typing import Any, Dict, List, Optional

from infrastructure.card_repository import CardRepository, Identity


def _identity_label(key: Identity) -> str:
    """Render a ``(name, subtitle)`` key as ``Name|Subtitle``.

    The analysis contract requires ``per_card[].identity`` to be a string, so
    the raw tuple must never leak into the output.
    """
    name, subtitle = key
    return f"{name}|{subtitle}" if subtitle else name


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
        leader_key: Optional[Identity],
        base_key: Optional[Identity],
        main_counts: Dict[Identity, int],
    ) -> Dict[str, Any]:
        """Calculate the aspect penalty for all main-deck cards.

        Args:
            leader_key: ``(name, subtitle)`` identity of the leader card,
                       or None if no leader
            base_key: ``(name, subtitle)`` identity of the base card, or None
            main_counts: Dictionary mapping card identities to copy counts

        Returns:
            Dictionary with keys: total, max, per_card
            - total: Total penalty across all cards
            - max: Maximum penalty on a single card
            - per_card: List of dicts with per-card penalty details
        """
        # Step 1: Collect provided aspects from leader and base as a multiset.
        provided: Counter[str] = Counter()
        if leader_key:
            provided.update(self.card_repository.get_aspects(leader_key))
        if base_key:
            provided.update(self.card_repository.get_aspects(base_key))

        # Step 2: Calculate penalty for each main-deck card.
        n = sum(main_counts.values())
        total = 0
        maximum = 0
        affected_slots = 0
        per_card: List[Dict[str, Any]] = []

        for key, copies in sorted(main_counts.items()):
            card_aspects = self.card_repository.get_aspects(key)
            required: Counter[str] = Counter(card_aspects)

            # One entry per icon that has no matching icon from leader/base.
            missing: List[str] = []
            for aspect, count in required.items():
                missing.extend([aspect] * max(0, count - provided[aspect]))

            penalty = 2 * len(missing)
            total += penalty * copies
            if penalty > maximum:
                maximum = penalty
            if penalty:
                affected_slots += copies

            if penalty:
                per_card.append({
                    "identity": _identity_label(key),
                    "copies": copies,
                    "penalty": penalty,
                    "missing_aspects": missing,
                })

        return {
            "total": total,
            "max": maximum,
            "affected_slots": affected_slots,
            "total_per_slot": round(total / n, 2) if n else 0.0,
            "per_card": per_card,
        }

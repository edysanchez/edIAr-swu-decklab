"""Factory for creating InMemoryCardRepository instances with test data."""

from infrastructure.in_memory_repository import InMemoryCardRepository


class InMemoryCardRepositoryFactory:
    """Factory class to create pre-configured InMemoryCardRepository instances."""
    
    @staticmethod
    def create_standard() -> InMemoryCardRepository:
        """Create a standard repository with typical SWU cards."""
        return InMemoryCardRepository({
            "HMW_012": {
                "name": "Poggle the Lesser",
                "aspects": ["White"],
                "cost": 3,
                "power": 3,
                "hp": 4,
                "rarity": "Common",
                "type": "Unit",
            },
            "ASH_032": {
                "name": "Aurra the Seer",
                "aspects": ["Blue", "White"],
                "cost": 4,
                "power": 2,
                "hp": 3,
                "rarity": "Uncommon",
                "type": "Unit",
            },
            "HMW_022": {
                "name": "Sanctum",
                "aspects": ["Power"],
                "cost": 0,
                "power": 0,
                "hp": 20,
                "rarity": "Base",
                "type": "Base",
            },
            "LOF_015": {
                "name": "Finn",
                "aspects": ["Ground"],
                "cost": 2,
                "power": 2,
                "hp": 3,
                "rarity": "Common",
                "type": "Unit",
            },
            "SEC_045": {
                "name": "Bastila",
                "aspects": ["Blue"],
                "cost": 5,
                "power": 4,
                "hp": 5,
                "rarity": "Rare",
                "type": "Unit",
            },
        })
    
    @staticmethod
    def create_with_aspects(*aspect_sets: tuple) -> InMemoryCardRepository:
        """Create a repository with specified aspect configurations.
        
        Args:
            *aspect_sets: Tuples of (card_key, aspects_list)
                         e.g., ("HMW_012", ["White", "Blue"])
        """
        cards = {}
        for aspect_set in aspect_sets:
            if len(aspect_set) >= 2:
                key, aspects = aspect_set[0], aspect_set[1]
                cards[key] = {"name": key, "aspects": aspects}
        
        return InMemoryCardRepository(cards)
    
    @staticmethod
    def create_empty() -> InMemoryCardRepository:
        """Create an empty repository."""
        return InMemoryCardRepository()
    
    @staticmethod
    def create_with_leader_base(
        leader_key: str, leader_aspects: list,
        base_key: str, base_aspects: list
    ) -> InMemoryCardRepository:
        """Create a repository with leader and base cards.
        
        Useful for testing deck validation.
        """
        cards = {
            leader_key: {"name": leader_key, "aspects": leader_aspects},
            base_key: {"name": base_key, "aspects": base_aspects},
        }
        return InMemoryCardRepository(cards)
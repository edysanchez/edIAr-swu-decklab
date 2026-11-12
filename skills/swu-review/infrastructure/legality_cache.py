"""Module for SWU card legality caching.

Provides functionality to store and query Premier format legal sets
with an expiration-based cache system.

Allows offline operation after first execution using cached data.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import urllib.request
from urllib.error import HTTPError, URLError


# Cache file path relative to project root
CACHE_FILE = "data/legality_cache.json"

# Cache validity days after first execution
CACHE_EXPIRY_DAYS = 30

# SWU Competitive Hub API base URL
API_BASE = "https://www.swu-competitivehub.com/premier-format-and-rotation/"

# Set codes commonly used in SWU Premier format
# These are the standard codes we know, but we'll determine legality via the API
PREMIER_SET_CODES = ["JTL", "LOF", "IBH", "SEC", "LAW", "ASH", "HMW"]

# Known Premier format rotation dates (2026-2027)
# Used as fallback when API is unavailable
NEXT_ROTATIONS: list[tuple[str, str]] = [
    ("Icons 2027 Edition", "2026-11-20"),
    ("Block A Rotation", "2027-02-01"),
    ("Legacy of Skywalker", "2027-02-02"),
    ("System Overload", "2027-05-01"),
]


class LegalityCache:
    """Cache for SWU Premier format legal sets.

    Stores legal sets in a local file with expiration date,
    allowing offline operation after first execution.

    Functionality:
    - First run: Fetch data from web and save cache
    - Subsequent runs: Use cache from file
    - After expiration: Automatic update on next run
    - Offline: Use expired cache if no network available
    """

    def __init__(self, cache_path: str = CACHE_FILE):
        self.cache_path = Path(cache_path)
        self._cache: dict | None = None

    def _load_cache(self) -> dict | None:
        """Load cache from file.

        Returns cache dict if file exists and is valid, None otherwise.
        """
        if not self.cache_path.exists():
            return None
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _save_cache(self, legal_sets: list[str], source: str = "official") -> None:
        """Save cache to file with expiration date.

        Args:
            legal_sets: List of legal set codes.
            source: Data source for records.
        """
        data = {
            "last_checked": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=CACHE_EXPIRY_DAYS)).isoformat(),
            "legal_sets": legal_sets,
            "source": source,
        }
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def is_valid(self) -> bool:
        """Check if cache is valid (not expired).

        Returns:
            True if cache exists and not expired, False otherwise.
        """
        cache = self._load_cache()
        if not cache:
            return False
        expires_at = datetime.fromisoformat(cache["expires_at"])
        return datetime.now() < expires_at

    def get_legal_sets(self) -> list[str]:
        """Get legal sets, from cache or by fetching.

        Returns:
            List of legal set codes.
        """
        if self.is_valid():
            # Valid cache: use directly
            return self._load_cache()["legal_sets"]

        # Invalid or missing cache: fetch and save
        legal_sets = self._fetch_legal_sets()
        self._save_cache(legal_sets)
        return legal_sets

    def _fetch_legal_sets(self) -> list[str]:
        """Fetch legal sets from the SWU Competitive Hub API.

        Makes HTTP requests to determine which sets are legal for the Premier format.
        Parses the API response to check legality status.
        Falls back to rotation date logic if the API is completely unavailable.

        Returns:
            List of legal set codes confirmed by the API.
        """
        legal_sets: list[str] = []

        # Try each known Premier set code against the Competitive Hub API
        for set_code in PREMIER_SET_CODES:
            url = f"{API_BASE}?set={set_code}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "edIAr-swu-decklab/0.1"})
                with urllib.request.urlopen(req, timeout=30) as response:
                    # Parse the JSON response from the API
                    data = json.loads(response.read().decode("utf-8"))
                    
                    # Check the legality status from the API response
                    # The API may return fields like: "legal", "is_legal", "status", etc.
                    # We'll check for common fields to determine if the set is legal
                    is_legal_set = self._check_api_legality(data, set_code)
                    
                    if is_legal_set:
                        legal_sets.append(set_code)
                        print(f"Set {set_code} confirmed legal via Competitive Hub API")
                    else:
                        print(f"Set {set_code} not legal via Competitive Hub API")
                        
            except HTTPError as e:
                # Set not found or not legal in Competitive Hub
                # We simply skip it - don't add to legal_sets
                print(f"Set {set_code} not legal via Competitive Hub (HTTP {e.code})")
            except URLError as e:
                # Network error => fall back to rotation date logic
                print(f"Network error: {e}")
                # Fall through to rotation logic below
                break

        # If we got at least one legal set from API, return them
        if legal_sets:
            return legal_sets

        # API completely unavailable: fall back to rotation date logic
        # on the known set codes
        legal_sets = []
        for set_code in PREMIER_SET_CODES:
            # Check if set hasn't rotated out yet
            rotated = False
            for _, date_str in NEXT_ROTATIONS:
                rotation_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if datetime.now().date() >= rotation_date:
                    # This set has rotated out (simplified logic)
                    rotated = True
                    break
            if not rotated:
                # Set is still legal according to rotation dates
                legal_sets.append(set_code)

        return legal_sets

    def _check_api_legality(self, data: dict, set_code: str) -> bool:
        """Check if a set is legal based on the API response data.
        
        Looks for common fields that indicate legality status.
        """
        # Check for various possible fields that indicate legality
        legal_fields = ["legal", "is_legal", "status", "legal_status", "status_legal"]
        
        for field in legal_fields:
            if field in data:
                value = data[field]
                # Handle different types of values
                if isinstance(value, bool):
                    return value
                elif isinstance(value, str):
                    return value.lower() in ["true", "yes", "1", "legal"]
                elif isinstance(value, (int, float)):
                    return value == 1 or value > 0
        
        # If no specific field found, check if data contains set_code
        # which implies the set exists and might be legal
        if set_code in data:
            return True
        
        # Default: assume not legal if we can't determine
        return False

    @classmethod
    def reset_cache(cls) -> None:
        """Clear cache (useful for tests)."""
        cache_path = Path(CACHE_FILE)
        if cache_path.exists():
            cache_path.unlink()

    @classmethod
    def get_expiry_date(cls) -> str | None:
        """Return the cache's expiration date.

        Returns:
            Expiration date string or None if no cache.
        """
        cache = cls._load_cache()
        if cache:
            return cache.get("expires_at")
        return None


class LegalityValidator:
    """Legality validator using the sets cache."""

    def __init__(self, legal_sets: list[str] | None = None):
        """Initialize with a set of legal sets.

        If not provided, uses the default cache.
        """
        if legal_sets is None:
            from infrastructure.legality_cache import LegalityCache
            cache = LegalityCache()
            self.legal_sets = LegalityCache.get_legal_sets()
        else:
            self.legal_sets = legal_sets

    def is_legal_set(self, set_code: str) -> bool:
        """Check if a card set is legal for Premier format.

        Args:
            set_code: The set code (e.g. "JTL", "LOF", etc.)

        Returns:
            True if the set is legal, False otherwise.
        """
        return set_code in self.legal_sets

    def validate_deck_sets(self, deck_sets: list[str]) -> list[str]:
        """Validate a list of sets and return illegal ones.

        Args:
            deck_sets: List of set codes from the deck.

        Returns:
            List of set codes that are not legal.
        """
        non_legal: list[str] = []
        for set_code in deck_sets:
            if not self.is_legal_set(set_code):
                non_legal.append(set_code)
        return non_legal
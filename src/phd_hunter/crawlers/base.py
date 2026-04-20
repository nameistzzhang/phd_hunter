"""Base classes for crawlers."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json


@dataclass
class CacheEntry:
    """Cached data entry with TTL."""
    data: Any
    timestamp: datetime
    ttl: int = 86400  # 1 day default

    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age < self.ttl


class BaseCrawler(ABC):
    """Base class for all crawlers."""

    def __init__(self, cache_enabled: bool = True, cache_ttl: int = 86400):
        """Initialize crawler.

        Args:
            cache_enabled: Enable result caching
            cache_ttl: Cache TTL in seconds
        """
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self._cache: dict[str, CacheEntry] = {}

    @abstractmethod
    def fetch(self, *args, **kwargs) -> Any:
        """Fetch data from source. Must be implemented by subclasses."""
        pass

    def _get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_cached(self, key: str) -> Optional[Any]:
        """Get data from cache if valid."""
        if not self.cache_enabled:
            return None
        entry = self._cache.get(key)
        if entry and entry.is_valid():
            return entry.data
        return None

    def set_cache(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Store data in cache."""
        self._cache[key] = CacheEntry(
            data=data,
            timestamp=datetime.now(),
            ttl=ttl or self.cache_ttl
        )

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    def save_cache_to_disk(self, path: str) -> None:
        """Save cache to disk."""
        import pickle
        with open(path, 'wb') as f:
            pickle.dump(self._cache, f)

    def load_cache_from_disk(self, path: str) -> None:
        """Load cache from disk."""
        import pickle
        with open(path, 'rb') as f:
            self._cache = pickle.load(f)

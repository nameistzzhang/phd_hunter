"""Tests for crawlers."""

import pytest
from phd_hunter.crawlers.base import BaseCrawler, CacheEntry
from datetime import datetime, timedelta


class DummyCrawler(BaseCrawler):
    """Test crawler implementation."""

    def fetch(self, value: str):
        return {"result": value}


def test_base_crawler_cache():
    """Test base crawler caching."""
    crawler = DummyCrawler(cache_enabled=True, cache_ttl=10)

    # First fetch - not cached
    result1 = crawler.fetch("test")
    assert result1 == {"result": "test"}

    # Second fetch - should be cached
    result2 = crawler.fetch("test")
    assert result2 == result1

    # Different parameter - not cached
    result3 = crawler.fetch("different")
    assert result3 != result1


def test_cache_expiry():
    """Test cache entry expiry."""
    entry = CacheEntry(data="test", timestamp=datetime.now(), ttl=1)
    assert entry.is_valid()

    # Manually set old timestamp
    entry.timestamp = datetime.now() - timedelta(seconds=2)
    assert not entry.is_valid()

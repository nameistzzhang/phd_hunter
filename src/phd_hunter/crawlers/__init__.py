"""Crawlers package."""

from .base import BaseCrawler, CacheEntry
from .csrankings import CSRankingsCrawler
# Import other crawlers as they are implemented:
# from .scholar import ScholarCrawler
# from .professor import ProfessorCrawler
# from .arxiv import ArXivCrawler

__all__ = [
    "BaseCrawler",
    "CacheEntry",
    "CSRankingsCrawler",
]

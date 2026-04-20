"""arXiv crawler - fetches papers by author from arXiv."""

import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import arxiv

from .base import BaseCrawler
from ..models import Professor, Paper
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ArxivCrawler(BaseCrawler):
    """Crawler for arXiv paper search by author."""

    def __init__(
        self,
        delay: float = 1.0,
        cache_enabled: bool = True,
        cache_ttl: int = 86400,
        **kwargs
    ):
        """Initialize arXiv crawler.

        Args:
            delay: Delay between requests (seconds) to respect rate limits
            cache_enabled: Enable result caching
            cache_ttl: Cache TTL in seconds
        """
        super().__init__(cache_enabled=cache_enabled, cache_ttl=cache_ttl)
        self.delay = delay

    def fetch(
        self,
        professor: Professor,
        max_papers: int = 10,
    ) -> List[Paper]:
        """Fetch papers by author from arXiv.

        Args:
            professor: Professor object with name to search
            max_papers: Maximum number of papers to return

        Returns:
            List of Paper objects
        """
        cache_key = f"arxiv_{professor.name}_{max_papers}"
        cached = self.get_cached(cache_key)
        if cached:
            logger.info(f"Using cached arXiv results for {professor.name}")
            return cached

        logger.info(f"Searching arXiv for author: {professor.name}")

        # Build arXiv query: author search
        query = f'au:"{professor.name}"'

        try:
            search = arxiv.Search(
                query=query,
                max_results=max_papers,
                sort_by=arxiv.SortCriterion.SubmittedDate,  # Newest first
            )

            papers = []
            for result in search.results():
                # Extract arXiv ID from entry_id (format: http://arxiv.org/abs/XXXX.XXXXX)
                arxiv_id = result.entry_id.split('/')[-1]

                # Build authors list
                authors = [a.name for a in result.authors]

                # Get publication year and month
                pub_date = result.published
                year = pub_date.year
                month = pub_date.month

                # Create Paper object
                paper = Paper(
                    arxiv_id=arxiv_id,
                    title=result.title,
                    authors=authors,
                    abstract=result.summary,
                    year=year,
                    venue=None,  # arXiv doesn't have venue info
                    citations=0,  # arXiv doesn't provide citation counts
                    url=result.entry_id,
                    pdf_url=result.pdf_url,
                )
                papers.append(paper)

                logger.debug(f"  Found paper: {paper.title[:80]}")

            logger.info(f"Found {len(papers)} papers for {professor.name}")

            # Be respectful with rate limits
            time.sleep(self.delay)

            self.set_cache(cache_key, papers)
            return papers

        except Exception as e:
            logger.error(f"Error fetching arXiv papers for {professor.name}: {e}")
            return []

    def close(self) -> None:
        """Close crawler - no cleanup needed for arXiv."""
        pass

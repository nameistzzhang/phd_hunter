"""arXiv crawler - fetches papers by author from arXiv."""

import os
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import arxiv
from arxiv import HTTPError

from .base import BaseCrawler
from ..models import Professor, Paper
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ArxivCrawler(BaseCrawler):
    """Crawler for arXiv paper search by author."""

    def __init__(
        self,
        delay: float = 10.0,
        max_retries: int = 3,
        cache_enabled: bool = True,
        cache_ttl: int = 86400,
        **kwargs
    ):
        """Initialize arXiv crawler.

        Args:
            delay: Delay between requests (seconds) to respect rate limits
            max_retries: Maximum number of retry attempts on failure
            cache_enabled: Enable result caching
            cache_ttl: Cache TTL in seconds
        """
        super().__init__(cache_enabled=cache_enabled, cache_ttl=cache_ttl)
        self.delay = delay
        self.max_retries = max_retries

    def fetch(
        self,
        professor: Professor,
        max_papers: int = 10,
        download: bool = False,
        pdf_dir: Optional[str] = None,
    ) -> List[Paper]:
        """Fetch papers by author from arXiv.

        Args:
            professor: Professor object with name to search
            max_papers: Maximum number of papers to return
            download: If True, download PDFs to pdf_dir
            pdf_dir: Directory to save PDFs (default: "papers")

        Returns:
            List of Paper objects (with local_pdf_path if downloaded)
        """
        cache_key = f"arxiv_{professor.name}_{max_papers}_{download}"
        cached = self.get_cached(cache_key)
        if cached:
            logger.info(f"Using cached arXiv results for {professor.name}")
            return cached

        logger.info(f"Searching arXiv for author: {professor.name}")

        # Build arXiv query: author search
        query = f'au:"{professor.name}"'

        # Prepare PDF directory if downloading
        if download:
            pdf_base = Path(pdf_dir or "papers")
            # Sanitize professor name for directory name
            safe_name = "".join(c for c in professor.name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            prof_pdf_dir = pdf_base / safe_name
            prof_pdf_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"PDFs will be saved to: {prof_pdf_dir}")

        for attempt in range(self.max_retries):
            try:
                search = arxiv.Search(
                    query=query,
                    max_results=max_papers,
                    sort_by=arxiv.SortCriterion.SubmittedDate,  # Newest first
                )

                papers = []
                for result in search.results():
                    # Extract arXiv ID from entry_id
                    arxiv_id = result.entry_id.split('/')[-1]

                    # Build authors list
                    authors = [a.name for a in result.authors]

                    # Get publication year and month
                    pub_date = result.published
                    year = pub_date.year
                    month = pub_date.month

                    # Download PDF if requested
                    local_pdf_path = None
                    if download:
                        try:
                            # Create filename: {arxiv_id}.pdf or {arxiv_id}_{sanitized_title}.pdf
                            safe_title = "".join(c for c in result.title[:80] if c.isalnum() or c in (' ', '-', '_', '.')).strip()
                            safe_title = safe_title.replace(' ', '_')
                            filename = f"{arxiv_id}_{safe_title}.pdf"
                            # Truncate if too long
                            if len(filename) > 200:
                                filename = f"{arxiv_id}.pdf"

                            pdf_path = prof_pdf_dir / filename

                            # Download if not already exists
                            if not pdf_path.exists():
                                logger.debug(f"  Downloading PDF: {filename}")
                                result.download_pdf(dirpath=str(prof_pdf_dir), filename=filename)
                            else:
                                logger.debug(f"  PDF already exists: {filename}")

                            local_pdf_path = str(pdf_path.relative_to(pdf_base))
                        except Exception as e:
                            logger.warning(f"  Failed to download PDF for {arxiv_id}: {e}")
                            local_pdf_path = None

                    # Create Paper object
                    paper = Paper(
                        arxiv_id=arxiv_id,
                        title=result.title,
                        authors=authors,
                        abstract=result.summary,
                        year=year,
                        month=month,
                        venue=None,  # arXiv doesn't have venue info
                        citations=0,  # arXiv doesn't provide citation counts
                        url=result.entry_id,
                        pdf_url=result.pdf_url,
                        pdf_path=local_pdf_path,
                    )
                    papers.append(paper)

                    logger.debug(f"  Found paper: {paper.title[:80]}")

                logger.info(f"Found {len(papers)} papers for {professor.name}")

                # Be respectful with rate limits
                time.sleep(self.delay)

                self.set_cache(cache_key, papers)
                return papers

            except HTTPError as e:
                # arxiv.HTTPError has 'status' attribute (not 'status_code')
                status = getattr(e, 'status', None)
                if status == 429:
                    wait_time = (attempt + 1) * 10  # 10, 20, 30 seconds
                    logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"HTTP error {status}: {e}")
                    break
            except Exception as e:
                logger.error(f"Error fetching arXiv papers for {professor.name} (attempt {attempt+1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                break

        logger.error(f"Failed to fetch papers for {professor.name} after {self.max_retries} attempts")
        return []

    def close(self) -> None:
        """Close crawler - no cleanup needed for arXiv."""
        pass

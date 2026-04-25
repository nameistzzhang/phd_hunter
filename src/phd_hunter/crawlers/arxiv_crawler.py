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


def _normalize_name(name: str) -> str:
    """Normalize a person name for fuzzy comparison.

    Removes punctuation, lowercases, and collapses whitespace.
    """
    import re
    name = name.lower().strip()
    name = re.sub(r"[.,;:\-\(\)\[\]]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _name_to_parts(name: str) -> List[str]:
    """Split a name into individual word parts."""
    return [p for p in _normalize_name(name).split(" ") if p]


def _is_author_match(professor_name: str, authors: List[str]) -> bool:
    """Check whether professor_name appears in the authors list.

    Handles common variations:
      - Full name:  "David P. Woodruff"
      - Initials:   "D. P. Woodruff", "D. Woodruff"
      - Last-only:  "Woodruff"
      - Case-insensitive
    """
    prof_parts = _name_to_parts(professor_name)
    if not prof_parts:
        return False

    prof_last = prof_parts[-1]
    prof_initials = [p[0] for p in prof_parts[:-1] if p]

    for author in authors:
        auth_parts = _name_to_parts(author)
        if not auth_parts:
            continue

        auth_last = auth_parts[-1]

        # Last name must match
        if prof_last != auth_last:
            continue

        # Exact match
        if prof_parts == auth_parts:
            return True

        # Initial match: "D. P. Woodruff" or "D. Woodruff"
        auth_initials = [p[0] for p in auth_parts[:-1] if p]
        if auth_initials == prof_initials:
            return True

        # Relaxed: same last name + at least one shared first initial
        if prof_initials and auth_initials:
            if any(pi == ai for pi, ai in zip(prof_initials, auth_initials)):
                return True

    return False


def _clean_title_for_search(title: str) -> str:
    """Clean a paper title for use in arXiv search query.

    Removes quotes, newlines, and trims to a reasonable length.
    """
    title = title.strip()
    title = title.replace('"', "")
    title = title.replace("\n", " ")
    title = title.replace("\r", " ")
    # arXiv query length is limited; truncate very long titles
    if len(title) > 200:
        title = title[:200]
    return title


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

    def _result_to_paper(
        self,
        result: arxiv.Result,
        professor: Professor,
        download: bool = False,
        pdf_dir: Optional[Path] = None,
    ) -> Optional[Paper]:
        """Convert an arXiv result to a Paper object.

        Returns None if the professor is not in the author list.
        """
        # Extract arXiv ID from entry_id
        arxiv_id = result.entry_id.split('/')[-1]

        # Build authors list
        authors = [a.name for a in result.authors]

        # Verify professor is actually an author
        if not _is_author_match(professor.name, authors):
            return None

        # Get publication year and month
        pub_date = result.published
        year = pub_date.year
        month = pub_date.month

        # Download PDF if requested
        local_pdf_path = None
        if download and pdf_dir is not None:
            try:
                safe_title = "".join(
                    c for c in result.title[:80]
                    if c.isalnum() or c in (' ', '-', '_', '.')
                ).strip()
                safe_title = safe_title.replace(' ', '_')
                filename = f"{arxiv_id}_{safe_title}.pdf"
                if len(filename) > 200:
                    filename = f"{arxiv_id}.pdf"

                pdf_path = pdf_dir / filename

                if not pdf_path.exists():
                    logger.debug(f"  Downloading PDF: {filename}")
                    result.download_pdf(dirpath=str(pdf_dir), filename=filename)
                else:
                    logger.debug(f"  PDF already exists: {filename}")

                local_pdf_path = str(pdf_path.relative_to(pdf_dir))
            except Exception as e:
                logger.warning(f"  Failed to download PDF for {arxiv_id}: {e}")
                local_pdf_path = None

        return Paper(
            arxiv_id=arxiv_id,
            title=result.title,
            authors=authors,
            abstract=result.summary,
            year=year,
            month=month,
            venue=None,
            citations=0,
            url=result.entry_id,
            pdf_url=result.pdf_url,
            pdf_path=local_pdf_path,
        )

    def fetch_by_titles(
        self,
        professor: Professor,
        titles: List[str],
        max_papers: int = 10,
        download: bool = False,
        pdf_dir: Optional[str] = None,
    ) -> List[Paper]:
        """Fetch papers from arXiv by exact title search.

        For each title, searches arXiv and returns papers where the
        professor appears as an author.  This avoids the name-collision
        problem of author-based search.

        Args:
            professor: Professor object (used for author verification)
            titles: List of paper titles to search for
            max_papers: Maximum total papers to return
            download: If True, download PDFs
            pdf_dir: Directory to save PDFs

        Returns:
            List of Paper objects where the professor is a confirmed author.
        """
        if not titles:
            logger.info(f"No titles provided for {professor.name}, skipping title search")
            return []

        cache_key = f"arxiv_titles_{professor.name}_{hash(tuple(titles))}_{max_papers}"
        cached = self.get_cached(cache_key)
        if cached:
            logger.info(f"Using cached arXiv title-search results for {professor.name}")
            return cached

        logger.info(f"Searching arXiv by title for {professor.name} ({len(titles)} titles)")

        # Prepare PDF directory if downloading
        prof_pdf_dir = None
        if download:
            pdf_base = Path(pdf_dir or "papers")
            safe_name = "".join(
                c for c in professor.name if c.isalnum() or c in (' ', '-', '_')
            ).strip().replace(' ', '_')
            prof_pdf_dir = pdf_base / safe_name
            prof_pdf_dir.mkdir(parents=True, exist_ok=True)

        papers: List[Paper] = []
        seen_ids: set = set()

        for title in titles:
            if len(papers) >= max_papers:
                break

            cleaned = _clean_title_for_search(title)
            if not cleaned or len(cleaned) < 5:
                logger.debug(f"  Skipping too-short title: {title}")
                continue

            query = f'ti:"{cleaned}"'
            logger.debug(f"  Searching arXiv: {query}")

            for attempt in range(self.max_retries):
                try:
                    search = arxiv.Search(
                        query=query,
                        max_results=3,
                        sort_by=arxiv.SortCriterion.Relevance,
                    )

                    for result in search.results():
                        arxiv_id = result.entry_id.split('/')[-1]
                        if arxiv_id in seen_ids:
                            continue

                        paper = self._result_to_paper(
                            result, professor,
                            download=download, pdf_dir=prof_pdf_dir,
                        )
                        if paper:
                            papers.append(paper)
                            seen_ids.add(arxiv_id)
                            logger.debug(f"  Matched: {paper.title[:80]}")

                        if len(papers) >= max_papers:
                            break

                    # Be respectful with rate limits
                    time.sleep(self.delay)
                    break  # Success, move to next title

                except HTTPError as e:
                    status = getattr(e, 'status', None)
                    if status == 429:
                        wait_time = (attempt + 1) * 10
                        logger.warning(f"Rate limited (429). Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    logger.error(f"HTTP error {status} for title '{title}': {e}")
                    break
                except Exception as e:
                    logger.error(f"Error searching title '{title}' (attempt {attempt+1}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    break

        logger.info(f"Found {len(papers)} confirmed papers for {professor.name} via title search")
        self.set_cache(cache_key, papers)
        return papers

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
                    paper = self._result_to_paper(
                        result, professor,
                        download=download, pdf_dir=prof_pdf_dir,
                    )
                    if paper:
                        papers.append(paper)
                        logger.debug(f"  Found paper: {paper.title[:80]}")

                logger.info(f"Found {len(papers)} confirmed papers for {professor.name}")

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

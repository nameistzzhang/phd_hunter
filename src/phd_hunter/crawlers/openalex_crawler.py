"""OpenAlex crawler - fetches papers by professor from OpenAlex API."""

import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import requests

from .base import BaseCrawler
from ..models import Professor, Paper
from ..utils.logger import get_logger

logger = get_logger(__name__)


class OpenAlexCrawler(BaseCrawler):
    """Crawler for fetching professor papers via OpenAlex API.

    OpenAlex provides a free, open bibliographic database with
    reliable author-institution linking and arXiv associations.
    """

    BASE_URL = "https://api.openalex.org"

    def __init__(
        self,
        delay: float = 1.0,
        max_retries: int = 3,
        cache_enabled: bool = True,
        cache_ttl: int = 86400,
        **kwargs
    ):
        """Initialize OpenAlex crawler.

        Args:
            delay: Delay between requests (seconds) to respect rate limits
            max_retries: Maximum number of retry attempts on failure
            cache_enabled: Enable result caching
            cache_ttl: Cache TTL in seconds
        """
        super().__init__(cache_enabled=cache_enabled, cache_ttl=cache_ttl)
        self.delay = delay
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "PhDHunter/1.0 (mailto:phd@example.com)"
        })

    def _get(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request with retries and rate limiting."""
        for attempt in range(self.max_retries):
            try:
                resp = self._session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                time.sleep(self.delay)
                return resp.json()
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else None
                if status == 429:
                    wait = (attempt + 1) * 5
                    logger.warning(f"Rate limited (429). Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"HTTP error {status}: {e}")
                raise
            except Exception as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise

    def get_institution_id(self, institution_name: str) -> Optional[str]:
        """Search for an institution by name and return its OpenAlex ID.

        Args:
            institution_name: University/institution name (e.g. "New York University")

        Returns:
            OpenAlex institution ID (e.g. "https://openalex.org/I154802399")
            or None if not found.
        """
        cache_key = f"oa_inst_{institution_name}"
        cached = self.get_cached(cache_key)
        if cached:
            return cached

        logger.info(f"[OpenAlex] Searching institution: {institution_name}")
        data = self._get(
            f"{self.BASE_URL}/institutions",
            params={"search": institution_name}
        )
        results = data.get("results", [])
        if not results:
            logger.warning(f"[OpenAlex] Institution not found: {institution_name}")
            return None

        top = results[0]
        inst_id = top["id"]
        logger.info(
            f"[OpenAlex] Found institution: {top['display_name']} ({inst_id})"
        )
        self.set_cache(cache_key, inst_id)
        return inst_id

    def get_author_id(self, name: str, institution_id: str) -> Optional[str]:
        """Search for an author by name + institution and return OpenAlex ID.

        Args:
            name: Author name (e.g. "Yann LeCun")
            institution_id: OpenAlex institution ID

        Returns:
            OpenAlex author ID (e.g. "https://openalex.org/A5070270706")
            or None if not found.
        """
        cache_key = f"oa_author_{name}_{institution_id}"
        cached = self.get_cached(cache_key)
        if cached:
            return cached

        logger.info(f"[OpenAlex] Searching author: {name} @ {institution_id}")
        inst_short = institution_id.replace("https://openalex.org/", "")
        data = self._get(
            f"{self.BASE_URL}/authors",
            params={
                "search": name,
                "filter": f"affiliations.institution.id:{inst_short}",
                "per-page": 10,
            }
        )
        authors = data.get("results", [])
        if not authors:
            logger.warning(f"[OpenAlex] Author not found: {name}")
            return None

        # Pick the author with the most works (most likely the professor)
        selected = max(authors, key=lambda a: a.get("works_count", 0))
        author_id = selected["id"]
        aff = selected.get("last_known_institutions", [{}])[0].get(
            "display_name", "unknown"
        )
        logger.info(
            f"[OpenAlex] Selected author: {selected['display_name']} "
            f"({aff}, {selected.get('works_count', 0)} works, {author_id})"
        )
        self.set_cache(cache_key, author_id)
        return author_id

    def _work_to_paper(self, work: Dict[str, Any]) -> Optional[Paper]:
        """Convert an OpenAlex work dict to a Paper object."""
        title = work.get("display_name", "")
        if not title:
            return None

        # Publication date -> year/month
        pub_date = work.get("publication_date", "")
        year = None
        month = None
        if pub_date:
            try:
                dt = datetime.strptime(pub_date, "%Y-%m-%d")
                year = dt.year
                month = dt.month
            except ValueError:
                try:
                    year = int(pub_date.split("-")[0])
                except (ValueError, IndexError):
                    pass

        import re

        # Extract arXiv info from locations
        arxiv_id = None
        arxiv_url = None
        pdf_url = None
        venue = None

        _ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})")

        for loc in work.get("locations", []) or []:
            source = loc.get("source", {}) or {}
            src_name = source.get("display_name", "")
            if src_name and "arxiv" in src_name.lower():
                landing = loc.get("landing_page_url", "")
                if landing:
                    # Extract arXiv ID from URL like /abs/2403.18814 or /pdf/2403.18814
                    m = _ARXIV_ID_RE.search(landing)
                    if m:
                        arxiv_id = m.group(1)
                        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
                    else:
                        arxiv_url = landing
                # Prefer explicit pdf_url, fallback to landing_page_url if it's a PDF
                pdf_url = loc.get("pdf_url")
                if not pdf_url and landing and "/pdf/" in landing:
                    pdf_url = landing
                break

        # If no arXiv, try open_access URL
        if not arxiv_url:
            oa = work.get("open_access", {}) or {}
            oa_url = oa.get("oa_url")
            if oa_url:
                m = _ARXIV_ID_RE.search(oa_url)
                if m:
                    arxiv_id = m.group(1)
                    arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
                else:
                    arxiv_url = oa_url

        # Venue / host
        host = work.get("host_venue", {}) or work.get("primary_location", {}) or {}
        if host:
            venue = host.get("display_name")
            if not venue:
                src = host.get("source") or {}
                venue = src.get("display_name")

        # Authors
        authors = []
        for auth in work.get("authorships", []) or []:
            a = auth.get("author", {})
            if a and a.get("display_name"):
                authors.append(a["display_name"])

        # DOI as fallback URL
        doi = work.get("doi", "")
        url = arxiv_url or doi or work.get("id", "")

        # Fallback: construct PDF URL from arXiv ID if not provided
        if arxiv_id and not pdf_url:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        # Citations
        citations = work.get("cited_by_count", 0) or 0

        return Paper(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            abstract=work.get("abstract", "") or "",
            year=year or 0,
            month=month,
            venue=venue,
            citations=citations,
            url=url,
            pdf_url=pdf_url,
        )

    def fetch(
        self,
        professor: Professor,
        max_papers: int = 10,
        **kwargs
    ) -> List[Paper]:
        """Fetch papers for a professor from OpenAlex.

        Args:
            professor: Professor object with name and university
            max_papers: Maximum number of papers to return

        Returns:
            List of Paper objects.
        """
        cache_key = f"oa_papers_{professor.name}_{professor.university}_{max_papers}"
        cached = self.get_cached(cache_key)
        if cached:
            logger.info(f"[OpenAlex] Using cached papers for {professor.name}")
            return cached

        logger.info(f"[OpenAlex] Fetching papers for: {professor.name}")

        # Step 1: Find institution
        inst_id = self.get_institution_id(professor.university)
        if not inst_id:
            logger.warning(
                f"[OpenAlex] Could not find institution for: {professor.university}"
            )
            return []

        # Step 2: Find author
        author_id = self.get_author_id(professor.name, inst_id)
        if not author_id:
            logger.warning(
                f"[OpenAlex] Could not find author: {professor.name}"
            )
            return []

        # Step 3: Fetch works
        author_short = author_id.replace("https://openalex.org/", "")
        papers: List[Paper] = []
        page = 1
        per_page = min(max_papers, 200)

        while len(papers) < max_papers:
            logger.debug(
                f"[OpenAlex] Fetching works page {page} "
                f"({len(papers)}/{max_papers} so far)"
            )
            data = self._get(
                f"{self.BASE_URL}/works",
                params={
                    "filter": f"author.id:{author_short}",
                    "sort": "publication_date:desc",
                    "per-page": per_page,
                    "page": page,
                }
            )
            works = data.get("results", [])
            if not works:
                break

            for work in works:
                paper = self._work_to_paper(work)
                if paper:
                    papers.append(paper)
                if len(papers) >= max_papers:
                    break

            # Check for more pages
            meta = data.get("meta", {})
            total = meta.get("count", 0)
            if page * per_page >= total:
                break
            page += 1

        logger.info(
            f"[OpenAlex] Found {len(papers)} papers for {professor.name}"
        )
        self.set_cache(cache_key, papers)
        return papers

    def close(self) -> None:
        """Close crawler and cleanup resources."""
        self._session.close()

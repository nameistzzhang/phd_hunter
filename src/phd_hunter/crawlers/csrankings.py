"""CSRankings crawler - fetches professor data from csrankings.org."""

from typing import List, Optional, Dict, Any
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from .base import BaseCrawler
from ..models import Professor
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CSRankingsCrawler(BaseCrawler):
    """Crawler for CSRankings.org."""

    BASE_URL = "https://csrankings.org"

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30,
        **kwargs
    ):
        """Initialize CSRankings crawler.

        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout
        """
        super().__init__(**kwargs)
        self.headless = headless
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None

    def _init_driver(self) -> None:
        """Initialize Selenium WebDriver."""
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        self.driver = webdriver.Chrome(
            ChromeDriverManager().install(),
            options=options
        )
        self.driver.implicitly_wait(self.timeout)

    def fetch(
        self,
        universities: Optional[List[str]] = None,
        areas: Optional[List[str]] = None,
        start_year: int = 2018,
    ) -> List[Professor]:
        """Fetch professors from CSRankings.

        Args:
            universities: List of university names (as shown on CSRankings)
            areas: List of CS areas (e.g., "ai", "ml", "nlp")
            start_year: Include papers from this year onwards

        Returns:
            List of Professor objects
        """
        cache_key = self._get_cache_key(universities, areas, start_year)
        cached = self.get_cached(cache_key)
        if cached:
            logger.info("Using cached CSRankings data")
            return cached

        if self.driver is None:
            self._init_driver()

        professors: List[Professor] = []

        try:
            # Build URL with filters
            url = f"{self.BASE_URL}/index.html"
            self.driver.get(url)
            time.sleep(2)  # Wait for page to load

            # Apply filters
            if universities:
                self._select_universities(universities)
            if areas:
                self._select_areas(areas)

            # Wait for results to load
            time.sleep(3)

            # Parse professor table
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')

            # Find professor rows
            rows = soup.select("table#ranking tbody tr")
            for row in rows:
                try:
                    prof = self._parse_professor_row(row)
                    if prof:
                        professors.append(prof)
                except Exception as e:
                    logger.warning(f"Failed to parse row: {e}")

            logger.info(f"Found {len(professors)} professors")

            # Cache results
            self.set_cache(cache_key, professors)

        except Exception as e:
            logger.error(f"CSRankings fetch failed: {e}")
            raise

        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

        return professors

    def _select_universities(self, universities: List[str]) -> None:
        """Select universities from dropdown."""
        # CSRankings uses institution IDs
        institution_map = {
            "MIT": "MIT",
            "Stanford": "Stanford",
            "Berkeley": "UC Berkeley",
            "CMU": "CMU",
        }
        # Implementation would click checkboxes
        pass

    def _select_areas(self, areas: List[str]) -> None:
        """Select research areas."""
        # Implementation would click area checkboxes
        pass

    def _parse_professor_row(self, row) -> Optional[Professor]:
        """Parse professor table row."""
        try:
            cells = row.select("td")
            if len(cells) < 3:
                return None

            name_cell = cells[0]
            name = name_cell.get_text(strip=True)

            # Extract links
            scholar_link = None
            homepage_link = None
            for link in name_cell.select("a"):
                href = link.get('href', '')
                if 'scholar.google.com' in href:
                    scholar_link = href
                elif href.startswith('http'):
                    homepage_link = href

            uni_cell = cells[1]
            university = uni_cell.get_text(strip=True)

            area_cell = cells[2]
            areas = [a.strip() for a in area_cell.get_text(',').split(',')]

            prof_id = f"csr_{hash(name + university)}"

            return Professor(
                id=prof_id,
                name=name,
                university=university,
                homepage=homepage_link,
                scholar_url=scholar_link,
                research_interests=areas,
                source_urls=[self.BASE_URL],
            )
        except Exception as e:
            logger.warning(f"Row parse error: {e}")
            return None

"""CSRankings crawler - fetches professor data from csrankings.org."""

from typing import List, Optional, Dict, Any, Tuple, Union
from pydantic import BaseModel, Field
import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from .base import BaseCrawler
from ..models import Professor, University
from ..utils.logger import get_logger, setup_logger
from ..database import Database

logger = get_logger(__name__)


class CrawlerInterrupted(Exception):
    """Raised when the crawler receives a stop signal."""
    pass


class University(BaseModel):
    """University/institution data from CSRankings."""
    id: str
    name: str
    rank: int
    score: float
    paper_count: int
    cs_rankings_url: str
    department_url: Optional[str] = None
    location: Optional[str] = None
    professor_count: int = 0
    faculty_url: Optional[str] = None


class CSRankingsCrawler(BaseCrawler):
    """Crawler for CSRankings.org."""

    BASE_URL = "https://csrankings.org"

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30,
        verbose: bool = False,
        db_path: Optional[str] = None,
        stop_event=None,
        progress_callback=None,
        **kwargs
    ):
        """Initialize CSRankings crawler.

        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout
            verbose: Enable verbose logging (DEBUG level)
            db_path: Path to SQLite database file (default: phd_hunter.db in current dir)
            stop_event: Optional threading.Event to check for stop requests
            progress_callback: Optional callback(current, total, phase) for progress updates
        """
        super().__init__(**kwargs)

        # Setup verbose logging if requested
        if verbose:
            setup_logger(name="phd_hunter", level="DEBUG")
            logger.debug("Verbose logging enabled")

        self.headless = headless
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None
        self.db = Database(db_path or "phd_hunter.db")
        self._stop_event = stop_event
        self._progress_callback = progress_callback
        self._closed = False
        self._close_lock = threading.Lock()

    def _report_progress(self, current: int, total: int, phase: str) -> None:
        """Report progress via callback if registered."""
        if self._progress_callback is not None:
            try:
                self._progress_callback(current, total, phase)
            except Exception:
                pass

    def _check_stop(self):
        """Check if a stop has been requested and raise CrawlerInterrupted if so."""
        if self._stop_event is not None and self._stop_event.is_set():
            logger.info("Stop signal received in crawler, aborting...")
            raise CrawlerInterrupted("Crawler stopped by user request")

    def _interruptible_sleep(self, seconds: float, check_interval: float = 0.1) -> None:
        """Sleep for the given duration, but check for stop signal periodically.

        If a stop is requested during the sleep, raises CrawlerInterrupted immediately.

        Args:
            seconds: Total time to sleep
            check_interval: How often to check the stop signal (seconds)
        """
        elapsed = 0.0
        while elapsed < seconds:
            self._check_stop()
            sleep_duration = min(check_interval, seconds - elapsed)
            time.sleep(sleep_duration)
            elapsed += sleep_duration

    def _init_driver(self) -> None:
        """Initialize Selenium WebDriver."""
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(self.timeout)

    def close(self) -> None:
        """Close WebDriver and release resources (thread-safe, idempotent)."""
        with self._close_lock:
            if self._closed:
                logger.debug("Crawler already closed, skipping")
                return
            self._closed = True

        def _do_close():
            # Close WebDriver
            if self.driver:
                try:
                    self.driver.quit()
                    logger.debug("WebDriver closed")
                except Exception as e:
                    logger.debug(f"WebDriver already closed or error during quit: {e}")
                finally:
                    self.driver = None

            # Close database connection
            if self.db:
                try:
                    self.db.close()
                    logger.debug("Database connection closed")
                except Exception as e:
                    logger.debug(f"Error closing database: {e}")

        # Run quit in daemon thread with timeout to avoid Windows WebDriver hang
        t = threading.Thread(target=_do_close, daemon=True)
        t.start()
        t.join(timeout=3.0)
        if t.is_alive():
            logger.warning("WebDriver quit timed out after 3s, force-closing")

    def _wait_for_ranking_table(self, timeout: int = 10) -> bool:
        """Wait for ranking table to be present.

        Args:
            timeout: Max wait time in seconds

        Returns:
            True if table loaded, False if timeout
        """
        # Use short-poll loop to allow stop signal checking during wait
        elapsed = 0.0
        poll_interval = 0.3
        while elapsed < timeout:
            self._check_stop()
            try:
                table_exists = self.driver.execute_script(
                    "return document.getElementById('ranking') !== null;"
                )
                if table_exists:
                    logger.debug("Ranking table is present")
                    return True
            except Exception:
                pass
            self._interruptible_sleep(poll_interval)
            elapsed += poll_interval

        logger.warning(f"Ranking table not loaded after {timeout}s")
        return False

    def fetch(
        self,
        areas: Optional[List[str]] = None,
        start_year: int = 2024,
        end_year: int = 2026,
        region: Optional[str] = None,
        include_professors: bool = False,
        max_universities: Optional[int] = None,
        max_professors: Optional[int] = None,
    ) -> Union[List[University], Tuple[List[University], List[Professor]]]:
        """Fetch university rankings and optionally professor details from CSRankings.

        Note: CSRankings provides institution rankings, not individual professors.
        This method returns university data by default. Set include_professors=True
        to also fetch all faculty members for each university after applying filters.

        Args:
            universities: Filter by specific university names
            areas: Research areas to filter (e.g., "ai", "ml")
            start_year: Include papers from this year onwards
            end_year: Include papers up to this year
            region: Filter by region/country (e.g., "us", "cn", "world")
            include_professors: If True, also fetch all professor details by expanding each university
            max_universities: Limit number of universities to process (applied after filtering)
            max_professors: Limit number of professors to return (applied after extraction)

        Returns:
            If include_professors=False: List of University objects
            If include_professors=True: Tuple of (List[University], List[Professor])
        """
        logger.debug(f"Fetch parameters: areas={areas}, start_year={start_year}, region={region}")

        cache_key = self._get_cache_key(areas, start_year, end_year, region)
        logger.debug(f"Cache key: {cache_key}")

        cached = self.get_cached(cache_key)
        if cached:
            logger.info("Using cached CSRankings data")
            logger.debug(f"Cached universities count: {len(cached)}")
            return cached

        if self.driver is None:
            self._init_driver()

        universities_list: List[University] = []

        try:
            # Navigate to CSRankings
            url = f"{self.BASE_URL}/index.html"
            logger.debug(f"Navigating to: {url}")
            self.driver.get(url)

            # Wait for ranking table to be present
            if not self._wait_for_ranking_table(60):
                logger.warning("Ranking table did not load within timeout")

            # Close any popup overlays (sponsor, survey, PhD inquiry)
            self._close_overlays()

            logger.debug("Page loaded, current URL: " + self.driver.current_url)

            # Apply year filter via JavaScript
            if start_year:
                logger.debug(f"Setting year range: {start_year}-{end_year}")
                self._select_years(start_year, end_year)

            # Apply area filters
            if areas:
                logger.debug(f"Applying area filters: {areas}")
                self._select_areas(areas)

            # Apply region filter
            if region:
                logger.debug(f"Applying region filter: {region}")
                self._select_region(region)

            # Wait for all filters to be applied and table to settle
            logger.debug("Waiting for table to update after all filters...")
            if not self._wait_for_table_update(15):
                logger.warning("Table update wait timed out, proceeding with parsing...")

            # Parse university table using BeautifulSoup (fast)
            html = self.driver.page_source
            logger.debug(f"Page HTML length: {len(html)} characters")

            # Save HTML for debugging
            if logger._core.handlers:
                import pathlib
                debug_dir = pathlib.Path("debug_output")
                debug_dir.mkdir(exist_ok=True)
                html_file = debug_dir / f"csrankings_page_{cache_key[:8]}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.debug(f"Saved page HTML to: {html_file}")

            soup = BeautifulSoup(html, 'lxml')

            # Find university rows (4-cell rows)
            all_rows = soup.select("table#ranking tbody tr")
            logger.debug(f"Found {len(all_rows)} total rows")

            total_rows = len(all_rows)
            for idx, row in enumerate(all_rows):
                try:
                    # Check for stop signal every row to ensure quick response
                    self._check_stop()

                    # Report progress every few rows
                    if idx % 3 == 0 or idx == total_rows - 1:
                        self._report_progress(idx + 1, total_rows, 'crawl_universities')

                    # Only process 4-cell rows (university data)
                    cells = row.select("td")
                    if len(cells) != 4:
                        logger.debug(f"Row {idx+1}: Skipped (expected 4 cells, got {len(cells)})")
                        continue

                    logger.debug(f"Parsing university row {idx+1}/{total_rows}")
                    university = self._parse_university_row(row)
                    if university:
                        universities_list.append(university)
                        logger.debug(f"  -> Added: {university.name} (rank={university.rank}, score={university.score})")
                except Exception as e:
                    logger.warning(f"Failed to parse row {idx+1}: {e}")

            logger.info(f"Found {len(universities_list)} universities total")

            # Apply max_universities limit (before professor extraction)
            if max_universities is not None and max_universities > 0:
                universities_list = universities_list[:max_universities]
                logger.info(f"Limited to {len(universities_list)} universities (max_universities={max_universities})")

            # Show summary of top universities
            if universities_list:
                top_universities = sorted(universities_list, key=lambda u: u.rank)[:10]
                logger.debug(f"Top 10 universities: {[u.name for u in top_universities]}")

            # Cache university results
            self.set_cache(cache_key, universities_list)

            # Fetch professor details if requested (uses same driver session)
            professors_list: List[Professor] = []
            if include_professors and universities_list:
                logger.info("Fetching professor details for universities...")
                professors_list = self._fetch_professors_from_current_page(
                    universities_list,
                    max_universities=max_universities,
                    max_professors_per_university=max_professors
                )
                logger.info(f"Found {len(professors_list)} professors total")

        except Exception as e:
            logger.error(f"CSRankings fetch failed: {e}", exc_info=True)
            raise

        finally:
            if self.driver:
                logger.debug("Quitting WebDriver")
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.debug(f"WebDriver already closed or error during quit: {e}")
                finally:
                    self.driver = None

        # Save results to database
        if include_professors:
            self._save_to_db(universities_list, professors_list)
        else:
            self._save_to_db(universities_list, [])

        # Return based on requested data
        if include_professors:
            return universities_list, professors_list
        else:
            return universities_list

    def _close_overlays(self) -> None:
        """Close any popup overlays (sponsor, survey, PhD inquiry, Tour)."""
        try:
            # Wait briefly for overlays to appear (interruptible)
            self._interruptible_sleep(1.0)

            # Method 1: Close Shepherd Tour popup (specific button)
            try:
                shepherd_close = self.driver.find_elements(
                    By.XPATH,
                    "//button[@aria-label='Close Tour' and contains(@class, 'shepherd-cancel-icon')]"
                )
                if shepherd_close:
                    logger.debug(f"Found Tour close button, attempting to click")
                    try:
                        shepherd_close[0].click()
                        self._interruptible_sleep(0.5)
                        logger.debug("Tour popup closed via aria-label button")
                    except Exception as e:
                        logger.debug(f"Direct click failed: {e}, trying JavaScript")
                        self.driver.execute_script("arguments[0].click();", shepherd_close[0])
                        self._interruptible_sleep(0.5)
            except Exception as e:
                logger.debug(f"Shepherd Tour close attempt failed: {e}")

            # Method 2: Close via absolute XPath (as fallback)
            try:
                xpath_btn = self.driver.find_elements(
                    By.XPATH,
                    "/html/body/div[4]/div/header/button"
                )
                if xpath_btn:
                    logger.debug("Found Tour button via absolute XPath, clicking")
                    try:
                        xpath_btn[0].click()
                        self._interruptible_sleep(0.5)
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", xpath_btn[0])
                        self._interruptible_sleep(0.5)
            except Exception as e:
                logger.debug(f"XPath button click failed: {e}")

            # Method 3: Generic overlay removal
            self.driver.execute_script("""
                document.querySelectorAll('.overlay, .modal, .dialog, .popup, .shepherd-button').forEach(el => {
                    el.style.display = 'none';
                    el.remove();
                });
            """)
            self._interruptible_sleep(0.5)

            logger.debug("Overlay close sequence completed")

        except CrawlerInterrupted:
            raise
        except Exception as e:
            logger.warning(f"Overlay close failed: {e}")

    def _wait_for_table_update(self, timeout: int = 10) -> bool:
        """Wait for ranking table to update after filter change.

        Uses URL hash stabilization and table presence detection instead of
        row count change, which is more reliable for CSRankings' hash-based routing.

        Args:
            timeout: Max wait time in seconds

        Returns:
            True if table updated, False if timeout
        """
        try:
            wait = WebDriverWait(self.driver, timeout)

            # Wait for URL hash to stabilize (hash change triggers table update)
            def hash_stabilized(driver):
                # The hash should contain our filter parameters
                hash_val = driver.execute_script("return window.location.hash")
                return hash_val and hash_val.startswith("#/index?")

            wait.until(hash_stabilized)
            logger.debug("URL hash stabilized: " + self.driver.current_url)

            # Additional short wait for table DOM to update (interruptible)
            self._interruptible_sleep(1.5)

            # Verify table has content using JavaScript to avoid stale element issues
            table_exists = self.driver.execute_script("""
                return document.getElementById('ranking') !== null;
            """)
            if not table_exists:
                logger.warning("Table element not found in DOM")
                return False

            row_count = self.driver.execute_script("""
                const table = document.getElementById('ranking');
                if (!table) return 0;
                const rows = table.querySelectorAll('tbody tr');
                let count = 0;
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length === 4) count++;
                });
                return count;
            """)

            if row_count > 0:
                logger.debug(f"Table updated with {row_count} university rows")
                return True
            else:
                logger.warning("Table updated but no university rows found")
                return False

        except TimeoutException:
            logger.warning(f"Timeout waiting for table update after {timeout}s")
            return False

    def _fetch_professors_from_current_page(
        self,
        universities: List[University],
        max_universities: Optional[int] = None,
        max_professors_per_university: Optional[int] = None
    ) -> List[Professor]:
        """Fetch professor details by expanding university rows.

        Args:
            universities: List of University objects (already filtered/sorted)
            max_universities: Max number of universities to process
            max_professors_per_university: Max professors per university

        Returns:
            List of Professor objects
        """
        professors: List[Professor] = []
        driver = self.driver

        # Build name → University object mapping
        uni_name_to_obj = {u.name: u for u in universities}

        # Determine which universities to process (apply max_universities limit)
        uni_names_to_process = [u.name for u in universities]
        if max_universities is not None and max_universities > 0:
            uni_names_to_process = uni_names_to_process[:max_universities]

        logger.debug(f"Will process {len(uni_names_to_process)} universities: {uni_names_to_process}")

        total_unis = len(uni_names_to_process)
        # Process each university: re-fetch fresh DOM each time to avoid stale elements
        for idx, uni_name in enumerate(uni_names_to_process):
            # Check for stop signal before processing each university
            self._check_stop()

            # Report progress
            self._report_progress(idx + 1, total_unis, 'crawl_professors')

            university = uni_name_to_obj.get(uni_name)
            if not university:
                continue

            logger.debug(f"[{idx+1}/{total_unis}] Processing: {uni_name}")

            # Re-fetch all rows to get fresh DOM
            all_rows = driver.find_elements(By.CSS_SELECTOR, "table#ranking tbody tr")

            # Find current university row in fresh DOM
            current_uni_row = None
            for row in all_rows:
                try:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) == 4:
                        cls = row.get_attribute("class") or ""
                        if "faculty-row" not in cls:
                            name_el = row.find_element(By.XPATH, ".//td[2]/span[2]")
                            if name_el.text.strip() == uni_name:
                                current_uni_row = row
                                break
                except Exception:
                    continue

            if not current_uni_row:
                logger.warning(f"  Could not find university row in table, skipping")
                continue

            # Check stop signal before interacting with element
            self._check_stop()

            # Find expand button
            try:
                expand_spans = current_uni_row.find_elements(By.XPATH, ".//span[contains(@onclick, 'toggleFaculty')]")
                if not expand_spans:
                    logger.warning(f"  No expand button for {uni_name}, skipping")
                    continue
                expand_span = expand_spans[0]
            except Exception as e:
                logger.warning(f"  Error finding expand button: {e}")
                continue

            # Expand
            driver.execute_script("arguments[0].click();", expand_span)
            self._interruptible_sleep(1.0)

            # Check stop signal after expansion wait
            self._check_stop()

            # Re-fetch all rows after expansion (fresh DOM)
            all_rows_expanded = driver.find_elements(By.CSS_SELECTOR, "table#ranking tbody tr")

            # Find current university row in expanded DOM by searching fresh DOM
            current_uni_row_expanded = None
            for row in all_rows_expanded:
                try:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) == 4:
                        cls = row.get_attribute("class") or ""
                        if "faculty-row" not in cls:
                            name_el = row.find_element(By.XPATH, ".//td[2]/span[2]")
                            if name_el.text.strip() == uni_name:
                                current_uni_row_expanded = row
                                break
                except Exception:
                    continue

            if not current_uni_row_expanded:
                logger.warning(f"  Could not find university row after expansion, skipping")
                driver.execute_script("arguments[0].click();", expand_span)
                self._interruptible_sleep(0.3)
                continue

            # Check stop signal before parsing faculty rows
            self._check_stop()

            # Stream through faculty rows with immediate parsing and limit check
            start_idx = all_rows_expanded.index(current_uni_row_expanded)
            extracted_count = 0
            row_counter = 0

            # Iterate through rows immediately after current university row
            for subsequent in all_rows_expanded[start_idx + 1:]:
                # Check stop signal every few rows during parsing
                row_counter += 1
                if row_counter % 3 == 0:
                    self._check_stop()

                cls = subsequent.get_attribute("class") or ""
                tds = subsequent.find_elements(By.TAG_NAME, "td")

                if "faculty-row" in cls:
                    # Check per-university limit BEFORE parsing
                    if max_professors_per_university is not None and extracted_count >= max_professors_per_university:
                        logger.debug(f"  Reached per-uni limit ({max_professors_per_university}), stopping")
                        break

                    # Parse immediately
                    try:
                        professor = self._parse_professor_row(subsequent, uni_name)
                        if professor:
                            professors.append(professor)
                            extracted_count += 1
                    except Exception as e:
                        logger.debug(f"    Parse error: {e}")

                elif len(tds) == 4 and "faculty-row" not in cls:
                    # Next university row encountered
                    break

            logger.debug(f"  Extracted {extracted_count} professors from {uni_name}")

            # Check stop signal before collapse
            self._check_stop()

            # Collapse
            driver.execute_script("arguments[0].click();", expand_span)
            self._interruptible_sleep(0.4)

        logger.info(f"Extracted {len(professors)} professors from {len(uni_names_to_process)} universities "
                    f"(max_unis={max_universities}, max_per_uni={max_professors_per_university})")
        return professors

    def _parse_professor_row(self, faculty_row, university_name: str) -> Optional[Professor]:
        """Parse a single faculty row (tr.faculty-row) into a Professor object.

        Args:
            faculty_row: Selenium WebElement for the faculty row
            university_name: Name of the university (for reference)

        Returns:
            Professor object or None if parsing failed
        """
        try:
            tds = faculty_row.find_elements(By.TAG_NAME, "td")
            if len(tds) < 4:
                return None

            # Column 1: name + areas + links
            name_td = tds[1]

            # Professor name and homepage (first <a>)
            name_link = name_td.find_element(By.XPATH, ".//a[1]")
            name = name_link.text.strip()
            homepage = name_link.get_attribute("href")

            # Research areas: inside span.areaname > span elements
            area_spans = name_td.find_elements(By.XPATH, ".//span[contains(@class, 'areaname')]//span")
            research_interests = [s.text.strip() for s in area_spans if s.text.strip()]

            # Google Scholar URL
            try:
                scholar_link = name_td.find_element(By.XPATH, ".//a[contains(@title, 'Google Scholar')]")
                scholar_url = scholar_link.get_attribute("href")
            except NoSuchElementException:
                scholar_url = ""

            # Column 2: paper count
            paper_td = tds[2]
            paper_text = paper_td.text.strip().replace(',', '').replace(' ', '')
            try:
                total_papers = int(paper_text) if paper_text else 0
            except ValueError:
                total_papers = 0

            # Column 3: adjusted score (CSRankings relevance score)
            score_td = tds[3]
            score_text = score_td.text.strip()
            try:
                adjusted_score = float(score_text) if score_text else 0.0
            except ValueError:
                adjusted_score = 0.0

            # Generate unique integer ID from name + university
            prof_id = abs(hash(name + university_name)) % 1000000

            return Professor(
                id=prof_id,
                name=name,
                university=university_name,
                homepage=homepage if homepage else None,
                scholar_url=scholar_url if scholar_url else None,
                research_interests=research_interests,
                total_papers=total_papers,
            )

        except Exception as e:
            logger.debug(f"Failed to parse professor row: {e}")
            return None

    def _save_to_db(
        self,
        universities: List[University],
        professors: List[Professor]
    ) -> None:
        """Save fetched universities and professors to database.

        Professor records include denormalized university info.

        Args:
            universities: List of University objects
            professors: List of Professor objects
        """
        import json

        logger.info(f"Saving {len(universities)} universities and {len(professors)} professors to database...")

        # Debug: check DB connection
        logger.debug(f"DB connection object: {self.db.conn}")
        logger.debug(f"DB path: {self.db.db_path}")

        # Build university name → University object mapping
        uni_map = {u.name: u for u in universities}

        # Save professors (university info denormalized into professor row)
        for prof in professors:
            university = uni_map.get(prof.university)
            if not university:
                logger.warning(f"University not found for professor: {prof.name} ({prof.university})")
                continue

            logger.debug(f"  Inserting professor: {prof.name} (id={prof.id})")
            try:
                prof_id = self.db.upsert_professor(prof, university)
                logger.debug(f"  -> Database ID: {prof_id}")
            except Exception as e:
                logger.error(f"  -> Failed to insert {prof.name}: {e}", exc_info=True)
                raise

        logger.info("Database save complete.")

    def _build_hash(self, areas: Optional[List[str]] = None, start_year: int = None,
                    end_year: int = None, region: Optional[str] = None) -> str:
        """Build URL hash for current filter state.

        CSRankings uses hash-based routing: #/index?[areas]&[start_year]-[end_year]&[region]

        Args:
            areas: List of area codes
            start_year: Start year
            end_year: End year
            region: Region code (e.g., "us", "cn", "world")

        Returns:
            Hash string like "?ai&2024-2026&us" or "?all&2018-2026&world"
        """
        # Build area part
        if not areas:
            area_part = "all"
        else:
            area_to_codes = {
                "ai": ["ai", "ml"],
                "artificial intelligence": ["ai", "ml"],
                "ml": ["ml"],
                "machine learning": ["ml"],
                "deep learning": ["ai", "ml"],
                "dl": ["ai", "ml"],
                "nlp": ["nlp"],
                "natural language processing": ["nlp"],
                "vision": ["vision"],
                "computer vision": ["vision"],
                "cv": ["vision"],
                "ir": ["ir"],
                "information retrieval": ["ir"],
                "the web": ["ir"],
                "web": ["ir"],
                "systems": ["systems"],
                "computer architecture": ["arch"],
                "architecture": ["arch"],
                "arch": ["arch"],
                "computer networks": ["net"],
                "networks": ["net"],
                "net": ["net"],
                "operating systems": ["os"],
                "os": ["os"],
                "design automation": ["da"],
                "da": ["da"],
                "embedded systems": ["es"],
                "embedded & real-time systems": ["es"],
                "es": ["es"],
                "high-performance computing": ["hpca"],
                "hpca": ["hpca"],
                "mobile computing": ["mob"],
                "mob": ["mob"],
                "measurement": ["metrics"],
                "measurement & perf. analysis": ["metrics"],
                "metrics": ["metrics"],
                "programming languages": ["pl"],
                "pl": ["pl"],
                "software engineering": ["se"],
                "se": ["se"],
                "security": ["sec"],
                "computer security": ["sec"],
                "sec": ["sec"],
                "cryptography": ["crypto"],
                "crypto": ["crypto"],
                "theory": ["theory"],
                "algorithms": ["theory"],
                "algorithms & complexity": ["theory"],
                "logic": ["theory"],
                "logic & verification": ["theory"],
                "databases": ["db"],
                "database": ["db"],
                "db": ["db"],
                "hci": ["hci"],
                "human-computer interaction": ["hci"],
                "interdisciplinary": ["interdisciplinary"],
                "bioinformatics": ["bio"],
                "comp. bio & bioinformatics": ["bio"],
                "bio": ["bio"],
                "graphics": ["graphics"],
                "computer graphics": ["graphics"],
                "computer science education": ["ed"],
                "cs education": ["ed"],
                "education": ["ed"],
                "economics & computation": ["econ"],
                "economics": ["econ"],
                "econ": ["econ"],
                "robotics": ["robotics"],
                "visualization": ["visualization"],
            }
            codes = set()
            for area in areas:
                area_lower = area.lower()
                if area_lower in area_to_codes:
                    codes.update(area_to_codes[area_lower])
                else:
                    codes.add(area_lower)
            area_part = "&".join(sorted(codes)) if codes else "all"

        # Build year part
        if start_year and end_year:
            year_part = f"{start_year}-{end_year}"
        else:
            year_part = "2018-2026"

        # Build hash: always include areas and years; region only if explicitly specified
        if region:
            return f"?{area_part}&{year_part}&{region}"
        else:
            return f"?{area_part}&{year_part}"

    def _apply_filters_via_hash(self, areas: Optional[List[str]] = None,
                                 start_year: int = 2024, end_year: int = 2026,
                                 region: Optional[str] = None) -> None:
        """Apply filters by directly setting window.location.hash.

        This is the most reliable way to trigger CSRankings table update.
        """
        hash_value = self._build_hash(areas, start_year, end_year, region)
        full_hash = f"/index{hash_value}"

        logger.debug(f"Setting hash to: {full_hash}")

        # Get initial count for comparison using JavaScript (avoids stale element)
        initial_count = self.driver.execute_script("""
            const rows = document.querySelectorAll('table#ranking tbody tr');
            let count = 0;
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length === 4) count++;
            });
            return count;
        """)
        logger.debug(f"Initial university count before filter: {initial_count}")

        # Set hash
        self.driver.execute_script(f"window.location.hash = '{full_hash}';")

        # Wait for table update
        self._wait_for_table_update(30)

    def _select_years(self, start_year: int, end_year: int) -> None:
        """Set year range using the noUiSlider API.

        Args:
            start_year: Start year (e.g., 2024)
            end_year: End year (e.g., 2026)
        """
        logger.debug(f"Setting year range via noUiSlider: {start_year}-{end_year}")

        try:
            # Check if year slider exists using JavaScript
            slider_exists = self.driver.execute_script(
                "return document.getElementById('year-slider') !== null;"
            )
            if not slider_exists:
                logger.warning("Year slider not found on page, skipping year selection")
                return

            # Get initial table count for comparison using JavaScript
            initial_count = self.driver.execute_script("""
                const rows = document.querySelectorAll('table#ranking tbody tr');
                let count = 0;
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length === 4) count++;
                });
                return count;
            """)
            logger.debug(f"Initial university count: {initial_count}")

            # Use noUiSlider's set method to update both handles via JavaScript
            result = self.driver.execute_script(f"""
                const slider = document.getElementById('year-slider');
                if (slider && slider.noUiSlider) {{
                    slider.noUiSlider.set([{start_year}, {end_year}]);
                    return true;
                }} else {{
                    console.warn('year-slider noUiSlider instance not found');
                    return false;
                }}
            """)
            logger.debug(f"Slider set result: {result}")

            # Small wait for UI to update (interruptible)
            self._interruptible_sleep(0.5)

            # Verify the year displays updated using JavaScript with null checks
            from_display = self.driver.execute_script("""
                const el = document.getElementById('year-display-from');
                return el ? el.textContent.trim() : '';
            """)
            to_display = self.driver.execute_script("""
                const el = document.getElementById('year-display-to');
                return el ? el.textContent.trim() : '';
            """)
            logger.debug(f"Year displays after slider set: from='{from_display}', to='{to_display}'")

            # Wait for table to update
            self._wait_for_table_update(30)

        except Exception as e:
            logger.error(f"Year selection failed: {e}")
            raise

    def _get_current_areas_from_hash(self) -> List[str]:
        """Extract currently selected areas from URL hash."""
        try:
            hash_str = self.driver.execute_script("return window.location.hash;")
            # hash format: #/index?[areas]&[years]&[region]
            if "?all" in hash_str:
                return []
            parts = hash_str.split("?")[1].split("&")

            # Known area codes (must match codes in area_to_codes values)
            known_areas = {
                "ai", "ml", "nlp", "vision", "ir", "systems", "arch", "net",
                "os", "da", "es", "hpca", "mob", "metrics", "pl", "se",
                "sec", "crypto", "theory", "db", "hci", "interdisciplinary",
                "bio", "graphics", "ed", "econ", "robotics", "visualization"
            }

            areas = []
            for part in parts:
                part = part.strip()
                # Must be a known area code and not a year (no digit) and not region
                if part and not part[0].isdigit() and part in known_areas:
                    areas.append(part)
            return areas
        except Exception:
            return []

    def _get_current_years_from_hash(self) -> tuple:
        """Extract year range from URL hash.

        Returns:
            (start_year, end_year) tuple, or (None, None) if not found
        """
        try:
            hash_str = self.driver.execute_script("return window.location.hash;")
            # hash format: #/index?[areas]&[start_year]-[end_year]
            parts = hash_str.split("?")[1].split("&")
            for part in parts:
                if "-" in part and part[0].isdigit():
                    years = part.split("-")
                    if len(years) == 2:
                        return int(years[0]), int(years[1])
        except Exception:
            pass
        return None, None

    def _get_current_region_from_hash(self) -> Optional[str]:
        """Extract region from URL hash.

        Returns:
            Region code (e.g., "us", "cn", "world") or None
        """
        try:
            hash_str = self.driver.execute_script("return window.location.hash;")
            # hash format: #/index?[areas]&[years]&[region]
            # e.g., "#/index?ai&2024-2026&us" or "#/index?all&2024-2026&cn"
            if "?" not in hash_str:
                return None
            parts = hash_str.split("?")[1].split("&")
            # Region is the last part (not starting with digit and not area codes)
            known_areas = {"ai", "ml", "nlp", "vision", "ir", "systems", "arch", "net",
                          "os", "da", "es", "hpca", "mob", "metrics", "pl", "se",
                          "sec", "crypto", "theory", "db", "hci", "interdisciplinary",
                          "bio", "graphics", "ed", "econ", "robotics", "visualization", "all"}
            for part in reversed(parts):  # check from the end
                part = part.strip()
                if part and not part[0].isdigit() and part not in known_areas:
                    return part
        except Exception:
            pass
        return None

    def _select_areas(self, areas: List[str]) -> None:
        """Select research areas via hash navigation.

        Args:
            areas: List of area codes or human-readable names
        """
        logger.debug(f"Selecting areas via hash: {areas}")

        try:
            # Get current years and region from hash (preserve filters)
            current_years = self._get_current_years_from_hash()
            start_year = current_years[0] if current_years[0] else 2024
            end_year = current_years[1] if current_years[1] else 2026
            current_region = self._get_current_region_from_hash() or "world"

            logger.debug(f"Keeping current year range: {start_year}-{end_year}, region: {current_region}")

            # Use hash-based approach
            self._apply_filters_via_hash(
                areas=areas,
                start_year=start_year,
                end_year=end_year,
                region=current_region
            )

        except Exception as e:
            logger.error(f"Area selection failed: {e}")
            raise

    def _select_region(self, region: str) -> None:
        """Select region by setting URL hash (hash-based routing).

        Args:
            region: Region code (e.g., "us", "cn", "world", "northamerica", "europe")
        """
        logger.debug(f"Selecting region via hash: {region}")

        try:
            # Get current filters to preserve
            current_areas = self._get_current_areas_from_hash()
            current_years = self._get_current_years_from_hash()
            start_year = current_years[0] if current_years[0] else 2024
            end_year = current_years[1] if current_years[1] else 2026

            logger.debug(f"Preserving areas: {current_areas}, years: {start_year}-{end_year}")

            # Apply all filters including new region
            self._apply_filters_via_hash(
                areas=current_areas if current_areas else None,
                start_year=start_year,
                end_year=end_year,
                region=region
            )

            logger.debug(f"Region '{region}' selected successfully")

        except Exception as e:
            logger.error(f"Region selection failed: {e}")
            raise

    def _parse_university_row(self, row) -> Optional[University]:
        """Parse university table row (4-cell format).

        Row format:
        Cell 0: Rank number (e.g., "1")
        Cell 1: University name (e.g., "►Tsinghua University") with link to dept
        Cell 2: Score (e.g., "18.4")
        Cell 3: Paper count (e.g., "178")
        """
        try:
            cells = row.select("td")
            if len(cells) != 4:
                logger.debug(f"Unexpected cell count: {len(cells)}")
                return None

            # Cell 0: Rank
            rank_str = cells[0].get_text(strip=True)
            try:
                rank = int(rank_str)
            except ValueError:
                logger.warning(f"Could not parse rank: {rank_str}")
                rank = 0

            # Cell 1: University name + link
            uni_cell = cells[1]
            # Remove leading special character (► or similar)
            uni_name = uni_cell.get_text(strip=True)
            # Clean up the name - remove leading non-ASCII chars
            uni_name_clean = uni_name.lstrip('►►\u25ba\u25b9\u25c0\u25b8').strip()

            # Extract department URL
            dept_link = uni_cell.select_one("a")
            dept_url = dept_link.get('href', '') if dept_link else None
            # Ensure absolute URL
            if dept_url and not dept_url.startswith('http'):
                dept_url = self.BASE_URL + dept_url

            # Cell 2: Score
            score_str = cells[2].get_text(strip=True)
            try:
                score = float(score_str)
            except ValueError:
                score = 0.0

            # Cell 3: Paper count
            papers_str = cells[3].get_text(strip=True)
            try:
                paper_count = int(papers_str.replace(',', '').replace(' ', ''))
            except ValueError:
                paper_count = 0

            # Generate unique ID
            uni_id = f"uni_{hash(uni_name_clean) % 1000000}"

            logger.debug(f"Parsed university: {uni_name_clean} (rank={rank}, score={score}, papers={paper_count})")

            return University(
                id=uni_id,
                name=uni_name_clean,
                rank=rank,
                score=score,
                paper_count=paper_count,
                cs_rankings_url=self.BASE_URL,
                department_url=dept_url,
            )
        except Exception as e:
            logger.warning(f"University row parse error: {e}")
            return None

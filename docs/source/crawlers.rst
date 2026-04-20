Crawlers
========

This module handles all web scraping and data collection from academic sources.

Overview
--------

Crawlers are responsible for:

* Fetching professor lists from CSRankings
* Retrieving publication data from Google Scholar
* Parsing professor homepages for contact and research info
* Downloading papers from arXiv

All crawlers respect rate limits and include retry logic.

CSRankings Crawler
------------------

**File**: ``crawlers/csrankings.py``

The CSRankings crawler extracts faculty data from https://csrankings.org.

Features:

* Select specific institutions and CS sub-areas
* Extract professor names, homepages, and affiliations
* Handle dynamic page content via Selenium

Usage:

.. code-block:: python

   from phd_hunter.crawlers.csrankings import CSRankingsCrawler

   crawler = CSRankingsCrawler(headless=True)
   professors = crawler.get_professors(
       institutions=["MIT", "Stanford"],
       areas=["ai", "ml"]
   )
   # Returns list of Professor objects

Data Extracted:

- Professor name
- University
- Homepage URL
- Google Scholar profile URL (if available)
- Research area tags

Google Scholar Crawler
----------------------

**File**: ``crawlers/scholar.py``

Fetches publication history from Google Scholar profiles.

Features:

* Get publication count and citation metrics
* Retrieve recent papers (title, venue, year, co-authors)
* Track citation trends

Usage:

.. code-block:: python

   from phd_hunter.crawlers.scholar import ScholarCrawler

   crawler = ScholarCrawler()
   profile = crawler.get_profile("https://scholar.google.com/...")
   # Returns ScholarProfile with publications list

Data Extracted:

- Total citations
- h-index
- Recent publications (last 5 years)
- Publication venues
- Co-author network

Professor Homepage Crawler
--------------------------

**File**: ``crawlers/professor.py``

Parses individual professor websites for detailed information.

Features:

* Extract contact information (email, office)
* Parse research interests and current projects
* Detect if accepting students (招生状态)
* Find CV/Resume links
* Extract education background

Usage:

.. code-block:: python

   from phd_hunter.crawlers.professor import ProfessorCrawler

   crawler = ProfessorCrawler()
   info = crawler.get_info("https://professor.university.edu/~name")
   # Returns ProfessorInfo object

Data Extracted:

- Email address
- Office location
- Research interests (bulleted list)
- Current projects
- Lab/group website
- Accepting students status

arXiv Crawler
-------------

**File**: ``crawlers/arxiv.py``

Downloads papers from arXiv for LLM analysis.

Features:

* Search papers by title/author
* Download PDF and source files
* Extract abstracts and full text
* Batch download with progress tracking

Usage:

.. code-block:: python

   from phd_hunter.crawlers.arxiv import ArXivCrawler

   crawler = ArXivCrawler()
   papers = crawler.search(
       query="author:John Doe",
       max_results=10
   )
   crawler.download(papers, output_dir="./papers")

Data Extracted:

- Paper title
- Authors
- Abstract
- Categories
- PDF URL
- arXiv ID

Configuration
-------------

Crawlers respect these settings in ``config/settings.yaml``:

.. code-block:: yaml

   crawlers:
     selenium:
       headless: true          # Run browser without UI
       timeout: 30             # Request timeout (seconds)
       user_agent: "Mozilla/5.0..."

     rate_limits:
       csrankings: 1.0         # Seconds between requests
       scholar: 2.0
       professor: 1.0
       arxiv: 0.5

     cache:
       enabled: true
       ttl: 86400              # Cache TTL in seconds (1 day)

Caching
-------

All crawler results are cached to avoid redundant requests:

- **Cache location**: ``./cache/crawlers/``
- **Cache key**: URL + parameters hash
- **Invalidation**: TTL-based or manual clear

Rate Limiting
-------------

To be respectful to source websites:

- Automatic delays between requests
- Retry with exponential backoff on failures
- Respect ``robots.txt`` where applicable

Error Handling
--------------

Crawlers handle:

* Network timeouts (retry up to 3 times)
* Changed page layouts (graceful degradation)
* CAPTCHA/anti-bot measures (pause and alert)
* Missing data (return partial results)

Adding New Crawlers
-------------------

To add a new data source:

1. Create ``crawlers/newsource.py``
2. Inherit from ``BaseCrawler``
3. Implement ``fetch()`` method
4. Register in ``crawlers/__init__.py``
5. Add tests in ``tests/crawlers/``

Example:

.. code-block:: python

   from phd_hunter.crawlers.base import BaseCrawler

   class DBLPCrawler(BaseCrawler):
       def fetch(self, query: str):
           # Implement crawling logic
           pass

See Also
--------

- :doc:`architecture`
- :doc:`agents`
- :doc:`llm`
- :doc:`api`

Crawlers
========

This module is responsible for fetching data from academic sources. Additionally, the project includes a web frontend interface for data display and interaction.

Overview
--------

Crawlers fetch data from different sources:

* Get professor lists from CSRankings
* Search for papers published by professors from arXiv (by title or by author)
* Scrape professor homepages for AI summary and recent paper titles

All crawlers follow rate limits and include retry logic.

.. note::
   For the web frontend section, see the "Web Frontend" chapter in :doc:`architecture`,
   or check the Flask application code in ``src/phd_hunter/frontend/`` directory.

CSRankings Crawler
------------------

**File**: ``crawlers/csrankings.py``

Extracts professor data from https://csrankings.org.

Features:

* Select specific institutions and CS sub-areas
* Extract professor names, homepages, and affiliations
* Use Selenium to handle dynamic page content

Usage:

.. code-block:: python

   from phd_hunter.crawlers.csrankings import CSRankingsCrawler

   crawler = CSRankingsCrawler(headless=True)
   universities, professors = crawler.fetch(
       areas=["ai"],
       region="world",
       max_professors=5
   )
   # Returns lists of University and Professor objects

Extracted data:

* University name, rank, score
* Professor name
* University URL
* Professor homepage (extracted from ranking page)

arXiv Crawler
-------------

**File**: ``crawlers/arxiv_crawler.py``

Search papers from arXiv by **paper title** or by **author name**.

**Preferred flow** (title search): The system first extracts recent paper titles from the professor's homepage using LLM, then searches arXiv by exact title.  This avoids the name-collision problem common with author-based search.

**Fallback flow** (author search): If the homepage does not list papers, the system falls back to searching by author name.

Features:

* Search papers by **exact title** (primary, avoids name collisions)
* Search papers by **author name** (fallback)
* Author verification: every result is checked against the professor's name
* Sort by submission date (newest first)
* Return paper metadata (title, authors, abstract, year, PDF link)

Usage — title search (recommended):

.. code-block:: python

   from phd_hunter.crawlers.arxiv_crawler import ArxivCrawler
   from phd_hunter.models import Professor

   crawler = ArxivCrawler()
   prof = Professor(name="Yangqiu Song")
   titles = ["Paper Title 1", "Paper Title 2"]
   papers = crawler.fetch_by_titles(prof, titles=titles, max_papers=10)
   # Returns list of Paper objects where the professor is a confirmed author

Usage — author search (fallback):

.. code-block:: python

   crawler = ArxivCrawler()
   prof = Professor(name="Yangqiu Song")
   papers = crawler.fetch(prof, max_papers=10)

Extracted data:

* Paper title
* Author list
* Abstract
* Publication year
* arXiv ID
* PDF URL

Homepage Crawler
----------------

**File**: ``crawlers/homepage_crawler.py``

Scrape professor homepages, generate AI summaries, and extract recent paper titles.

Features:

* Fetch professor homepage via HTTP
* Extract plain text from HTML
* Use LLM to generate summary (research focus, recruiting status, content summary)
* **Extract recent paper titles** from the homepage (used for precise arXiv search)

Usage:

.. code-block:: python

   from phd_hunter.crawlers.homepage_crawler import (
       fetch_and_summarize_homepage,
       load_homepage_papers,
   )

   # Fetch homepage and extract info
   success = await fetch_and_summarize_homepage(
       professor_id=1,
       homepage_url="https://cs.stanford.edu/~prof/",
       professor_name="John Doe",
       db_path="phd_hunter.db"
   )

   # Retrieve extracted paper titles
   titles = load_homepage_papers(1)
   # Returns ["Paper Title 1", "Paper Title 2", ...]

Configuration
-------------

Current configuration is passed via command line parameters. Key parameters:

.. code-block:: text

   CSRankingsCrawler:
     --headless / --no-headless   # Headless mode
     --timeout 30                 # Timeout (seconds)
     --max-professors 5           # Max professors per university

   ArxivCrawler:
     --delay 1.0                  # Request interval (seconds)
     --max-papers 10              # Max papers per professor

   HomepageCrawler:
     Requires LLM configuration in hound_config.json

Caching
-------

All crawler results are cached to avoid redundant requests:

* **Cache location**: Memory cache (in-process)
* **Cache key**: Parameter hash
* **TTL**: Default 1 day

Rate Limiting
-------------

To respect data sources:

* Automatic delay between requests
* arXiv: Default 1 second interval (configurable)

Error Handling
--------------

Crawlers handle:

* Network timeouts (retry)
* Page layout changes (fault tolerance)
* Missing data (return partial results)

Adding New Crawlers
-------------------

To add a new data source:

1. Create ``crawlers/newsource.py``
2. Inherit ``BaseCrawler``
3. Implement ``fetch()`` method
4. Register in ``crawlers/__init__.py``
5. Add command in ``main.py``

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
- :doc:`api`

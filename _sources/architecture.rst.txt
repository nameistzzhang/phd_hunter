Architecture Overview
=====================

This document describes the system architecture of PhD Hunter.

System Design
-------------

PhD Hunter adopts a clean modular design, with four core parts: crawlers, database, web frontend, and command line interface.

.. code-block:: text

   +------------------------------------------------------+
   |    Web Frontend (Flask + HTML/CSS/JS)                |
   |    - Professor cards with priority & filters         |
   |    - Real-time filtering & sorting                   |
   |    - AI chat for analysis & cold email generation    |
   |    - Profile page for CV/PS and arXiv papers         |
   +----------------------+-------------------------------+
                          | REST API
         +----------------+----------------+
         |                |                |
         v                v                v
   +---------+    +----------+    +---------+
   | CLI     |    | Arxiv    |    | SQLite  |
   |(main.py)|    | Crawler  |    |Database |
   +---------+    +----------+    +---------+
         |
         v
   +------------------+
   | CSRankings       |
   | Crawler          |
   +------------------+
   | Homepage         |
   | Crawler          |
   +------------------+

Core Components
---------------

1. **Web Frontend** (frontend/)

   Visualization interface built with Flask + vanilla HTML/CSS/JavaScript:

   - ``app.py``: Flask API server providing JSON data endpoints
   - ``index.html``: Main page with navigation bar, filter bar, professor list, and detail modal
   - ``styles.css``: Black-and-white minimalist stylesheet
   - ``app.js``: Frontend logic (data loading, filtering, priority update, modal display, chat)

   Main features:
   - Professor card display (score, paper count, research areas, priority color bar)
   - Multi-dimensional filtering (Priority / Research Area / University / Score)
   - Priority dropdown modification (real-time save to database)
   - Professor detail modal (basic info, metrics, paper list with arXiv links)
   - AI Chat page (auto-generated analysis report + cold email draft)
   - Profile page (CV/PS upload, arXiv paper management, research preferences)
   - Settings modal (LLM API key, model, temperature configuration)

2. **CLI Entry** (main.py)

   Command-line main program providing subcommands:

   - ``crawl``: Crawl professor information from CSRankings
   - ``fetch-papers``: Fetch professor papers from arXiv
   - ``stats`` / ``list``: View database contents

3. **Crawler Module** (crawlers/)

   - ``CSRankingsCrawler``: Use Selenium to crawl CSRankings.org university rankings and professor lists
   - ``ArxivCrawler``: Use arXiv API to search papers by author
   - ``HomepageCrawler``: Use Selenium to scrape professor homepages and generate AI summaries

   All crawlers inherit from ``BaseCrawler`` with caching support.

4. **Analyzer Module** (analyzer/)

   - ``analyzer.py``: Core logic for professor analysis and cold email generation
   - ``prompts.py``: Prompt templates for LLM

   Based on user Profile (CV/PS/papers) and professor data (homepage summary/papers), generate:
   - Professor research direction analysis
   - Matching points analysis
   - Cold email writing guidelines
   - Complete cold email draft

5. **Scorer Module** (hound/)

   - ``scorer.py``: LLM-based professor matching scoring
   - ``scorer_daemon.py``: Background daemon for automatic scoring

   Two scores (1-5):
   - Direction Match: Research direction matching degree
   - Admission Difficulty: Admission difficulty assessment

6. **Database** (database.py)

   SQLite database containing:

   - ``professors`` table: Professor basic information, scores, homepage summary, chat messages
   - ``papers`` table: Paper metadata
   - ``applicant_profile`` table: User CV/PS, research preferences, arXiv papers

   Provides complete CRUD operations and data export functionality.

7. **Data Models** (models.py)

   Pydantic model definitions:

   - ``Professor``: Professor information
   - ``Paper``: Paper information
   - ``University``: University information

8. **Utility Module** (utils/)

   - ``logger.py``: Structured logging configuration
   - ``helpers.py``: General helper functions
   - ``pdf_extract.py``: PDF text extraction and Profile building

9. **API Infrastructure** (api_infra/)

   - ``core/client.py``: Unified LLM client supporting multiple providers

Data Flow
---------

1. **Crawl Phase**

   .. code-block::

      User -> main.py crawl
         -> CSRankingsCrawler.fetch()
         -> Selenium opens browser
         -> Parse HTML to extract professor list
         -> Database.upsert_professor()
         -> SQLite save

2. **Paper Fetch Phase**

   .. code-block::

      User -> main.py fetch-papers
         -> Database.list_professors()
         -> For each professor:
            ArxivCrawler.fetch(professor)
            -> arxiv.Search query
            -> Parse returned results
            -> Database.upsert_paper()
         -> SQLite save

3. **Homepage Crawl Phase**

   .. code-block::

      User -> HomepageCrawler
         -> Selenium opens professor homepage
         -> Extract page content
         -> LLM generates summary
         -> Database.update_homepage_summary()

4. **Scoring Phase**

   .. code-block::

      ScorerDaemon -> Database.list_unscored_professors()
         -> For each professor:
            Scorer.run()
            -> LLM evaluates direction match & difficulty
            -> Database.update_professor_scores()

5. **Web Interface Query Phase**

   .. code-block::

      Browser -> Flask app.py (GET /api/professors)
         -> Database.list_professors()
         -> JSON returns professor list
         -> JavaScript renders cards + filters

      Browser -> Flask app.py (POST /api/chat/<id>)
         -> Analyzer.chat_with_professor()
         -> LLM generates response
         -> Database.update_professor_messages()

6. **Command Line Query Phase**

   .. code-block::

      User -> main.py stats / list
         -> Database.get_stats() / list_professors()
         -> Formatted output

Configuration
-------------

LLM configuration is stored in ``hound_config.json``:

.. code-block:: json

   {
       "api_key": "your-api-key",
       "model": "deepseek-v3.2",
       "provider": "yunwu",
       "url": "https://yunwu.ai/v1",
       "temperature": 0.6,
       "max_tokens": 800,
       "scoring_iterations": 3,
       "nickname": "YourName"
   }

Extensibility
-------------

Adding new crawlers:

1. Create ``crawlers/newsource.py``
2. Inherit ``BaseCrawler``
3. Implement ``fetch()`` method
4. Register in ``crawlers/__init__.py``
5. Add corresponding command in main.py

Example:

.. code-block:: python

   from .base import BaseCrawler

   class DBLPCrawler(BaseCrawler):
       def fetch(self, query: str):
           # Implement crawling logic
           pass

Development Workflow
--------------------

1. Modify code
2. Run validation: ``python main.py ...``
3. Submit changes

See Also
--------

- :doc:`crawlers`
- :doc:`api`
- :doc:`contributing`

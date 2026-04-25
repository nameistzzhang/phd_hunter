Changelog
=========

All major changes to PhD Hunter will be recorded here.

[0.1.0] - 2026-04-25
---------------------

Added
~~~~~

* **Analyzer Module** - LLM-powered professor analysis and cold email generation
    * Auto-generate professor analysis report + cold email draft on first chat
    * Multi-round conversation to refine cold emails
    * Personalized generation based on user Profile (CV/PS/papers)
* **Profile Page** - Complete user profile management
    * CV/PS PDF upload and text extraction
    * arXiv paper link addition and parsing
    * Research preference settings
* **Professor Matching Scoring** - LLM-driven scoring system
    * Direction Match Score (1-5): Research direction matching degree
    * Admission Difficulty Score (1-5): Admission difficulty assessment
    * Background auto-polling scoring with configurable iterations
* **Homepage Crawler** - Selenium + LLM summary
    * Automatically scrape professor personal homepages
    * AI extraction of research focus, recruiting status, content summary
* **LLM Config Modal** - Configure API Key, model, URL, temperature, etc.
* **Chat Page Improvements**
    * User/AI avatar distinction
    * Message deletion feature
    * "Analyzing..." loading animation
    * Auto-scroll messages
* **Web Interface Improvements**
    * Top bar displays Avg Match / Avg Diff statistics
    * Professor detail paper titles link to arXiv
    * Simplified Basic Info / Metrics layout

Changed
~~~~~~~

* Added ``api_infra`` module for unified LLM client calls
* Added ``utils/pdf_extract.py`` for PDF text extraction, decoupling scorer and analyzer
* Database tables added ``direction_match_score``, ``admission_difficulty_score``, ``homepage_summary``, ``messages`` fields

[0.0.1] - 2026-04-21
---------------------

Added
~~~~~

* ArxivCrawler: Search papers by author
* CLI command ``fetch-papers``: Batch fetch professor papers
* CLI commands ``stats`` / ``list``: Database queries
* Web frontend: Professor browsing, filtering, priority marking

Changed
~~~~~~~

* Main entry moved to root ``main.py``
* Simplified project structure

[0.0.0] - 2026-04-19
---------------------

Added
~~~~~

* Initial project structure
* uv dependency management
* Sphinx documentation system
* CSRankings crawler basic implementation
* SQLite database models

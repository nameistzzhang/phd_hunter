Changelog
=========

All major changes to PhD Hunter will be recorded here.

[0.1.1] - 2026-04-26
---------------------

Added
~~~~~

* **OpenAlex Crawler** - Replaced arXiv author search as primary paper source
    * Institution + author matching for accurate professor identification
    * arXiv link extraction from OpenAlex ``locations`` / ``open_access`` fields
    * Graceful handling of non-arXiv papers (conference/journal work without arXiv ID)
* **arXiv Abstract Enrichment** - Post-process OpenAlex papers with accurate arXiv abstracts
    * ``ArxivCrawler.fetch_by_ids()``: batch query arXiv by ID list
    * Updates DB ``abstract`` and ``openaccess_pdf`` fields when arXiv data is better
* **Professor Modal Enhancements**
    * **Rescore** button: re-run LLM scoring after paper edits
    * **Add Paper**: paste arXiv URL to manually add a paper (with author verification)
    * **Delete Paper**: remove incorrect papers via × button
* **Scorer Daemon Reliability**
    * Persistent event loop in daemon thread (avoids ``event loop closed`` errors)
    * Reduced polling frequency (30s) and inter-professor delay (5s) to avoid API rate limits
* **Database**
    * ``update_paper_by_arxiv_id()``: update paper fields by arxiv_id + professor_id
    * ``delete_paper()``: delete paper by database ID

Changed
~~~~~~~

* **Paper Fetching Flow**: OpenAlex → save to DB → arXiv enrichment (abstract + PDF URL)
* **arXiv Crawler**: ``fetch_by_titles()`` now supports progressive query degradation (full title → 5 words → 3 words) with Jaccard similarity filtering
* **Author Verification**: ``_is_author_match()`` handles initials, last-name-only, and case-insensitive matching
* **Frontend**: defensive ``request.get_json(silent=True)`` across all POST routes

Fixed
~~~~~

* OpenAlex arXiv source matching: exact ``== "arXiv"`` → case-insensitive substring match (handles ``"arXiv (Cornell University)"`` / ``"ArXiv.org"``)
* arXiv ID version stripping: ``2512.02589v2`` → ``2512.02589`` for consistent DB keys
* Second crawl no longer re-processes all existing professors (tracks ``existing_ids_before``)

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
* **Homepage Crawler** - HTTP + LLM summary
    * Automatically fetch professor personal homepages
    * AI extraction of research focus, recruiting status, content summary
    * **Extract recent paper titles** from homepage for precise arXiv search
* **arXiv Title Search** - Precise paper fetching by title
    * Primary flow: extract paper titles from homepage, search arXiv by exact title
    * Author verification on every result to prevent name collisions
    * Fallback to author-name search when homepage lacks publication list
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

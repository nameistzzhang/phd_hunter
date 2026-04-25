PhD Hunter - PhD Advisor Application Assistant
===============================================

PhD Hunter is a lightweight PhD advisor information collection tool focused on automating the acquisition of CS professor information and their latest papers.

Current Features
----------------

* **CSRankings Data Crawling**: Automatically crawl CSRankings website to get university and professor information
* **arXiv Paper Fetching**: Search and save the latest paper metadata by author
* **Homepage Crawling**: Scrape professor homepages and generate AI summaries
* **SQLite Storage**: All data persisted locally
* **Web Visualization Interface**: Interactive professor browsing, filtering, and management based on Flask
* **AI Analysis**: LLM-powered professor matching scoring and cold email generation
* **Profile Management**: Upload CV/PS, manage arXiv papers, set research preferences
* **Priority Tagging**: Mark priority for each professor (Reach/Match/Target/Safety/Not Considered)
* **Multi-dimensional Filtering**: Filter professor list by priority, research area, university, score

Project Architecture
--------------------

.. code-block:: text

    phd_hunter/
    ├── main.py                       # CLI entry (root directory)
    ├── pyproject.toml                # Project configuration
    ├── README.md                     # Project documentation
    ├── docs/                         # Sphinx documentation
    └── src/phd_hunter/
        ├── models.py                 # Pydantic data models
        ├── database.py               # SQLite database operations
        ├── api_infra/                # LLM API infrastructure
        ├── crawlers/
        │   ├── base.py               # Crawler base class (cache support)
        │   ├── csrankings.py         # CSRankings crawler
        │   ├── arxiv_crawler.py      # arXiv crawler
        │   └── homepage_crawler.py   # Homepage crawler
        ├── hound/
        │   └── scorer.py             # Professor scoring
        ├── analyzer/
        │   ├── analyzer.py           # Professor analysis
        │   └── prompts.py            # Prompt templates
        ├── utils/
        │   ├── logger.py             # Logging configuration
        │   ├── helpers.py            # Utility functions
        │   └── pdf_extract.py        # PDF text extraction
        └── frontend/                 # Web frontend interface
            ├── app.py                # Flask API server
            ├── index.html            # Main page
            ├── static/
            │   ├── styles.css        # Stylesheet
            │   ├── app.js            # Frontend logic
            │   └── windsurf.svg      # AI avatar icon
            └── templates/            # HTML templates

Quick Start
-----------

Requirements
~~~~~~~~~~~~

* Python 3.10+
* uv (recommended) or pip
* Chrome/Chromium browser (for Selenium)

Installation Steps
~~~~~~~~~~~~~~~~~~

1. **Clone the repository**

   .. code-block:: bash

      git clone <repository-url>
      cd phd-hunter

2. **Install dependencies**

   Using uv (recommended):

   .. code-block:: bash

      uv sync

   Or using pip:

   .. code-block:: bash

      python -m venv .venv
      .venv\Scripts\activate  # Windows
      pip install -e .

3. **Install api_infra** (REQUIRED for LLM features)

   .. code-block:: bash

      cd src/phd_hunter/api_infra
      pip install -e .
      cd ../../..

4. **Run the application**

   Command line mode:

   .. code-block:: bash

      # Crawl professor data
      python main.py crawl --area ai --region world --max-professors 5

      # Fetch papers
      python main.py fetch-papers --max-papers 10

      # View statistics
      python main.py stats

   Web interface mode:

   .. code-block:: bash

      # Start Flask server (Linux / macOS)
      PYTHONPATH=src python -m phd_hunter.frontend.app

      # Windows (Command Prompt):
      set PYTHONPATH=src && python -m phd_hunter.frontend.app

      # Windows (PowerShell):
      $env:PYTHONPATH="src"; python -m phd_hunter.frontend.app

      # Then open http://localhost:8080 in browser

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   architecture
   crawlers
   api
   contributing
   changelog

Indices and Tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

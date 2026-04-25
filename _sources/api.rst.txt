API Reference
=============

This project provides two types of APIs: command line interface (CLI) and web REST API (Flask).

Web REST API
------------

**Base URL**: ``http://localhost:8080``

The web frontend interacts with the backend through the following JSON APIs:

.. list-table:: API Endpoints
   :header-rows: 1

   * - Method
     - Path
     - Description
   * - ``GET``
     - ``/``
     - Serve homepage (return ``index.html``)
   * - ``GET``
     - ``/api/stats``
     - Get statistics (professor count, paper count, avg scores, etc.)
   * - ``GET``
     - ``/api/professors``
     - Get all professor list
   * - ``GET``
     - ``/api/professor/<int:id>``
     - Get single professor details
   * - ``POST``
     - ``/api/professor/<int:id>/priority``
     - Update professor priority
   * - ``GET``
     - ``/api/chat/<int:id>``
     - Get chat messages for a professor
   * - ``POST``
     - ``/api/chat/<int:id>``
     - Send message or trigger first-time analysis
   * - ``DELETE``
     - ``/api/chat/<int:id>/message``
     - Delete a chat message
   * - ``GET``
     - ``/api/hound-config``
     - Get LLM configuration
   * - ``POST``
     - ``/api/hound-config``
     - Update LLM configuration
   * - ``GET``
     - ``/api/profile``
     - Get applicant profile
   * - ``POST``
     - ``/api/profile``
     - Update applicant profile
   * - ``POST``
     - ``/api/profile/cv``
     - Upload CV PDF
   * - ``POST``
     - ``/api/profile/ps``
     - Upload PS PDF
   * - ``POST``
     - ``/api/profile/papers``
     - Add arXiv paper links
   * - ``POST``
     - ``/api/arxiv/resolve``
     - Resolve arXiv URL to metadata

Detailed examples:

.. code-block:: python

   import requests

   # Get statistics
   stats = requests.get('http://localhost:8080/api/stats').json()
   print(f"Professors: {stats['professors']}, Papers: {stats['papers']}")

   # Get professor list
   data = requests.get('http://localhost:8080/api/professors').json()
   professors = data['professors']

   # Update priority
   response = requests.post(
       'http://localhost:8080/api/professor/1/priority',
       json={'priority': 1}
   )
   # Returns: {"success": true, "priority": 1}

   # Send chat message
   response = requests.post(
       'http://localhost:8080/api/chat/1',
       json={'message': 'Can you make the email shorter?'}
   )
   # Returns: {"success": true, "response": "..."}

.. note::
   Web server entry is at ``src/phd_hunter/frontend/app.py``.
   Static files (HTML/CSS/JS) are hosted at ``src/phd_hunter/frontend/static/``.

Command Line Reference
----------------------

Main entry: ``python main.py``

Commands
~~~~~~~~

.. code-block:: text

   phd-hunter crawl [OPTIONS]
   phd-hunter fetch-papers [OPTIONS]
   phd-hunter stats
   phd-hunter list [OPTIONS]

For details, see :doc:`architecture`.

Database API
------------

Direct programmatic access via ``phd_hunter.database.Database`` class.

Quick example:

.. code-block:: python

   from phd_hunter.database import Database
   from phd_hunter.models import Professor, University

   db = Database(db_path="phd_hunter.db")

   # List professors
   professors = db.list_professors(limit=10)

   # Get single professor
   prof = db.get_professor(prof_id=1)

   # Get professor papers
   papers = db.get_papers_by_professor(professor_id=1)

   # Export to JSON
   db.export_to_json("output.json")

Database Class
~~~~~~~~~~~~~~

.. autoclass:: phd_hunter.database.Database
   :members:
   :undoc-members:
   :show-inheritance:

Main Methods
^^^^^^^^^^^^

**Connection and Initialization**

- ``__init__(db_path: str = "phd_hunter.db")``
  Initialize database connection and create tables.

**Professor Operations**

- ``list_professors(status, min_match_score, limit) -> List[Dict]``
  List professors with filtering support.

- ``get_professor(prof_id) -> Optional[Dict]``
  Get professor by ID.

- ``get_professor_by_name(name, university_name) -> Optional[Dict]``
  Get professor by name (optional university).

- ``upsert_professor(prof: Professor, university: University) -> int``
  Insert or update professor record, return database ID.

- ``update_professor_scores(professor_id, direction_match, admission_difficulty)``
  Update professor matching scores.

- ``update_professor_messages(professor_id, messages)``
  Update professor chat messages.

**Paper Operations**

- ``get_papers_by_professor(professor_id, limit) -> List[Dict]``
  Get all papers for a professor.

- ``upsert_paper(professor_id, paper_data) -> int``
  Insert or update paper record.

- ``get_professor_with_papers(professor_id) -> Optional[Dict]``
  Get professor and all papers (joined query).

**Profile Operations**

- ``get_applicant_profile() -> Optional[Dict]``
  Get applicant profile.

- ``upsert_applicant_profile(data)``
  Insert or update applicant profile.

**Statistics and Export**

- ``get_stats() -> Dict``
  Get database statistics.

- ``export_to_json(output_path)``
  Export all data to JSON file.

Model Reference
---------------

Professor
~~~~~~~~~

.. autoclass:: phd_hunter.models.Professor
   :members:
   :undoc-members:
   :show-inheritance:

Paper
~~~~~

.. autoclass:: phd_hunter.models.Paper
   :members:
   :undoc-members:
   :show-inheritance:

University
~~~~~~~~~~

.. autoclass:: phd_hunter.models.University
   :members:
   :undoc-members:
   :show-inheritance:

Crawler Base Class
------------------

.. autoclass:: phd_hunter.crawlers.base.BaseCrawler
   :members:
   :undoc-members:
   :show-inheritance:

CSRankingsCrawler
~~~~~~~~~~~~~~~~~

.. autoclass:: phd_hunter.crawlers.csrankings.CSRankingsCrawler
   :members:
   :undoc-members:
   :show-inheritance:

ArxivCrawler
~~~~~~~~~~~~

.. autoclass:: phd_hunter.crawlers.arxiv_crawler.ArxivCrawler
   :members:
   :undoc-members:
   :show-inheritance:

Analyzer
--------

.. autoclass:: phd_hunter.analyzer.analyzer.analyze_professor_first_time
   :members:

.. autoclass:: phd_hunter.analyzer.analyzer.chat_with_professor
   :members:

See Also
--------

- :doc:`architecture`
- :doc:`crawlers`
- :doc:`contributing`

API Reference
=============

FastAPI backend providing REST endpoints for the PhD Hunter system.

Base URL
--------

Development: ``http://localhost:8000``

Production: Depends on deployment configuration

Authentication
--------------

API key authentication (optional):

.. code-block:: python

   headers = {"X-API-Key": "your-api-key"}
   response = requests.get("/api/professors", headers=headers)

Endpoints
---------

Search
~~~~~~

**POST** ``/api/search``

Initiate a new professor search.

Request:

.. code-block:: json

   {
     "universities": ["MIT", "Stanford", "Berkeley"],
     "research_area": "machine learning",
     "keywords": ["deep learning", "neural networks"],
     "max_professors": 50,
     "include_papers": true
   }

Response:

.. code-block:: json

   {
     "search_id": "uuid-1234",
     "status": "running",
     "estimated_time": 120,
     "results_url": "/api/search/uuid-1234/results"
   }

**GET** ``/api/search/{search_id}/status``

Check search progress.

Response:

.. code-block:: json

   {
     "search_id": "uuid-1234",
     "status": "running",
     "progress": 45,
     "current_step": "fetching_papers",
     "eta_seconds": 60
   }

**GET** ``/api/search/{search_id}/results``

Get search results.

Response:

.. code-block:: json

   {
     "search_id": "uuid-1234",
     "completed": true,
     "total": 25,
     "professors": [
       {
         "id": "prof_001",
         "name": "John Doe",
         "university": "MIT",
         "match_score": 87.5,
         "email": "jdoe@mit.edu",
         "scholar_url": "https://scholar.google.com/...",
         "homepage": "https://...",
         "research_interests": ["ML", "NLP", "Computer Vision"],
         "citation_count": 12500,
         "h_index": 58,
         "recent_papers": 8
       }
     ]
   }

Professors
~~~~~~~~~~

**GET** ``/api/professors``

List all cached professors.

Query parameters:

- ``university``: Filter by university
- ``area``: Filter by research area
- ``min_score``: Minimum match score
- ``limit``: Max results (default 100)
- ``offset``: Pagination offset

Response: Array of professor objects.

**GET** ``/api/professors/{professor_id}``

Get detailed professor data.

Response includes full research analysis.

**GET** ``/api/professors/{professor_id}/papers``

Get professor's papers.

**DELETE** ``/api/professors/{professor_id}``

Remove professor from cache.

Reports
~~~~~~~

**GET** ``/api/reports/{professor_id}``

Get report for a professor.

Query parameters:

- ``format``: ``html``, ``pdf``, ``json``, ``markdown``
- ``sections``: Comma-separated list of sections to include

Response: Report content (or redirect to file).

**POST** ``/api/reports/batch``

Generate reports for multiple professors.

Request:

.. code-block:: json

   {
     "professor_ids": ["prof_001", "prof_002"],
     "format": "pdf",
     "combine": true
   }

Response: ZIP file or download URLs.

**GET** ``/api/reports/compare``

Generate comparison report.

Request:

.. code-block:: json

   {
     "professor_ids": ["prof_001", "prof_002", "prof_003"],
     "metrics": ["match_score", "h_index", "citation_count"]
   }

Papers
~~~~~~

**GET** ``/api/papers``

List papers (with filtering).

**GET** ``/api/papers/{paper_id}``

Get paper details including LLM analysis.

**GET** ``/api/papers/{paper_id}/download``

Download paper PDF.

LLM
~~~

**POST** ``/api/llm/analyze``

Run custom LLM analysis.

Request:

.. code-block:: json

   {
     "system_prompt": "You are a research analyst...",
     "user_content": "Analyze this paper...",
     "schema": { ... }  // Optional structured output schema
   }

Response:

.. code-block:: json

   {
     "content": "...",
     "tokens_used": 1500,
     "model": "gpt-4o",
     "cost": 0.045
   }

**POST** ``/api/llm/embed``

Generate embeddings.

Request:

.. code-block:: json

   {
     "texts": ["paper abstract 1", "paper abstract 2"]
   }

Response:

.. code-block:: json

   {
     "embeddings": [[0.1, 0.2, ...], [...]]
   }

Health
~~~~~~

**GET** ``/health``

Health check.

Response:

.. code-block:: json

   {
     "status": "healthy",
     "version": "0.1.0",
     "timestamp": "2026-04-19T..."
   }

**GET** ``/metrics``

Prometheus metrics.

Configuration
-------------

Configure API in ``config/settings.yaml``:

.. code-block:: yaml

   api:
     host: "0.0.0.0"
     port: 8000
     reload: true        # Development only
     workers: 4          # Production

     cors:
       enabled: true
       origins: ["http://localhost:8501"]

     rate_limit:
       requests_per_minute: 100

     auth:
       enabled: false
       api_keys: []       # List of allowed keys

Python Client
-------------

Convenient Python client:

.. code-block:: python

   from phd_hunter.api import Client

   client = Client(base_url="http://localhost:8000")

   # Search
   results = client.search(
       universities=["MIT", "Stanford"],
       area="NLP"
   )

   # Get report
   report = client.get_report(
       professor_id="prof_001",
       format="pdf"
   )

   # Batch operations
   batch = client.batch_reports(
       professor_ids=["prof_001", "prof_002"],
       format="html"
   )

Error Handling
--------------

API errors return standard HTTP status codes:

- ``200``: Success
- ``400``: Invalid request
- ``401``: Authentication required
- ``403``: Permission denied
- ``404``: Not found
- ``429``: Rate limited
- ``500``: Server error

Error response format:

.. code-block:: json

   {
     "error": "InvalidRequest",
     "message": "University not found",
     "details": {"university": "Unknown University"}
   }

Rate Limiting
-------------

Default: 100 requests/minute per IP

Headers returned:

- ``X-RateLimit-Limit``: Max requests
- ``X-RateLimit-Remaining``: Requests left
- ``X-RateLimit-Reset``: Reset timestamp

When rate limited (429):

.. code-block:: json

   {
     "error": "RateLimitExceeded",
     "retry_after": 60
   }

Webhooks
--------

Optional webhook notifications:

.. code-block:: python

   # Register webhook
   response = requests.post("/api/webhooks", json={
       "url": "https://myserver.com/callback",
       "events": ["search.completed", "report.ready"]
   })

   # Webhook payload
   {
     "event": "search.completed",
     "search_id": "uuid-1234",
     "result_count": 25,
     "timestamp": "2026-04-19T..."
   }

SDKs
----

**Python SDK** (``phd_hunter.api``)

**JavaScript SDK** (coming soon)

**CLI** (``phd-hunter`` command)

.. code-block:: bash

   phd-hunter search --universities MIT --area ML
   phd-hunter report prof_001 --format pdf
   phd-hunter list --university Stanford

See Also
--------

- :doc:`architecture`
- :doc:`frontend`
- :doc:`deployment`

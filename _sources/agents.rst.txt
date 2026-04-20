Agents
======

The agent system orchestrates data collection, analysis, and report generation using specialized AI agents.

Agent Types
-----------

Coordinator Agent
~~~~~~~~~~~~~~~~~

**File**: ``agents/coordinator.py``

The master agent that manages the entire workflow.

Responsibilities:

- Accepts user search queries
- Dispatches tasks to specialized agents
- Manages caching and rate limiting
- Aggregates results
- Handles errors and retries

Example flow:

.. code-block:: python

   from phd_hunter.agents.coordinator import CoordinatorAgent

   coordinator = CoordinatorAgent()
   results = coordinator.search(
       universities=["MIT", "Stanford"],
       research_area="machine learning"
   )
   # Returns list of ProfessorReport objects

Researcher Agent
~~~~~~~~~~~~~~~~

**File**: ``agents/researcher.py``

Analyzes professor research and evaluates fit.

Responsibilities:

- Fetches and processes papers
- Uses LLM to analyze research directions
- Computes relevance scores
- Identifies key techniques and methods

Analysis dimensions:

1. **Research Alignment**: How well does the professor's work match your interests?
2. **Recent Activity**: How active is the professor? (papers/year)
3. **Collaboration Network**: Co-author diversity and frequency
4. **Student Mentorship**: History of advising students ( inferred from co-author patterns)
5. **Funding Indicators**: Grant mentions, industry partnerships

Reporter Agent
~~~~~~~~~~~~~~

**File**: ``agents/reporter.py``

Generates comprehensive assessment reports.

Responsibilities:

- Assembles data from all sources
- Generates narrative summaries
- Creates match scores and recommendations
- Outputs multiple formats (HTML, PDF, JSON)

Report sections:

1. **Executive Summary**: High-level recommendation
2. **Professor Profile**: Basic info and contact
3. **Research Analysis**: Themes, methods, recent work
4. **Fit Assessment**: Strengths and concerns
5. **Application Strategy**: Suggested approach for contact
6. **Risk Factors**: Potential issues to consider

Agent Communication
------------------

Agents communicate via structured messages:

.. code-block:: python

   message = AgentMessage(
       sender="coordinator",
       recipient="researcher",
       task="analyze_papers",
       data={"professor_id": "123", "paper_ids": ["arxiv:1234"]}
   )

Workflow
--------

Typical search workflow:

.. code-block:: text

   1. User Query
      ↓
   2. Coordinator → CSRankings Crawler
      (Get professor list)
      ↓
   3. For each professor:
      a. → Scholar Crawler (get papers)
      b. → Professor Crawler (get info)
      c. → ArXiv Crawler (download papers)
      ↓
   4. Coordinator → Researcher Agent
      (Analyze all data)
      ↓
   5. Researcher → LLM (paper analysis prompts)
      ↓
   6. Coordinator → Reporter Agent
      (Generate reports)
      ↓
   7. Results returned to frontend

LLM Integration
---------------

Agents use LLM for analysis via the ``LLMClient``:

.. code-block:: python

   from phd_hunter.llm.client import LLMClient

   client = LLMClient()
   response = client.analyze(
       system_prompt="You are a research analyst...",
       user_content="Analyze this paper's contribution..."
   )

Prompt templates are defined in ``llm/prompts.py``:

- Paper summarization
- Research theme extraction
- Professor profiling
- Fit assessment

Configuration
-------------

Agent settings in ``config/settings.yaml``:

.. code-block:: yaml

   agents:
     coordinator:
       max_parallel: 5           # Max concurrent professor analyses
       timeout: 300              # Seconds per professor

     researcher:
       batch_size: 10            # Papers per LLM call
       context_window: 128000    # Token limit

     reporter:
       template: "comprehensive" # Report style
       include_original: true    # Keep raw data

Caching & Persistence
---------------------

Agent results are cached:

- **Redis** (optional) for shared cache
- **SQLite** for persistent storage
- **File-based** fallback

Cache keys:

- ``professor:{id}``: Professor data
- ``papers:{professor_id}``: Paper list
- ``analysis:{paper_id}``: LLM analysis
- ``report:{professor_id}``: Final report

Extensibility
-------------

Add custom agents:

1. Create ``agents/my_agent.py``
2. Inherit from ``BaseAgent``
3. Implement ``process()`` method
4. Register in ``agents/__init__.py``
5. Update coordinator to use it

See Also
--------

- :doc:`architecture`
- :doc:`crawlers`
- :doc:`llm`
- :doc:`api`

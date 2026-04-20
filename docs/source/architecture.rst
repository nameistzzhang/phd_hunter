Architecture Overview
=====================

This document describes the system architecture of PhD Hunter.

System Design
-------------

PhD Hunter follows a modular, agent-based architecture where specialized agents work together to collect, analyze, and report on potential PhD advisors.

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────────┐
   │                         Frontend (Streamlit)                    │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
   │  │   Search    │  │  Results    │  │   Reports   │            │
   │  │    Page     │  │   Page      │  │    Page     │            │
   │  └─────────────┘  └─────────────┘  └─────────────┘            │
   └─────────────────────────────┬───────────────────────────────────┘
                                 │ HTTP/REST
                    ┌────────────▼────────────┐
                    │   FastAPI Backend       │
                    │  ┌──────────────────┐  │
                    │  │  API Routes      │  │
                    │  │  - /search       │  │
                    │  │  - /professors   │  │
                    │  │  - /reports      │  │
                    │  └──────────────────┘  │
                    └────────────┬────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌───────▼───────┐    ┌───────────▼──────────┐   ┌────────▼─────────┐
│  Coordinator  │    │    Researcher        │   │    Reporter      │
│    Agent      │◄───►│     Agent            │◄──►│     Agent        │
│               │    │                      │   │                  │
│ - Orchestrate │    │ - Fetch papers       │   │ - Generate       │
│ - Manage flow │    │ - Analyze content    │   │   reports        │
│ - Cache mgmt  │    │ - Score relevance    │   │ - Format output  │
└───────┬───────┘    └───────────┬──────────┘   └────────┬─────────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐   ┌──────────────────┐
│   Crawlers       │    │   LLM Client     │   │   Templates      │
│                  │    │                  │   │                  │
│ - csrankings     │    │ - OpenAI API     │   │ - HTML           │
│ - google_scholar │    │ - Anthropic API  │   │ - PDF            │
│ - professor      │    │ - Prompt mgmt    │   │ - Markdown       │
│ - arxiv          │    │ - Rate limiting  │   │                  │
└──────────────────┘    └──────────────────┘   └──────────────────┘

Core Components
---------------

1. **Crawlers** (crawlers/)

   Web crawlers for gathering data from various sources:

   - ``csrankings.py``: Scrapes CSRankings.org for university rankings and faculty lists
   - ``scholar.py``: Fetches publication data from Google Scholar profiles
   - ``professor.py``: Parses professor homepages for contact info and research interests
   - ``arxiv.py``: Downloads papers from arXiv API

2. **Agents** (agents/)

   Intelligent agents that process information:

   - ``coordinator.py``: Orchestrates the entire workflow, manages caches
   - ``researcher.py``: Analyzes papers and evaluates professor-student fit
   - ``reporter.py``: Generates final assessment reports

3. **LLM Module** (llm/)

   LLM integration layer:

   - ``client.py``: Unified interface for OpenAI and Anthropic APIs
   - ``prompts.py``: System prompts and templates for different analysis tasks

4. **Reports** (reports/)

   Report generation and management:

   - ``templates/``: Jinja2 templates for HTML/PDF reports
   - ``generator.py``: Assembles report components

5. **Utils** (utils/)

   Shared utilities:

   - ``config.py``: Configuration loading and validation
   - ``logger.py``: Structured logging setup
   - ``helpers.py``: Common helper functions

6. **Frontend** (frontend/)

   User interface:

   - ``app.py``: Main Streamlit application
   - ``pages/``: Additional pages (history, settings, about)

Data Flow
---------

1. **Search Phase**

   User inputs target universities/areas → Coordinator queries CSRankings → Crawler extracts professor list → Results cached.

2. **Research Phase**

   For each professor:

   - Fetch Google Scholar profile → Get recent papers
   - Download papers from arXiv (if available)
   - Crawl professor homepage for research interests
   - LLM analyzes papers and extracts themes
   - Compute match score

3. **Report Phase**

   Coordinator aggregates all data → Reporter generates comprehensive report → User reviews results.

Configuration
-------------

See :doc:`/installation` for setup details. Key configuration files:

- ``config/settings.yaml``: Main configuration
- ``pyproject.toml``: Python dependencies and project metadata

Extensibility
-------------

The modular design makes it easy to extend:

- Add new crawlers for additional sources (e.g., DBLP, Semantic Scholar)
- Integrate different LLM providers
- Customize report templates
- Add new analysis agents

Development Workflow
--------------------

1. Create a new branch for features
2. Write tests in ``tests/``
3. Run ``uv run pytest`` to test
4. Update documentation in ``docs/``
5. Submit PR

See Also
--------

- :doc:`crawlers`
- :doc:`agents`
- :doc:`llm`
- :doc:`reports`
- :doc:`frontend`
- :doc:`api`

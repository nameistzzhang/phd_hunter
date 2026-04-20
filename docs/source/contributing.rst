Contributing
============

Thank you for considering contributing to PhD Hunter! This document outlines the development workflow.

Getting Started
---------------

1. **Fork and clone**

   .. code-block:: bash

      git clone https://github.com/your-username/phd-hunter.git
      cd phd-hunter

2. **Set up development environment**

   .. code-block:: bash

      uv sync
      uv run pre-commit install

3. **Create a branch**

   .. code-block:: bash

      git checkout -b feature/my-feature

Development Workflow
--------------------

1. **Write code**

   Follow PEP 8, use type hints.

   Example:

   .. code-block:: python

      from typing import Optional

      def search_professor(
          name: str,
          university: Optional[str] = None
      ) -> Professor:
          """Search for a professor by name."""
          ...

2. **Write tests**

   Place tests in ``tests/`` mirroring source structure.

   .. code-block:: python

      # tests/crawlers/test_csrankings.py
      def test_csrankings_fetch():
          crawler = CSRankingsCrawler()
          result = crawler.fetch()
          assert len(result) > 0

3. **Run tests**

   .. code-block:: bash

      uv run pytest tests/ -v

4. **Lint and format**

   .. code-block:: bash

      uv run ruff check .
      uv run black .

5. **Check types**

   .. code-block:: bash

      uv run mypy src/phd_hunter/

6. **Commit**

   Follow conventional commits:

   .. code-block:: text

      feat: add arxiv download batch mode
      fix: handle scholar profile not found
      docs: update installation guide
      refactor: simplify crawler base class
      test: add tests for professor parser

   Pre-commit hooks will run automatically.

7. **Push and PR**

   .. code-block:: bash

      git push origin feature/my-feature

   Open a PR on GitHub with:

   - Clear description
   - Linked issue (if applicable)
   - Screenshots for UI changes
   - Updated documentation

Code Style
----------

**Python**: PEP 8, 88 character line limit

**Type hints**: Required for all public functions

   .. code-block:: python

      def process_paper(paper: Paper) -> Analysis:
          ...

**Docstrings**: Google style

   .. code-block:: python

      def fetch_professor(name: str) -> Professor:
          """Fetch professor data from CSRankings.

          Args:
              name: Professor's full name

          Returns:
              Professor object with extracted data

          Raises:
              CrawlerError: If page cannot be fetched
          """
          ...

**Imports**: Standard library → third-party → local

   .. code-block:: python

      import os
      from pathlib import Path

      import requests
      from bs4 import BeautifulSoup

      from phd_hunter.config import settings

Testing
-------

**Unit tests**: Test individual functions

.. code-block:: python

   def test_parse_email():
       html = "<a href='mailto:test@univ.edu'>"
       email = parse_email(html)
       assert email == "test@univ.edu"

**Integration tests**: Test component interactions

.. code-block:: python

   def test_crawl_and_analyze():
       professor = crawler.fetch("Prof Name")
       analysis = researcher.analyze(professor)
       assert analysis.score > 0

**Run all tests**:

.. code-block:: bash

   uv run pytest tests/ -v --cov=phd_hunter --cov-report=html

Project Structure
-----------------

.. code-block:: text

   phd_hunter/
   ├── __init__.py           # Package init
   ├── main.py              # Entry point
   ├── config.py            # Configuration
   │
   ├── crawlers/            # Web scrapers
   │   ├── __init__.py
   │   ├── base.py          # BaseCrawler class
   │   ├── csrankings.py
   │   └── ...
   │
   ├── agents/              # AI agents
   │   ├── __init__.py
   │   ├── base.py
   │   ├── coordinator.py
   │   └── ...
   │
   ├── llm/                 # LLM integration
   │   ├── __init__.py
   │   ├── client.py
   │   └── prompts.py
   │
   ├── reports/             # Report generation
   │   ├── __init__.py
   │   ├── generator.py
   │   └── templates/
   │
   ├── utils/               # Utilities
   │   ├── __init__.py
   │   ├── logger.py
   │   └── cache.py
   │
   └── frontend/            # Streamlit UI
       ├── app.py
       └── pages/

Adding Features
---------------

1. **Add a new crawler**

   - Create ``crawlers/newsource.py``
   - Inherit from ``BaseCrawler``
   - Implement ``fetch()`` method
   - Add tests in ``tests/crawlers/``
   - Update ``crawlers/__init__.py``

2. **Add a new agent**

   - Create ``agents/myagent.py``
   - Inherit from ``BaseAgent``
   - Implement ``process()`` method
   - Register in ``coordinator.py``
   - Add tests

3. **Add a new report format**

   - Create ``reports/formats/myformat.py``
   - Implement ``generate()``
   - Add to factory in ``generator.py``

4. **Update documentation**

   - Update relevant ``docs/source/*.rst``
   - Add docstrings to code
   - Update README if needed

Documentation
-------------

Build docs locally:

.. code-block:: bash

   cd docs
   make html

View: ``docs/build/html/index.html``

Submit docs changes with code changes.

Pull Request Checklist
----------------------

- [ ] Code follows style guide
- [ ] Tests added/updated and passing
- [ ] Type hints complete
- [ ] Docstrings updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Pre-commit hooks passed

Release Process
---------------

1. Update version in ``pyproject.toml``
2. Update ``CHANGELOG.md``
3. Create release PR
4. Merge to main
5. Create GitHub release
6. Publish to PyPI:

   .. code-block:: bash

      uv publish

Getting Help
------------

- Issues: https://github.com/your-org/phd-hunter/issues
- Discussions: https://github.com/your-org/phd-hunter/discussions
- Email: team@phdhunter.dev

Code of Conduct
---------------

Be respectful, constructive, and inclusive. See ``CODE_OF_CONDUCT.md``.

License
-------

MIT License - see ``LICENSE`` file.

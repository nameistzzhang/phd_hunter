Contributing
============

Thank you for considering contributing to PhD Hunter! This document outlines the development workflow.

Quick Start
-----------

1. **Fork and clone**

   .. code-block:: bash

      git clone https://github.com/your-username/phd-hunter.git
      cd phd-hunter

2. **Set up development environment**

   .. code-block:: bash

      uv sync

3. **Create a branch**

   .. code-block:: bash

      git checkout -b feature/my-feature

Development Workflow
--------------------

1. **Write code**

   Follow PEP 8, use type hints.

   .. code-block:: python

      from typing import Optional

      def search_professor(
          name: str,
          university: Optional[str] = None
      ) -> Professor:
          """Search for a professor by name."""
          ...

2. **Run tests**

   .. code-block:: bash

      python -m pytest tests/ -v

3. **Code formatting**

   .. code-block:: bash

      uv run black .
      uv run ruff check .

4. **Commit**

   Follow conventional commits:

   .. code-block:: text

      feat: add arxiv batch mode
      fix: handle professor not found
      docs: update installation guide

Code Standards
--------------

**Python**: PEP 8, 88 character line limit

**Type hints**: Required for all public functions

**Docstrings**: Google style

**Imports**: stdlib -> third-party -> local

Adding Features
---------------

1. **Add new crawler**

   - Create ``crawlers/newsource.py``
   - Inherit ``BaseCrawler``
   - Implement ``fetch()`` method
   - Register in ``crawlers/__init__.py``
   - Add command in ``main.py``

2. **Modify CLI**

   Add new subcommands and arguments in ``main.py``.

Documentation
-------------

Build documentation:

.. code-block:: bash

   cd docs
   make html

Update documentation when submitting code.

Pull Request Checklist
----------------------

- [ ] Code follows standards
- [ ] Tests pass
- [ ] Type hints are complete
- [ ] Docstrings updated
- [ ] Documentation updated
- [ ] CHANGELOG updated

Getting Help
------------

- Issues: https://github.com/your-org/phd-hunter/issues
- Email: team@phdhunter.dev

License
-------

MIT License - see ``LICENSE`` file.

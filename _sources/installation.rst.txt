Installation Guide
==================

This guide will help you set up PhD Hunter on your machine.

Prerequisites
-------------

- **Python**: 3.10 or higher
- **uv**: Recommended package manager (or pip)
- **Browser**: Chrome or Chromium (for Selenium web crawling)

Step-by-Step Installation
--------------------------

1. **Clone the Repository**

   .. code-block:: bash

      git clone https://github.com/your-org/phd-hunter.git
      cd phd-hunter

2. **Create Virtual Environment**

   Using **uv** (recommended):

   .. code-block:: bash

      # Sync dependencies from pyproject.toml
      uv sync

      # Activate the virtual environment
      # On Windows (PowerShell):
      .venv\\Scripts\\Activate.ps1
      # On Windows (CMD):
      .venv\\Scripts\\activate.bat
      # On Unix/macOS:
      source .venv/bin/activate

   Using **pip**:

   .. code-block:: bash

      python -m venv .venv
      .venv\\Scripts\\activate  # Windows
      pip install -e ".[dev]"

3. **Install Browser Driver**

   PhD Hunter uses Selenium for web crawling. You need Chrome/Chromium and ChromeDriver:

   - **Option A: Automatic installation** (推荐)

     .. code-block:: bash

        uv run pip install webdriver-manager

   - **Option B: Manual installation**

     1. Download ChromeDriver from https://chromedriver.chromium.org/
     2. Add ChromeDriver to your PATH

4. **Configure Environment**

   Copy the example configuration:

   .. code-block:: bash

      copy config\\settings.example.yaml config\\settings.yaml

   Edit ``config/settings.yaml`` and add your API keys:

   .. code-block:: yaml

      # LLM Configuration
      llm:
        provider: "openai"        # "openai" or "anthropic"
        api_key: "sk-..."         # Your API key
        model: "gpt-4o"           # Model to use
        temperature: 0.3
        max_tokens: 4096

      # Crawler Configuration
      crawlers:
        selenium:
          headless: true          # Run browser in background
          timeout: 30             # Request timeout (seconds)
          user_agent: "Mozilla/5.0..."

      # Output Configuration
      output:
        reports_dir: "./reports"
        papers_dir: "./papers"
        cache_dir: "./cache"

      # Database (optional)
      database:
        enabled: false
        url: "sqlite:///phd_hunter.db"

5. **Verify Installation**

   Run the test suite:

   .. code-block:: bash

      uv run pytest tests/ -v

   Or run a quick sanity check:

   .. code-block:: bash

      uv run python -c "import phd_hunter; print('OK')"

Troubleshooting
---------------

**Issue**: ``ModuleNotFoundError: No module named 'phd_hunter'``

**Solution**: Make sure you've installed the package in development mode:

.. code-block:: bash

   pip install -e .

**Issue**: Selenium WebDriver errors

**Solution**: Ensure Chrome/Chromium is installed and ChromeDriver matches your browser version.

**Issue**: ``PermissionError`` on Windows

**Solution**: Run PowerShell as Administrator or use:

.. code-block:: bash

   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

Next Steps
----------

- Read the :doc:`architecture` documentation
- Learn about :doc:`crawlers`
- Explore the :doc:`frontend`

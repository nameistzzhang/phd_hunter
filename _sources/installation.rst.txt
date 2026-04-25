Installation Guide
==================

This guide helps you set up PhD Hunter locally.

Prerequisites
-------------

* **Python**: 3.10 or higher
* **uv**: Recommended package manager (or pip)
* **Browser**: Chrome or Chromium (for Selenium)

Step-by-Step Installation
-------------------------

1. **Clone the repository**

   .. code-block:: bash

      git clone https://github.com/your-org/phd-hunter.git
      cd phd-hunter

2. **Install dependencies**

   Using **uv** (recommended):

   .. code-block:: bash

      uv sync

   Using **pip**:

   .. code-block:: bash

      python -m venv .venv
      .venv\Scripts\activate  # Windows
      pip install -e .

   Using **uv pip**:

   .. code-block:: bash

      uv pip install -e .

3. **Install api_infra** (REQUIRED for LLM features)

   .. code-block:: bash

      cd src/phd_hunter/api_infra
      pip install -e .
      cd ../../..

4. **Install browser driver**

   PhD Hunter uses Selenium for web crawling. Chrome/Chromium and ChromeDriver are required:

   - **Option A: Automatic installation** (recommended)

     .. code-block:: bash

        uv run pip install webdriver-manager

   - **Option B: Manual installation**

     1. Download ChromeDriver from https://chromedriver.chromium.org/
     2. Add ChromeDriver to PATH

5. **Configure LLM**

   Copy the example config and fill in your API key:

   .. code-block:: bash

      cp src/phd_hunter/frontend/hound_config.example.json src/phd_hunter/frontend/hound_config.json

   Edit ``hound_config.json`` with your API key, model, and provider settings.

5. **Verify installation**

   Run a quick check:

   .. code-block:: bash

      python main.py --help

   You should see a list of available commands.

Troubleshooting
---------------

**Issue**: ``ModuleNotFoundError: No module named 'phd_hunter'``

**Solution**: Make sure the package is installed:

.. code-block:: bash

   pip install -e .

**Issue**: Selenium WebDriver error

**Solution**: Ensure Chrome/Chromium is installed and ChromeDriver version matches.

**Issue**: Permission error on Windows

**Solution**: Run PowerShell as administrator or modify execution policy:

.. code-block:: bash

   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

Next Steps
----------

- Read :doc:`architecture` to understand the architecture
- Learn :doc:`crawlers` to understand crawlers
- Check :doc:`api` for API reference

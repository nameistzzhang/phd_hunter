# PhD Hunter 🎓

**PhD Advisor Application Assistant** - Automate CS professor information collection, intelligent matching analysis, and cold email generation

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status](https://img.shields.io/badge/status-v0.1-green.svg)

> 📖 **Full documentation**: https://nameistzzhang.github.io/phd_hunter/

## ✨ Features

### Data Collection
- 📊 **CSRankings Crawler** - Automatically fetch CS professor rankings and lists
- 📚 **OpenAlex Paper Fetching** - Fetch papers via institution + author matching (primary source)
- 🔗 **arXiv Abstract Enrichment** - Supplement OpenAlex abstracts with accurate arXiv data
- 🏠 **Homepage Scraping** - Scrape professor homepages and generate AI summaries
- 💾 **SQLite Storage** - All data persisted locally

### AI Analysis
- 🤖 **Professor Matching Scoring** - LLM-based direction match (1-5) and admission difficulty (1-5)
- 💬 **Intelligent Chat Analysis** - One-click professor analysis report + cold email draft
- 🎯 **Personalized Cold Emails** - Customized emails based on your Profile (CV/PS/papers)

### Web Frontend
- 🌐 **Modern SPA Interface** - Flask-based interactive single-page application
- 🏷️ **Priority Management** - Reach / Match / Target / Safety / Not Considered
- 🔍 **Multi-dimensional Filtering** - By priority, research area, university, score
- 👤 **Profile Management** - Upload CV/PS, manage arXiv papers, set research preferences
- ⚙️ **LLM Configuration** - Configure API Key, model, temperature, iterations

## 🚀 Quick Start

### Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Chrome/Chromium browser (for Selenium homepage scraping)

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd phd-hunter

# 2. Install dependencies
# Using uv (recommended):
uv sync
# Or using pip:
pip install -e .
# Or using uv pip:
uv pip install -e .

# 3. Install api_infra (REQUIRED for LLM features)
cd src/phd_hunter/api_infra
pip install -e .
cd ../../..
```

### ⚠️ Required Configuration

**You must create the config files before running the application.**

```bash
# 1. Configure LLM parameters (REQUIRED for AI features)
cp src/phd_hunter/frontend/hound_config.example.json src/phd_hunter/frontend/hound_config.json
# Edit hound_config.json and fill in your API key and model settings

# 2. Configure crawl parameters (optional)
cp src/phd_hunter/frontend/hunt_config.example.json src/phd_hunter/frontend/hunt_config.json
```

**`hound_config.json` example:**
```json
{
  "api_key": "your-api-key-here",
  "model": "deepseek-v3.2",
  "provider": "yunwu",
  "url": "https://yunwu.ai/v1",
  "temperature": 0.6,
  "max_tokens": 800,
  "scoring_iterations": 3,
  "nickname": "YourName"
}
```

> **Note**: Without `hound_config.json`, the Analyzer (chat), Scorer (matching score), and Homepage Crawler will not work. You can still browse professor data and manage priorities without it.

### Data Collection (CLI Mode)

```bash
# 1. Crawl professor data
python main.py crawl --area ai --region world --max-professors 5

# 2. Fetch papers
python main.py fetch-papers --max-papers 10

# 3. Scrape professor homepages (requires LLM config)
python -m phd_hunter.crawlers.homepage_crawler

# 4. Run matching score (requires LLM config)
python -m phd_hunter.hound.scorer

# 5. View statistics
python main.py stats
```

### Start Web Interface

```bash
# Start Flask Web Server (default http://localhost:8080)

# Linux / macOS:
PYTHONPATH=src python -m phd_hunter.frontend.app

# Windows (Command Prompt):
set PYTHONPATH=src && python -m phd_hunter.frontend.app

# Windows (PowerShell):
$env:PYTHONPATH="src"; python -m phd_hunter.frontend.app
```

Then open http://localhost:8080 in your browser:

- **Hunt page**: Browse professor cards, filter, sort, mark priorities
- **Chat page**: Click a professor to start AI conversation with auto-generated analysis and cold email draft
- **Profile page**: Upload CV/PS, add arXiv papers, set research preferences

## 📁 Project Structure

```
phd_hunter/
├── main.py                       # CLI entry
├── pyproject.toml                # Project config
├── README.md                     # This file
├── docs/                         # Sphinx documentation
├── tests/                        # Test files
└── src/phd_hunter/
    ├── __init__.py               # Package init
    ├── models.py                 # Pydantic data models
    ├── database.py               # SQLite database operations
    ├── api_infra/                # LLM API infrastructure
    │   ├── __init__.py
    │   └── core/
    │       └── client.py         # Unified LLM client
    ├── crawlers/
    │   ├── __init__.py           # Export crawlers
    │   ├── base.py               # Crawler base class (with caching)
    │   ├── csrankings.py         # CSRankings crawler (Selenium)
    │   ├── openalex_crawler.py   # OpenAlex crawler (primary paper source)
    │   ├── arxiv_crawler.py      # arXiv crawler (abstract enrichment + manual add)
    │   └── homepage_crawler.py   # Homepage scraper + AI summary
    ├── hound/
    │   ├── __init__.py
    │   ├── scorer.py             # Professor matching scorer
    │   └── scorer_daemon.py      # Background auto-scoring daemon
    ├── analyzer/
    │   ├── __init__.py           # Export analyze_professor, chat_with_professor
    │   ├── analyzer.py           # Professor analysis + cold email core
    │   └── prompts.py            # Analyzer prompt templates
    ├── utils/
    │   ├── logger.py             # Logging config
    │   ├── helpers.py            # Utility functions
    │   └── pdf_extract.py        # PDF text extraction + Profile builder
    └── frontend/                 # Web frontend
        ├── app.py                # Flask API server
        ├── index.html            # Main page
        ├── hound_config.json     # LLM config (create from example!)
        ├── hunt_config.json      # Crawl config (create from example!)
        ├── static/
        │   ├── styles.css        # Stylesheet
        │   ├── app.js            # Frontend logic
        │   └── windsurf.svg      # AI avatar icon
        └── templates/            # HTML templates
```

## 🗄️ Database Schema

SQLite database with core tables:

### professors table
- Basic info: name, university, rank, department, email, homepage
- Research interests, priority (-1~3)
- AI analysis: homepage_summary, direction_match_score, admission_difficulty_score
- Chat history: messages (JSON)

### papers table
- Paper metadata (title, authors, abstract, year, venue)
- arXiv ID, PDF link, citation count
- Linked to professor record

### applicant_profile table
- User Profile: CV text, PS text
- Research preferences, arXiv paper list

## 🔧 Core Modules

### Analyzer - Professor Analysis & Cold Email

Based on your Profile and professor data, auto-generates:
1. Professor research direction analysis
2. Matching points between you and the professor
3. Cold email writing guidelines
4. Complete cold email draft

Supports multi-round conversation to refine the draft.

### Scorer - Matching Score

Uses LLM to score each professor:
- **Direction Match** (1-5): Research direction matching degree
- **Admission Difficulty** (1-5): Admission difficulty assessment

### Homepage Crawler - Homepage Scraping

Uses Selenium to scrape professor homepages, then LLM extracts:
- Research focus
- Recruiting status
- Homepage content summary

## 🌐 Web Interface Guide

### 1. Configure LLM

Click the ⚙️ settings icon in the top-right corner to configure:
- API Key
- Provider / Model
- URL (custom API endpoint)
- Temperature / Max Tokens
- Scoring Iterations

### 2. Complete Your Profile

Go to the Profile page:
- Upload CV and PS (PDF format)
- Add interesting arXiv paper links
- Set research preferences

### 3. Browse Professors

The Hunt page displays all professor cards:
- Top bar shows statistics: universities, professors, papers, avg scores
- Use filter bar to filter by priority / area / university / score
- Click professor card to view details (papers link to arXiv)

**Professor Detail Modal:**
- **Rescore** — Re-run LLM scoring after editing papers
- **Add Paper** — Paste an arXiv URL to manually add a paper
- **Delete Paper** — Remove incorrect papers with the × button

### 4. AI Chat Analysis

Click Chat to enter the conversation:
- First entry auto-analyzes professor and generates cold email draft
- Continue the conversation to modify or ask questions
- Each message can be individually deleted

## 📊 CLI Reference

### `crawl` - Crawl professor information

```bash
python main.py crawl --area ai --region world --max-professors 5
```

**Parameters:**
- `--area`: Research area (default: `ai`)
- `--region`: Region filter (default: `world`)
- `--max-universities`: Max university count (default: all)
- `--max-professors`: Max professors per university (default: 5)
- `--no-headless`: Show browser window
- `--timeout`: Page timeout (seconds, default: 30)

### `fetch-papers` - Fetch papers

```bash
python main.py fetch-papers --max-papers 10 --max-professors 50
```

**Parameters:**
- `--max-papers`: Max papers per professor (default: 10)
- `--max-professors`: Max professors to process (default: all)
- `--delay`: Request interval (seconds, default: 1.0)

### `stats` - Statistics

```bash
python main.py stats
```

## ⚠️ Known Limitations

1. **arXiv vs Non-arXiv Papers**: OpenAlex covers all venues, but only papers with an arXiv association get enriched with full abstracts and PDF links. Pure conference/journal papers may have limited metadata.
2. **OpenAlex Institution Matching**: Author identification relies on OpenAlex's institution linking. Professors with ambiguous names or recent institution changes may occasionally be misidentified.
3. **LLM Cost**: Analyzer, Scorer, and Homepage Paper Extraction all require LLM API calls. Watch your budget.
4. **Homepage Scraping**: Some professor homepages have anti-bot mechanisms and may fail. Homepage extraction is best-effort; missing data does not block other features.

## 📖 Documentation

- 📚 **Online Docs**: https://nameistzzhang.github.io/phd_hunter/
- 📁 **Local Docs**: See `docs/` directory
  - [Installation Guide](docs/source/installation.rst)
  - [System Architecture](docs/source/architecture.rst)
  - [Crawler Module](docs/source/crawlers.rst)
  - [API Reference](docs/source/api.rst)
  - [Changelog](docs/source/changelog.rst)

Build docs locally:
```bash
cd docs && make html
```

## 🧪 Development

### Run Tests

```bash
uv run pytest tests/ -v
```

### Code Checks

```bash
uv run black --check src/
uv run ruff check src/
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgements

- [CSRankings](http://csrankings.org/) - Professor data source
- [OpenAlex](https://openalex.org/) - Primary paper and author data source
- [arXiv](https://arxiv.org/) - Paper abstract enrichment and manual addition
- [Semantic Scholar](https://www.semanticscholar.org/) - Supplementary paper data

---

**⭐ Star this repo if it helps you!**

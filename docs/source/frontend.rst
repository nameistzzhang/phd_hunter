Frontend
========

The frontend is built with Streamlit, providing an interactive web interface for searching, browsing, and reviewing professor assessments.

Getting Started
---------------

Launch the frontend:

.. code-block:: bash

   uv run streamlit run frontend/app.py

Then open http://localhost:8501 in your browser.

Pages
-----

**Home Page** (app.py)
   Main search interface:

   - Search by university, research area, or professor name
   - Filter by rankings, location, funding
   - View real-time progress

**Results Page**
   Displays professor cards:

   - Match score (0-100)
   - Key metrics (citations, recent papers)
   - Quick actions (view report, contact info)

**Professor Detail Page**
   Full report for a single professor:

   - Executive summary
   - Research analysis
   - Fit assessment
   - Contact information
   - Download options (PDF, JSON)

**Settings Page**
   Configure the application:

   - API keys
   - Crawler settings
   - Report preferences

**History Page**
   View past searches and saved professors.

UI Components
-------------

**Professor Card**

.. code-block:: text

   ┌─────────────────────────────────────┐
   │  Prof. John Doe  ────────────────┐  │
   │  MIT CSAIL                      │  │
   │                                  │  │
   │  Match Score: 87%        [VIEW] │  │
   │  Citations: 12,500      [SAVE]  │  │
   │  Recent Papers: 8        [PDF]  │  │
   │                                  │  │
   │  Tags: ML • NLP • Reasoning     │  │
   └───────────────────────────────────┘──┘

**Progress Tracker**

Real-time updates during search:

.. code-block:: text

   Searching... [████████░░░░] 60%
   - Fetched 15/25 professors
   - Downloaded 47 papers
   - Analyzed 31 papers

**Filter Sidebar**

Filter professors by:

- Match score range
- Minimum citations
- University ranking
- Research area
- Accepting students status

**Comparison View**

Select multiple professors and compare side-by-side:

.. code-block:: text

   ┌─────────┬─────────┬─────────┐
   │ Metric  │ Prof A  │ Prof B  │
   ├─────────┼─────────┼─────────┤
   │ Score   │   87    │   82    │
   │ Citations│ 12.5k  │  8.2k  │
   │ Papers  │    8    │   12    │
   └─────────┴─────────┴─────────┘

Data Visualization
------------------

Built-in charts:

- **Score Radar**: Multi-dimensional comparison
- **Timeline**: Professor's publication history
- **Network Graph**: Collaboration network
- **Word Cloud**: Research themes

Example:

.. code-block:: python

   import streamlit as st
   import plotly.express as px

   fig = px.radar(
       df,
       r="score",
       theta="dimension",
       title="Fit Assessment"
   )
   st.plotly_chart(fig)

State Management
----------------

Session state stores:

- Search results
- Selected professors
- Filter settings
- User preferences

Example:

.. code-block:: python

   import streamlit as st

   # Initialize
   if "professors" not in st.session_state:
       st.session_state.professors = []

   # Update
   st.session_state.professors = results

   # Access
   for prof in st.session_state.professors:
       st.write(prof.name)

Customization
-------------

Theme customization in ``.streamlit/config.toml``:

.. code-block:: toml

   [theme]
   primaryColor = "#0066CC"
   backgroundColor = "#FFFFFF"
   secondaryBackgroundColor = "#F0F2F6"
   textColor = "#262730"

Page layout:

.. code-block:: python

   st.set_page_config(
       page_title="PhD Hunter",
       page_icon="🎓",
       layout="wide",
       initial_sidebar_state="expanded"
   )

Performance
-----------

Streamlit caching for speed:

.. code-block:: python

   @st.cache_data
   def search_professors(query):
       # Expensive operation
       return results

   @st.cache_resource
   def get_llm_client():
       # Reuse client
       return LLMClient()

Offline Mode
------------

Cache data for offline access:

.. code-block:: python

   import phd_hunter.utils.cache as cache

   # Save to local cache
   cache.save(results, "last_search.pkl")

   # Load from cache
   cached = cache.load("last_search.pkl")

Mobile Support
--------------

Streamlit is responsive. Access from phone:

1. Ensure server is accessible
2. Use your IP: ``http://192.168.1.x:8501``
3. Or deploy to cloud (see :doc:`deployment`)

Deployment
----------

Deploy to:

- **Streamlit Cloud**: Easiest (push to GitHub)
- **Vercel/Heroku**: With Docker
- **Self-hosted**: On your server

See :doc:`deployment` for details.

API Integration
---------------

Frontend calls the FastAPI backend:

.. code-block:: python

   import requests

   response = requests.post(
       "http://localhost:8000/api/search",
       json={"universities": ["MIT"], "area": "AI"}
   )
   results = response.json()

Security
--------

- API keys stored in session (never exposed to client)
- Rate limiting on API endpoints
- Input sanitization

Troubleshooting
---------------

**Page not updating**: Clear cache with ``st.cache_data.clear()``

**Slow performance**: Enable caching, reduce page size

**Connection refused**: Check backend is running on port 8000

Development
-----------

Frontend structure:

.. code-block:: text

   frontend/
   ├── app.py              # Main entry
   ├── pages/              # Additional pages
   │   ├── history.py
   │   ├── settings.py
   │   └── about.py
   ├── components/         # Reusable UI
   │   ├── professor_card.py
   │   └── search_bar.py
   └── styles/             # CSS customizations
       └── custom.css

Add new page:

.. code-block:: python

   # pages/my_page.py
   import streamlit as st

   st.title("My Page")
   st.write("Content here")

See Also
--------

- :doc:`architecture`
- :doc:`api`
- :doc:`deployment`

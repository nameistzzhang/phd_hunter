Reports
=======

The reporting module generates comprehensive assessment reports for each professor.

Report Formats
--------------

1. **HTML Report**: Interactive web page with charts and collapsible sections
2. **PDF Report**: Printable version for offline review
3. **JSON Report**: Machine-readable data for further processing
4. **Markdown Report**: Simple text format for quick review

Report Structure
----------------

Each report contains:

.. code-block:: text

   ┌─────────────────────────────────────────┐
   │    PhD Hunter - Professor Assessment    │
   ├─────────────────────────────────────────┤
   │  1. Executive Summary                   │
   │     - Overall recommendation            │
   │     - Match score (0-100)               │
   │     - Key highlights                    │
   │                                         │
   │  2. Professor Profile                   │
   │     - Name, affiliation, contact        │
   │     - Research interests                │
   │     - Google Scholar metrics            │
   │                                         │
   │  3. Research Analysis                   │
   │     - Recent publications (5 years)     │
   │     - Research themes                   │
   │     - Methodology patterns              │
   │     - Collaboration network             │
   │                                         │
   │  4. Fit Assessment                      │
   │     - Research alignment score          │
   │     - Methodology compatibility         │
   │     - Career stage match                │
   │     - Potential synergies               │
   │                                         │
   │  5. Application Strategy                │
   │     - Suggested contact approach        │
   │     - Recommended talking points        │
   │     - Timing advice                     │
   │                                         │
   │  6. Risk Factors                        │
   │     - Concerns to consider              │
   │     - Alternative suggestions           │
   │                                         │
   │  7. References                          │
   │     - Papers analyzed                   │
   │     - Sources consulted                 │
   └─────────────────────────────────────────┘

Generating Reports
------------------

Basic usage:

.. code-block:: python

   from phd_hunter.reports.generator import ReportGenerator
   from phd_hunter.agents.coordinator import CoordinatorAgent

   # Run search
   coordinator = CoordinatorAgent()
   results = coordinator.search(
       universities=["MIT", "Berkeley"],
       area="NLP"
   )

   # Generate report
   generator = ReportGenerator()
   report = generator.generate(
       professor_data=results[0],
       format="html",  # "html", "pdf", "json", "markdown"
       output_path="./reports/professor_123.html"
   )

Custom Templates
----------------

Create custom report templates:

1. Copy the default template from ``reports/templates/``
2. Modify the Jinja2 template
3. Point config to your template:

.. code-block:: yaml

   reports:
     template_dir: "./custom_templates"
     template: "my_template.html"

Template variables available:

.. code-block:: jinja

   {{ professor.name }}
   {{ professor.university }}
   {{ professor.email }}
   {{ professor.research_interests }}
   {{ professor.scholar_metrics }}
   {{ analysis.themes }}
   {{ analysis.fit_score }}
   {{ analysis.recommendation }}

Batch Reports
-------------

Generate reports for multiple professors:

.. code-block:: python

   from phd_hunter.reports.batch import BatchReportGenerator

   generator = BatchReportGenerator(output_dir="./reports")
   generator.generate_batch(
       professors=results,
       format="html",
       combine=True  # Create index.html with all professors
   )

Output creates:

.. code-block:: text

   reports/
   ├── index.html           # Overview page
   ├── professor_001.html   # Individual report 1
   ├── professor_002.html   # Individual report 2
   ├── professor_003.html   # Individual report 3
   └── summary.json         # Aggregated scores

Report Customization
--------------------

In ``config/settings.yaml``:

.. code-block:: yaml

   reports:
     # Output settings
     output_dir: "./reports"
     format: "html"              # html, pdf, markdown, json

     # Content options
     include:
       - executive_summary
       - professor_profile
       - research_analysis
       - fit_assessment
       - application_strategy
       - risk_factors

     # Scoring weights (customize match algorithm)
     scoring:
       research_alignment: 0.4
       recent_activity: 0.2
       collaboration_network: 0.15
       student_mentorship: 0.15
       funding_potential: 0.1

     # Template customization
     template:
       name: "default"
       theme: "light"             # light or dark
       primary_color: "#0066CC"

     # PDF options
     pdf:
       page_size: "A4"
       margin: "1in"
       header: "PhD Hunter Report"

Comparison Reports
------------------

Compare multiple professors side-by-side:

.. code-block:: python

   from phd_hunter.reports.comparison import ComparisonReport

   comparison = ComparisonReport(professors=results)
   comparison.generate(
       output_path="./reports/comparison.html",
       metrics=["fit_score", "h_index", "recent_papers"]
   )

Creates a comparison table with:

- Overall scores
- Metric breakdowns
- Radar chart visualization
- Pros/cons summary

Export Options
--------------

Reports can be exported to:

- **CSV**: Professor list with scores
- **Excel**: Full data with formatting
- **Notion**: Push to Notion database
- **Google Sheets**: Share with collaborators

Example:

.. code-block:: python

   generator.export_csv(
       results,
       path="./reports/rankings.csv"
   )

   generator.export_notion(
       results,
       database_id="..."
   )

Scheduling
----------

Set up periodic report generation:

.. code-block:: python

   from phd_hunter.reports.scheduler import ReportScheduler

   scheduler = ReportScheduler()
   scheduler.schedule_daily(
       query={"area": "AI", "universities": ["MIT", "Stanford"]},
       time="09:00",
       output="./daily_reports/"
   )

API Access
----------

Generate reports via API:

.. code-block:: bash

   POST /api/reports/generate
   {
     "professor_id": "123",
     "format": "pdf",
     "include_sections": ["summary", "analysis"]
   }

   Response: {"report_url": "/reports/123.pdf"}

See Also
--------

- :doc:`architecture`
- :doc:`agents`
- :doc:`frontend`
- :doc:`api`

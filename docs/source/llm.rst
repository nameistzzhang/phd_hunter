LLM Integration
===============

The LLM module provides a unified interface to multiple LLM providers (OpenAI, Anthropic) for research analysis.

Supported Providers
-------------------

- **OpenAI**: GPT-4o, GPT-4o-mini, GPT-4-turbo
- **Anthropic**: Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku

Quick Start
-----------

.. code-block:: python

   from phd_hunter.llm.client import LLMClient

   # Initialize with config
   client = LLMClient(
       provider="openai",
       api_key="sk-...",
       model="gpt-4o"
   )

   # Simple completion
   response = client.complete(
       system="You are a research analyst.",
       user="Summarize this paper: ..."
   )

   # Structured output (JSON)
   result = client.structured(
       system="Extract research topics.",
       user="Paper abstract: ...",
       schema={
           "topics": ["string"],
           "methods": ["string"]
       }
   )

LLMClient Class
---------------

**File**: ``llm/client.py``

Key methods:

.. code-block:: python

   class LLMClient:
       def complete(
           self,
           system: str,
           user: str,
           temperature: float = 0.3,
           max_tokens: int = 4096
       ) -> str:
           """Get text completion from LLM."""

       def structured(
           self,
           system: str,
           user: str,
           schema: dict | type[BaseModel]
       ) -> dict | BaseModel:
           """Get structured JSON output."""

       def embed(
           self,
           texts: list[str]
       ) -> list[list[float]]:
           """Get embeddings for texts."""

       def count_tokens(self, text: str) -> int:
           """Estimate token count."""

Prompt Templates
----------------

**File**: ``llm/prompts.py``

Pre-defined prompts for common tasks:

1. **Paper Summarization**

   .. code-block:: python

      from phd_hunter.llm.prompts import SUMMARIZE_PAPER

      summary = client.complete(
          system=SUMMARIZE_PAPER,
          user=paper_text
      )

2. **Research Theme Extraction**

   .. code-block:: python

      from phd_hunter.llm.prompts import EXTRACT_THEMES

      themes = client.structured(
          system=EXTRACT_THEMES,
          user=paper_abstracts,
          schema=ResearchThemesSchema
      )

3. **Professor Profiling**

   .. code-block:: python

      from phd_hunter.llm.prompts import PROFILE_PROFESSOR

      profile = client.structured(
          system=PROFILE_PROFESSOR,
          user=professor_data,
          schema=ProfessorProfileSchema
      )

4. **Fit Assessment**

   .. code-block:: python

      from phd_hunter.llm.prompts import ASSESS_FIT

      assessment = client.structured(
          system=ASSESS_FIT,
          user=fit_data,
          schema=FitAssessmentSchema
      )

Custom Prompts
--------------

Define your own prompts:

.. code-block:: python

   MY_PROMPT = """
   You are an expert in {field}.

   Task: {task_description}

   Output format:
   {output_format}
   """

   response = client.complete(
       system=MY_PROMPT.format(field="ML", ...),
       user=content
   )

Structured Output
-----------------

Use Pydantic models for type-safe structured output:

.. code-block:: python

   from pydantic import BaseModel
   from typing import List

   class PaperAnalysis(BaseModel):
       main_contribution: str
       methodology: str
       strengths: List[str]
       limitations: List[str]
       relevance_to_phd: float  # 0-1 score

   analysis = client.structured(
       system="Analyze this paper...",
       user=paper_text,
       schema=PaperAnalysis
   )

   print(analysis.main_contribution)

Token Management
----------------

Track token usage for cost estimation:

.. code-block:: python

   tokens = client.count_tokens(text)
   print(f"Estimated tokens: {tokens}")

Cost calculation:

.. code-block:: python

   from phd_hunter.llm.cost import estimate_cost

   cost = estimate_cost(
       provider="openai",
       model="gpt-4o",
       input_tokens=1000,
       output_tokens=500
   )
   print(f"Estimated cost: ${cost:.4f}")

Error Handling
--------------

Built-in retry and fallback:

.. code-block:: python

   try:
       response = client.complete(...)
   except LLMRateLimitError:
       # Wait and retry
       pass
   except LLMProviderError:
       # Fallback to another provider
       pass

Rate Limiting
-------------

The client handles rate limits automatically:

- Tracks request quotas per provider
- Implements exponential backoff
- Queues requests when limits reached

Configuration
-------------

In ``config/settings.yaml``:

.. code-block:: yaml

   llm:
     provider: "openai"              # "openai" or "anthropic"
     api_key: "sk-..."               # Or set OPENAI_API_KEY env var
     model: "gpt-4o"
     temperature: 0.3
     max_tokens: 4096

     # Rate limits (per minute)
     rate_limit:
       requests_per_minute: 60
       tokens_per_minute: 300000

     # Retry settings
     retry:
       max_attempts: 3
       initial_delay: 1.0
       max_delay: 60.0

     # Cost tracking
     cost_tracking: true

Environment Variables
---------------------

Alternative to config file:

.. code-block:: bash

   # OpenAI
   set OPENAI_API_KEY=sk-...

   # Anthropic
   set ANTHROPIC_API_KEY=sk-...

   # PhD Hunter
   set PHD_HUNTER_LLM_PROVIDER=openai
   set PHD_HUNTER_LLM_MODEL=gpt-4o

Batch Processing
----------------

For processing multiple professors:

.. code-block:: python

   from phd_hunter.llm.batch import BatchProcessor

   processor = BatchProcessor(client, max_concurrent=5)

   tasks = [
       {"system": PROMPT, "user": paper_text}
       for paper_text in papers
   ]

   results = processor.run(tasks)
   # Results in same order as tasks

Context Management
------------------

For long documents, automatic chunking:

.. code-block:: python

   from phd_hunter.llm.context import ContextManager

   manager = ContextManager(max_tokens=128000)

   chunks = manager.chunk(long_text)
   responses = [client.complete(..., user=chunk) for chunk in chunks]

   summary = manager.merge(responses)

See Also
--------

- :doc:`architecture`
- :doc:`agents`
- :doc:`crawlers`
- :doc:`api`

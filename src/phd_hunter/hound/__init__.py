"""Hound: LLM-powered PhD hunting agents.

Modules:
    scorer: Professor-applicant fit scoring via LLM reasoning.
    analyzer: Application strategy analysis and cold-email drafting (TBD).
    prompts: System prompts and prompt builders for LLM interactions.
"""

from .scorer import score_professor, score_all_professors, get_applicant_profile
from .prompts import SCORER_SYSTEM_PROMPT, build_scorer_user_prompt

__all__ = [
    "score_professor",
    "score_all_professors",
    "get_applicant_profile",
    "SCORER_SYSTEM_PROMPT",
    "build_scorer_user_prompt",
]
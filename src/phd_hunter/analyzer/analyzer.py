"""Analyzer core logic: professor analysis and cold email generation."""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any

from api_infra import ModelClient
from phd_hunter.database import Database
from phd_hunter.utils.pdf_extract import get_applicant_profile
from phd_hunter.analyzer.prompts import (
    ANALYZER_SYSTEM_PROMPT,
    build_analyzer_initial_prompt,
)


CONFIG_PATH = Path(__file__).parent.parent / "frontend" / "hound_config.json"


def load_hound_config() -> Dict[str, Any]:
    """Load hound configuration from JSON file."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Hound config not found at {CONFIG_PATH}.\n"
            "Please copy hound_config.example.json to hound_config.json and fill in your API key."
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config


def _create_client(config: Dict[str, Any], override_max_tokens: Optional[int] = None) -> ModelClient:
    """Create a ModelClient from config dict."""
    return ModelClient(
        provider=config.get("provider", "yunwu"),
        model=config.get("model", "deepseek-v3.2"),
        api_keys=[config["api_key"]],
        temperature=config.get("temperature", 0.6),
        max_tokens=override_max_tokens or config.get("max_tokens", 800),
        base_url=config.get("url"),
    )


async def _fetch_homepage_if_needed(
    professor_id: int,
    professor_data: Dict[str, Any],
    db_path: str,
) -> Dict[str, Any]:
    """Fetch homepage summary if missing, returning updated professor data."""
    homepage_fetch_status = professor_data.get("homepage_fetch_status")
    if homepage_fetch_status in (None, "pending", "failed") or not professor_data.get("homepage_summary"):
        homepage_url = professor_data.get("homepage") or professor_data.get("homepage_url")
        if homepage_url:
            from phd_hunter.crawlers.homepage_crawler import fetch_and_summarize_homepage
            print(f"[Analyzer] Fetching homepage for {professor_data['name']}...")
            success = await fetch_and_summarize_homepage(
                professor_id=professor_id,
                homepage_url=homepage_url,
                professor_name=professor_data["name"],
                db_path=db_path,
            )
            if success:
                # Reload from DB
                db = Database(db_path=db_path)
                updated = db.get_professor_hound_data(professor_id)
                db.close()
                if updated:
                    return updated
    return professor_data


async def analyze_professor_first_time(
    professor_id: int,
    db_path: str = "phd_hunter.db",
) -> Optional[str]:
    """First-time analysis: generate analysis + cold email draft and save messages.

    Args:
        professor_id: Professor database ID
        db_path: Path to SQLite database

    Returns:
        Assistant response text or None if failed.
    """
    config = load_hound_config()
    db = Database(db_path=db_path)

    # --- Load applicant profile ---
    applicant = get_applicant_profile(db)
    if not applicant:
        print("[Analyzer] No applicant profile found. Please fill in Profile page first.")
        db.close()
        return None

    # --- Load professor data ---
    professor = db.get_professor_hound_data(professor_id)
    if not professor:
        print(f"[Analyzer] Professor {professor_id} not found.")
        db.close()
        return None

    # --- Fetch homepage if needed ---
    professor = await _fetch_homepage_if_needed(professor_id, professor, db_path)

    # --- Build messages ---
    user_prompt = build_analyzer_initial_prompt(applicant, professor)
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": ANALYZER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt, "hidden": True},
    ]

    # --- Call LLM ---
    # Analyzer needs more tokens than scorer (analysis + email draft)
    client = _create_client(config, override_max_tokens=2500)
    try:
        response = await client.generate(messages=messages, track_cost=True)
        assistant_content = response.content

        # Append assistant response
        messages.append({"role": "assistant", "content": assistant_content})

        # Save to DB
        db.update_professor_messages(professor_id, messages)
        print(f"[Analyzer] First-time analysis saved for {professor['name']}")

        return assistant_content
    except Exception as e:
        print(f"[Analyzer] LLM call failed: {e}")
        return None
    finally:
        await client.close()
        db.close()


async def chat_with_professor(
    professor_id: int,
    user_message: str,
    db_path: str = "phd_hunter.db",
) -> Optional[str]:
    """Continue chat with a professor. Load existing messages, append user message,
    call LLM, save updated history.

    Args:
        professor_id: Professor database ID
        user_message: User's new message
        db_path: Path to SQLite database

    Returns:
        Assistant response text or None if failed.
    """
    config = load_hound_config()
    db = Database(db_path=db_path)

    # --- Load existing messages ---
    professor = db.get_professor_hound_data(professor_id)
    if not professor:
        print(f"[Analyzer] Professor {professor_id} not found.")
        db.close()
        return None

    messages = professor.get("messages", [])
    if not messages or not isinstance(messages, list):
        print(f"[Analyzer] No existing messages for professor {professor_id}. Run first-time analysis first.")
        db.close()
        return None

    # Ensure messages are dicts with role/content (strip non-standard fields for LLM)
    clean_messages = []
    for msg in messages:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            clean_messages.append({"role": msg["role"], "content": msg["content"]})
    messages = clean_messages

    # Append user message
    messages.append({"role": "user", "content": user_message})

    # --- Call LLM ---
    client = _create_client(config, override_max_tokens=2000)
    try:
        response = await client.generate(messages=messages, track_cost=True)
        assistant_content = response.content

        # Append assistant response
        messages.append({"role": "assistant", "content": assistant_content})

        # Save to DB
        db.update_professor_messages(professor_id, messages)
        print(f"[Analyzer] Chat response saved for {professor['name']}")

        return assistant_content
    except Exception as e:
        print(f"[Analyzer] LLM chat call failed: {e}")
        return None
    finally:
        await client.close()
        db.close()

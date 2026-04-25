"""Hound Scorer: LLM-based professor-applicant fit scoring.

Reads configuration from src/phd_hunter/frontend/hound_config.json
(which is gitignored — copy from hound_config.example.json).
Scores each professor 3 times and averages for stability.
"""

import json
import asyncio
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any

from phd_hunter.api_infra import ModelClient, ContextManager
from phd_hunter.database import Database
from phd_hunter.hound.prompts import (
    SCORER_SYSTEM_PROMPT,
    build_scorer_user_prompt,
)
from phd_hunter.utils.pdf_extract import get_applicant_profile


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent.parent / "frontend" / "hound_config.json"


def load_hound_config() -> Dict[str, Any]:
    """Load hound configuration from JSON file.

    Returns:
        Config dict with api_key, model, provider, temperature, max_tokens,
        scoring_iterations.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Hound config not found at {CONFIG_PATH}.\n"
            "Please copy hound_config.example.json to hound_config.json and fill in your API key."
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config


# ---------------------------------------------------------------------------
# Professor data helpers
# ---------------------------------------------------------------------------

def get_professor_data(db: Database, professor_id: int) -> Optional[Dict[str, Any]]:
    """Get professor data with papers for scoring."""
    return db.get_professor_hound_data(professor_id)


# ---------------------------------------------------------------------------
# Core: single LLM call -> parsed scores
# ---------------------------------------------------------------------------

async def _call_llm_for_scores(
    applicant: Dict[str, Any],
    professor: Dict[str, Any],
    client: ModelClient,
) -> Optional[Dict[str, Any]]:
    """Single LLM call to score a professor."""
    user_prompt = build_scorer_user_prompt(applicant, professor)

    context = ContextManager()
    context.set_system_prompt(SCORER_SYSTEM_PROMPT)
    context.add_user_message(user_prompt)

    response = await client.generate(
        messages=context.build(),
        track_cost=True,
    )
    content = response.content.strip()

    # Strip markdown code fences if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    scores = json.loads(content)
    return {
        "direction_match": int(scores.get("direction_match", 0)),
        "admission_difficulty": int(scores.get("admission_difficulty", 0)),
        "reasoning": scores.get("reasoning", ""),
    }


# ---------------------------------------------------------------------------
# Public API: score one professor (3 iterations, averaged)
# ---------------------------------------------------------------------------

async def score_professor(
    professor_id: int,
    db_path: str = "phd_hunter.db",
) -> Optional[Dict[str, Any]]:
    """Score a single professor using LLM, averaged over 3 iterations.

    Args:
        professor_id: Professor database ID
        db_path: Path to SQLite database

    Returns:
        Score dict or None if failed.
    """
    config = load_hound_config()
    db = Database(db_path=db_path)

    # --- load data ---------------------------------------------------------
    applicant = get_applicant_profile(db)
    if not applicant:
        print("[Scorer] No applicant profile found. Please fill in Profile page first.")
        db.close()
        return None

    professor = get_professor_data(db, professor_id)
    if not professor:
        print(f"[Scorer] Professor {professor_id} not found.")
        db.close()
        return None

    # --- fetch homepage if needed ------------------------------------------
    homepage_fetch_status = professor.get("homepage_fetch_status")
    if homepage_fetch_status in (None, "pending", "failed"):
        homepage_url = professor.get("homepage") or professor.get("homepage_url")
        if homepage_url:
            from phd_hunter.crawlers.homepage_crawler import fetch_and_summarize_homepage
            print(f"[Scorer] Fetching homepage for {professor['name']}...")
            success = await fetch_and_summarize_homepage(
                professor_id=professor_id,
                homepage_url=homepage_url,
                professor_name=professor["name"],
                db_path=db_path,
            )
            if success:
                # Reload professor data with new summary
                professor = get_professor_data(db, professor_id)

    # --- create client -----------------------------------------------------
    client = ModelClient(
        provider=config.get("provider", "yunwu"),
        model=config.get("model", "deepseek-v3.2"),
        api_keys=[config["api_key"]],
        temperature=config.get("temperature", 0.3),
        max_tokens=config.get("max_tokens", 800),
        base_url=config.get("url"),
    )

    # --- run 3 iterations --------------------------------------------------
    iterations = config.get("scoring_iterations", 3)
    scores_list: List[Dict[str, Any]] = []

    for i in range(iterations):
        try:
            result = await _call_llm_for_scores(applicant, professor, client)
            if result:
                # Clamp
                result["direction_match"] = max(1, min(5, result["direction_match"]))
                result["admission_difficulty"] = max(1, min(5, result["admission_difficulty"]))
                scores_list.append(result)
                print(
                    f"[Scorer]  Iteration {i + 1}/{iterations}: "
                    f"DM={result['direction_match']} AD={result['admission_difficulty']}"
                )
        except Exception as e:
            print(f"[Scorer]  Iteration {i + 1} failed: {e}")

        # Small delay between calls
        if i < iterations - 1:
            await asyncio.sleep(0.3)

    await client.close()

    # --- average -----------------------------------------------------------
    if not scores_list:
        print(f"[Scorer] All {iterations} iterations failed for {professor['name']}")
        db.close()
        return None

    avg_direction = round(sum(s["direction_match"] for s in scores_list) / len(scores_list))
    avg_difficulty = round(sum(s["admission_difficulty"] for s in scores_list) / len(scores_list))
    # Use reasoning from the first successful iteration
    reasoning = scores_list[0].get("reasoning", "")

    print(
        f"[Scorer]  Averaged ({len(scores_list)} runs): "
        f"DM={avg_direction} AD={avg_difficulty}"
    )

    # --- persist -----------------------------------------------------------
    db.update_professor_scores(
        professor_id=professor_id,
        direction_match=avg_direction,
        admission_difficulty=avg_difficulty,
        reasoning=reasoning,
    )
    db.close()

    return {
        "professor_id": professor_id,
        "professor_name": professor["name"],
        "direction_match": avg_direction,
        "admission_difficulty": avg_difficulty,
        "reasoning": reasoning,
        "raw_scores": scores_list,
    }


# ---------------------------------------------------------------------------
# Batch scoring
# ---------------------------------------------------------------------------

async def score_all_professors(
    db_path: str = "phd_hunter.db",
    limit: Optional[int] = None,
    unscored_only: bool = True,
) -> List[Dict[str, Any]]:
    """Score multiple professors in batch.

    Args:
        db_path: Path to SQLite database
        limit: Max number of professors to score
        unscored_only: Only score professors without existing scores

    Returns:
        List of score result dicts.
    """
    db = Database(db_path=db_path)

    applicant = get_applicant_profile(db)
    if not applicant:
        print("[Scorer] No applicant profile found. Please fill in Profile page first.")
        db.close()
        return []

    professors = db.list_professors_for_scoring(
        limit=limit,
        unscored_only=unscored_only,
    )
    db.close()

    if not professors:
        print("[Scorer] No professors to score.")
        return []

    print(f"[Scorer] Scoring {len(professors)} professors (3 iterations each)...")

    results = []
    for prof in professors:
        prof_id = prof["id"]
        name = prof["name"]
        print(f"\n[Scorer] --- {name} ({prof['university_name']}) ---")
        result = await score_professor(professor_id=prof_id, db_path=db_path)
        if result:
            results.append(result)
        await asyncio.sleep(0.5)

    print(f"\n[Scorer] Completed: {len(results)}/{len(professors)} professors scored.")
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    results = asyncio.run(score_all_professors(limit=3, unscored_only=True))
    for r in results:
        print(f"\n{r['professor_name']}:")
        print(f"  Direction Match: {r['direction_match']}/5")
        print(f"  Admission Difficulty: {r['admission_difficulty']}/5")
        raw = r.get("raw_scores", [])
        if raw:
            dm_vals = [s["direction_match"] for s in raw]
            ad_vals = [s["admission_difficulty"] for s in raw]
            print(f"  Raw scores: DM={dm_vals} AD={ad_vals}")
        print(f"  Reasoning: {r['reasoning'][:200]}...")

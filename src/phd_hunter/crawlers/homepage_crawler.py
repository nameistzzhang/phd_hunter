"""Homepage crawler - fetches professor homepage HTML and summarizes with LLM."""

import asyncio
import json
import traceback
from typing import Optional, Dict, Any
from pathlib import Path

import httpx

from .base import BaseCrawler
from phd_hunter.database import Database
from phd_hunter.utils.logger import get_logger

logger = get_logger(__name__)

# Raw HTML archive directory (project root / home_pages)
HOME_PAGES_DIR = Path(__file__).parent.parent.parent.parent / "home_pages"


def _save_raw_html(professor_id: int, html: str) -> Path:
    """Save raw HTML to file system archive.

    Returns:
        Path to the saved file.
    """
    HOME_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    file_path = HOME_PAGES_DIR / f"{professor_id}.html"
    file_path.write_text(html, encoding="utf-8")
    logger.info(f"[Homepage] Raw HTML saved: {file_path} ({len(html)} chars)")
    return file_path

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.0 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0"
)


def _create_http_client() -> httpx.AsyncClient:
    """Create a fresh httpx.AsyncClient for each request.

    Avoids event-loop binding issues when the function is called
    from different asyncio event loops (e.g. scorer daemon)."""
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=True,
        max_redirects=5,
    )


async def _fetch_homepage(url: str) -> Optional[str]:
    """Fetch raw HTML from a homepage URL.

    Returns:
        HTML string or None if failed.
    """
    client = _create_http_client()
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "").lower()
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            logger.warning(f"Non-HTML content-type for {url}: {content_type}")
            return None
        # Limit to ~2MB
        text = resp.text[:2_000_000]
        return text
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP {e.response.status_code} fetching {url}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def _extract_text_from_html(html: str, max_chars: int = 8000) -> str:
    """Quick and dirty text extraction from HTML (no heavy deps).

    Strips tags, scripts, styles. Returns plain text.
    """
    import re

    # Remove script/style tags and their content
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<noscript[^>]*>.*?</noscript>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Remove tags but keep a bit of structure
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</div>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</h[1-6]>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", "", html)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", html).strip()
    return text[:max_chars]


async def _llm_summarize_homepage(
    text: str,
    professor_name: str,
    config: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Use LLM to extract structured info from homepage text.

    Returns:
        Dict with keys: email, research_focus, recruiting_status, summary
        or None if failed.
    """
    from api_infra import ModelClient, ContextManager
    from phd_hunter.hound.prompts import HOMEPAGE_EXTRACTION_PROMPT

    prompt = HOMEPAGE_EXTRACTION_PROMPT.format(
        professor_name=professor_name,
        homepage_text=text,
    )

    client = ModelClient(
        provider=config.get("provider", "yunwu"),
        model=config.get("model", "deepseek-v3.2"),
        api_keys=[config["api_key"]],
        temperature=0.3,
        max_tokens=600,
    )

    context = ContextManager()
    context.set_system_prompt(
        "You are an expert academic information extractor. "
        "Extract key details from a professor's homepage. "
        "Respond ONLY with a valid JSON object."
    )
    context.add_user_message(prompt)

    try:
        response = await client.generate(
            messages=context.build(),
            track_cost=True,
        )
        content = response.content.strip()

        # Strip markdown code fences
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)
        await client.close()
        return {
            "email": data.get("email", ""),
            "research_focus": data.get("research_focus", ""),
            "recruiting_status": data.get("recruiting_status", "unknown"),
            "summary": data.get("summary", ""),
        }
    except Exception as e:
        logger.warning(f"LLM homepage extraction failed for {professor_name}: {e}")
        await client.close()
        return None


async def fetch_and_summarize_homepage(
    professor_id: int,
    homepage_url: str,
    professor_name: str,
    db_path: str = "phd_hunter.db",
) -> bool:
    """Fetch professor homepage, summarize with LLM, and update DB.

    Args:
        professor_id: Professor database ID
        homepage_url: Homepage URL (from csrankings)
        professor_name: Professor name for logging
        db_path: Path to SQLite database

    Returns:
        True if successful, False otherwise.
    """
    db = Database(db_path=db_path)

    # Skip invalid URLs
    if not homepage_url or not homepage_url.startswith(("http://", "https://")):
        db.update_professor_homepage(
            professor_id=professor_id,
            summary="",
            status="dead",
            error_msg="Invalid or missing homepage URL",
        )
        db.close()
        return False

    try:
        logger.info(f"[Homepage] Fetching: {professor_name} -> {homepage_url}")

        # 1. Fetch raw HTML
        html = await _fetch_homepage(homepage_url)
        if html is None:
            db.update_professor_homepage(
                professor_id=professor_id,
                summary="",
                status="failed",
                error_msg="Failed to fetch homepage",
            )
            db.close()
            return False

        # 1.5 Save raw HTML to file system archive
        _save_raw_html(professor_id, html)

        # 2. Extract text
        text = _extract_text_from_html(html)
        if not text or len(text) < 100:
            db.update_professor_homepage(
                professor_id=professor_id,
                summary="",
                status="dead",
                error_msg="Homepage content too short or empty",
            )
            db.close()
            return False

        # 3. Load config for LLM
        from phd_hunter.hound.scorer import load_hound_config
        config = load_hound_config()

        # 4. LLM summarize
        result = await _llm_summarize_homepage(text, professor_name, config)
        if not result:
            db.update_professor_homepage(
                professor_id=professor_id,
                summary="",
                status="failed",
                error_msg="LLM extraction failed",
            )
            db.close()
            return False

        # 5. Build summary string
        summary_parts = []
        if result["research_focus"]:
            summary_parts.append(f"Research Focus: {result['research_focus']}")
        if result["recruiting_status"] != "unknown":
            summary_parts.append(f"Recruiting: {result['recruiting_status']}")
        if result["summary"]:
            summary_parts.append(f"Summary: {result['summary']}")

        full_summary = "\n".join(summary_parts)

        # 6. Update DB
        db.update_professor_homepage(
            professor_id=professor_id,
            summary=full_summary,
            email=result["email"],
            status="success",
        )
        db.close()

        logger.info(
            f"[Homepage] Done: {professor_name} "
            f"(email={'yes' if result['email'] else 'no'}, "
            f"recruiting={result['recruiting_status']})"
        )
        return True

    except Exception as e:
        logger.error(f"[Homepage] Error for {professor_name}: {e}")
        traceback.print_exc()
        try:
            db.update_professor_homepage(
                professor_id=professor_id,
                summary="",
                status="failed",
                error_msg=str(e)[:500],
            )
        except Exception:
            pass
        db.close()
        return False


async def batch_fetch_homepages(
    db_path: str = "phd_hunter.db",
    limit: Optional[int] = None,
) -> None:
    """Batch fetch homepages for all professors that need it.

    Args:
        db_path: Path to SQLite database
        limit: Max number to process
    """
    db = Database(db_path=db_path)
    cursor = db.conn.cursor()

    query = """
        SELECT id, name, homepage
        FROM professors
        WHERE homepage_fetch_status IS NULL
           OR homepage_fetch_status = 'pending'
           OR homepage_fetch_status = 'failed'
    """
    params = ()
    if limit:
        query += " LIMIT ?"
        params = (limit,)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    db.close()

    if not rows:
        logger.info("[Homepage] No professors need homepage fetching.")
        return

    logger.info(f"[Homepage] Processing {len(rows)} professors...")

    for i, row in enumerate(rows, 1):
        await fetch_and_summarize_homepage(
            professor_id=row["id"],
            homepage_url=row["homepage"],
            professor_name=row["name"],
            db_path=db_path,
        )
        # Small delay between requests
        if i < len(rows):
            await asyncio.sleep(0.5)

    logger.info("[Homepage] Batch processing complete.")

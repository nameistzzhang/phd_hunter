"""PDF text extraction and applicant profile building utilities.

Moved from hound/scorer.py to avoid circular dependencies between
analyzer and scorer modules.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any

from PyPDF2 import PdfReader


def extract_pdf_text(pdf_path: str, max_chars: int = 3000) -> str:
    """Extract text from a PDF file."""
    if not pdf_path or not Path(pdf_path).exists():
        return ""
    try:
        reader = PdfReader(pdf_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        full_text = "\n".join(text_parts)
        return full_text[:max_chars]
    except Exception as e:
        print(f"[PDFExtract] Failed to extract PDF {pdf_path}: {e}")
        return ""


def _resolve_paper_abstracts(paper_links: List[Any]) -> List[str]:
    """Resolve arXiv paper abstracts from links (titles for now)."""
    abstracts = []
    for item in paper_links:
        if isinstance(item, dict):
            title = item.get("title", "")
            if title:
                abstracts.append(title)
        elif isinstance(item, str):
            abstracts.append(item)
    return abstracts


def get_applicant_profile(db) -> Optional[Dict[str, Any]]:
    """Build applicant profile dict from database.

    Args:
        db: Database instance with get_profile() method.

    Returns:
        Profile dict or None if no profile exists.
    """
    profile = db.get_profile()
    if not profile:
        return None

    result = {
        "cv_text": "",
        "ps_text": "",
        "paper_abstracts": [],
        "preferences": profile.get("preferences", ""),
    }

    cv_path = profile.get("cv_path")
    if cv_path:
        result["cv_text"] = extract_pdf_text(cv_path, max_chars=3000)

    ps_path = profile.get("ps_path")
    if ps_path:
        result["ps_text"] = extract_pdf_text(ps_path, max_chars=2000)

    paper_links = profile.get("paper_links", [])
    if paper_links and isinstance(paper_links, list):
        result["paper_abstracts"] = _resolve_paper_abstracts(paper_links)

    return result

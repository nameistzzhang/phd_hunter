"""Helper utilities."""

import re
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse
import asyncio
from functools import wraps


def normalize_name(name: str) -> str:
    """Normalize professor name for matching."""
    # Remove titles
    name = re.sub(r'^(Dr\.|Professor|Prof\.)\s+', '', name, flags=re.IGNORECASE)
    # Lowercase and strip
    return name.strip().lower()


def extract_email_from_text(text: str) -> Optional[str]:
    """Extract email address from text."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else None


def clean_html_text(text: str) -> str:
    """Clean HTML text content."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def ensure_dir(path: str) -> None:
    """Ensure directory exists."""
    from pathlib import Path
    Path(path).mkdir(parents=True, exist_ok=True)


async def retry_async(
    func,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Retry async function with exponential backoff."""
    for attempt in range(max_attempts):
        try:
            return await func()
        except exceptions as e:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(delay * (backoff ** attempt))


def retry_sync(
    func,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Retry sync function with exponential backoff."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if attempt == max_attempts - 1:
                    raise
                import time
                time.sleep(delay * (backoff ** attempt))
    return wrapper


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def safe_filename(name: str) -> str:
    """Convert string to safe filename."""
    # Remove/replace invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Limit length
    return name[:100]


def format_citation_count(count: int) -> str:
    """Format citation count for display."""
    if count >= 10000:
        return f"{count/1000:.1f}K"
    elif count >= 1000:
        return f"{count/1000:.1f}K"
    return str(count)


def merge_dicts(*dicts: Dict[Any, Any]) -> Dict[Any, Any]:
    """Merge multiple dictionaries, later ones override."""
    result = {}
    for d in dicts:
        result.update(d)
    return result

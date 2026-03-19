from __future__ import annotations

from typing import Iterable, List
from urllib.parse import urlparse


def _is_placeholder_baidu(url: str) -> bool:
    raw = (url or "").strip()
    if not raw:
        return True

    # Normalize scheme for parsing.
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    query = parsed.query or ""

    if host in {"baidu.com", "www.baidu.com"} and path in {"", "/"} and not query:
        return True
    return False


def sanitize_target_urls(urls: Iterable[str]) -> List[str]:
    cleaned: List[str] = []
    for value in urls or []:
        text = (value or "").strip()
        if not text:
            continue
        if _is_placeholder_baidu(text):
            continue
        cleaned.append(text)
    return cleaned

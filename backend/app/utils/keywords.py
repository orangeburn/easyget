import re
from typing import Iterable, List


_KEYWORD_SEPARATOR_RE = re.compile(r"[\r\n,，、;；]+")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_keyword(value: str) -> str:
    if value is None:
        return ""
    return _WHITESPACE_RE.sub(" ", str(value).strip())


def dedupe_keywords(values: Iterable[str]) -> List[str]:
    seen = set()
    keywords: List[str] = []
    for value in values:
        keyword = normalize_keyword(value)
        if not keyword:
            continue
        key = keyword.casefold()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(keyword)
    return keywords


def split_search_keywords(raw: str) -> List[str]:
    if not raw:
        return []
    parts = _KEYWORD_SEPARATOR_RE.split(str(raw).replace("\t", "\n"))
    return dedupe_keywords(parts)


def merge_keywords(*groups: Iterable[str]) -> List[str]:
    merged: List[str] = []
    for group in groups:
        merged.extend(group)
    return dedupe_keywords(merged)


def build_fallback_expanded_keywords(raw: str | Iterable[str]) -> List[str]:
    base_keywords = split_search_keywords(raw) if isinstance(raw, str) else dedupe_keywords(raw)
    expanded: List[str] = []
    for keyword in base_keywords:
        expanded.append(keyword)

        if any(token in keyword for token in ["招标", "采购", "公告", "项目"]):
            expanded.extend(
                [
                    f"{keyword}公告",
                    f"{keyword}项目",
                ]
            )
            continue

        suffixes = [
            "招标",
            "采购",
            "采购公告",
            "服务项目",
        ]
        for suffix in suffixes:
            if suffix in keyword:
                continue
            expanded.append(f"{keyword}{suffix}")

    return dedupe_keywords(expanded)

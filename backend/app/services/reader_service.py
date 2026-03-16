from html.parser import HTMLParser
from typing import Optional, List
from app.core.config import settings


class _SimpleMarkdownExtractor(HTMLParser):
    """
    Minimal, dependency-free HTML -> Markdown extractor.
    Focuses on readable text with basic structure for LLM parsing.
    """
    def __init__(self) -> None:
        super().__init__()
        self._out: List[str] = []
        self._skip_depth = 0
        self._current_href: Optional[str] = None
        self._link_text: List[str] = []
        self._last_was_newline = False

    def _append(self, text: str) -> None:
        if not text:
            return
        self._out.append(text)
        self._last_was_newline = text.endswith("\n")

    def _newline(self) -> None:
        if not self._last_was_newline:
            self._out.append("\n")
            self._last_was_newline = True

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        if tag in {"p", "div", "section", "article", "header", "footer", "br"}:
            self._newline()
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._newline()
            level = int(tag[1])
            self._append("#" * level + " ")
        if tag == "li":
            self._newline()
            self._append("- ")
        if tag == "a":
            href = None
            for k, v in attrs:
                if k.lower() == "href":
                    href = v
                    break
            self._current_href = href
            self._link_text = []

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "a":
            if self._link_text:
                text = "".join(self._link_text).strip()
                if text:
                    if self._current_href:
                        self._append(f"{text} ({self._current_href})")
                    else:
                        self._append(text)
            self._current_href = None
            self._link_text = []
        if tag in {"p", "div", "section", "article"}:
            self._newline()

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._current_href is not None:
            self._link_text.append(text)
        else:
            self._append(text + " ")

    def get_markdown(self) -> str:
        raw = "".join(self._out)
        # Normalize whitespace and newlines
        lines = [line.strip() for line in raw.splitlines()]
        cleaned = "\n".join([line for line in lines if line])
        return cleaned.strip()


class ReaderService:
    """
    Reader interface for converting raw HTML into Markdown-friendly text.
    Provider options are pluggable; default to builtin simple extractor.
    """
    def __init__(self):
        self.provider = settings.READER_PROVIDER

    def to_markdown(self, html: str, source_url: Optional[str] = None) -> str:
        if not html:
            return ""

        if self.provider == "builtin":
            parser = _SimpleMarkdownExtractor()
            parser.feed(html)
            return parser.get_markdown()

        # Placeholder for future providers (Jina/Firecrawl)
        # Fall back to builtin to keep behavior stable.
        parser = _SimpleMarkdownExtractor()
        parser.feed(html)
        return parser.get_markdown()

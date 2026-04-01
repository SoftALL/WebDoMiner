from __future__ import annotations

import html
import re


_WHITESPACE_RE = re.compile(r"\s+")
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_REPEAT_BLANK_LINES_RE = re.compile(r"\n{3,}")


def clean_extracted_text(text: str) -> str:
    """
    Clean extracted article text into a stable, readable form.

    This is intentionally conservative:
    - decode HTML entities
    - remove zero-width/control characters
    - normalize line spacing
    - collapse excessive whitespace inside lines
    """
    if not text:
        return ""

    text = html.unescape(text)
    text = _ZERO_WIDTH_RE.sub("", text)
    text = _CONTROL_RE.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    cleaned_lines: list[str] = []
    for raw_line in text.split("\n"):
        line = _WHITESPACE_RE.sub(" ", raw_line).strip()
        if line:
            cleaned_lines.append(line)
        else:
            cleaned_lines.append("")

    text = "\n".join(cleaned_lines)
    text = _REPEAT_BLANK_LINES_RE.sub("\n\n", text).strip()
    return text


def clean_title(title: str) -> str:
    """
    Normalize extracted page titles.
    """
    if not title:
        return ""
    title = html.unescape(title)
    title = _ZERO_WIDTH_RE.sub("", title)
    title = _CONTROL_RE.sub(" ", title)
    title = _WHITESPACE_RE.sub(" ", title).strip()
    return title


def count_words(text: str) -> int:
    """
    Count simple whitespace-separated words in cleaned text.
    """
    if not text:
        return 0
    return len(text.split())
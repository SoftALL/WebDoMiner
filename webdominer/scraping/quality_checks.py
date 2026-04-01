from __future__ import annotations

from dataclasses import dataclass

from webdominer.settings import Settings


_LOW_VALUE_PHRASES = (
    "enable javascript",
    "please enable javascript",
    "javascript is disabled",
    "access denied",
    "temporarily unavailable",
    "forbidden",
    "rate limit",
    "too many requests",
    "captcha",
    "robot check",
    "human verification",
    "sign in",
    "log in",
    "cookie policy",
    "privacy policy",
    "subscribe to continue",
)


@dataclass(slots=True)
class QualityCheckResult:
    """
    Result of evaluating whether scraped text is worth keeping.
    """

    is_acceptable: bool
    reason: str


def looks_like_low_value_page(text: str) -> bool:
    """
    Detect obvious junk, blockers, or non-content pages.
    """
    lowered = text.lower()
    return any(phrase in lowered for phrase in _LOW_VALUE_PHRASES)


def should_try_playwright_fallback(
    extracted_text: str,
    html_text: str,
    settings: Settings,
) -> bool:
    """
    Decide whether Playwright fallback is worth attempting.

    Use fallback only when the first-pass extraction looks weak and there are
    signs that the page may be JavaScript-rendered.
    """
    extracted_word_count = len(extracted_text.split()) if extracted_text else 0
    html_lower = html_text.lower() if html_text else ""

    if extracted_word_count >= settings.min_word_count:
        return False

    js_signals = (
        "__next",
        "__nuxt",
        "window.__",
        "id=\"root\"",
        "id='root'",
        "id=\"app\"",
        "id='app'",
        "javascript",
        "react",
        "hydration",
        "webpack",
    )

    return any(signal in html_lower for signal in js_signals)


def assess_text_quality(text: str, settings: Settings) -> QualityCheckResult:
    """
    Final content-quality check after cleaning.
    """
    if not text.strip():
        return QualityCheckResult(False, "empty_extracted_text")

    if looks_like_low_value_page(text):
        return QualityCheckResult(False, "low_value_or_blocked_page")

    word_count = len(text.split())
    if word_count < settings.min_word_count:
        return QualityCheckResult(False, f"below_min_word_count:{word_count}")

    return QualityCheckResult(True, "ok")
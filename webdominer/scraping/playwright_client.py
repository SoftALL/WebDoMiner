from __future__ import annotations

from dataclasses import dataclass

import trafilatura
from playwright.sync_api import sync_playwright

from webdominer.settings import Settings


@dataclass(slots=True)
class PlaywrightExtractionResult:
    """
    Result of Playwright rendering + Trafilatura extraction.
    """

    url: str
    final_url: str
    html: str
    extracted_text: str
    title: str


class PlaywrightClient:
    """
    Render JavaScript-heavy pages with headless Chromium, then extract content.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def render_and_extract(self, url: str) -> PlaywrightExtractionResult:
        """
        Render a page, capture HTML, then run Trafilatura on the rendered DOM.
        """
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(user_agent=self.settings.user_agent)

            try:
                page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=self.settings.playwright_timeout_ms,
                )
            except Exception:
                # Fall back to DOMContentLoaded if networkidle is too strict.
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.playwright_timeout_ms,
                )

            html_text = page.content()
            final_url = page.url
            title = page.title() or ""

            extracted_text = trafilatura.extract(
                html_text,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
            ) or ""

            browser.close()

        return PlaywrightExtractionResult(
            url=url,
            final_url=final_url,
            html=html_text,
            extracted_text=extracted_text,
            title=title,
        )
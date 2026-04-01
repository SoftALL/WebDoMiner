from __future__ import annotations

import time
from typing import Iterable

from webdominer.models import DiscoveredUrl, FailedPage, RejectedPage, ScrapedPage
from webdominer.scraping.cleaning import clean_extracted_text, clean_title, count_words
from webdominer.scraping.playwright_client import PlaywrightClient
from webdominer.scraping.quality_checks import (
    assess_text_quality,
    should_try_playwright_fallback,
)
from webdominer.scraping.trafilatura_client import TrafilaturaClient
from webdominer.settings import Settings


class ScraperService:
    """
    Scrape discovered URLs with a Trafilatura-first strategy and a strict
    Playwright fallback policy.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.trafilatura_client = TrafilaturaClient(settings)
        self.playwright_client = PlaywrightClient(settings)

    def scrape_urls(
        self,
        discovered_urls: Iterable[DiscoveredUrl],
    ) -> tuple[list[ScrapedPage], list[RejectedPage], list[FailedPage]]:
        """
        Scrape a batch of discovered URLs.

        Returns:
        - scraped_pages: pages with acceptable cleaned text
        - rejected_pages: pages that were fetched but rejected for quality reasons
        - failed_pages: pages that failed due to request/render errors
        """
        scraped_pages: list[ScrapedPage] = []
        rejected_pages: list[RejectedPage] = []
        failed_pages: list[FailedPage] = []

        for item in discovered_urls:
            try:
                scraped_page = self._scrape_one(item)
            except Exception as exc:
                failed_pages.append(
                    FailedPage(
                        url=item.url,
                        error=f"{type(exc).__name__}: {exc}",
                        matched_keyword=item.matched_keyword,
                        query=item.query,
                        title=item.title,
                    )
                )
                time.sleep(self.settings.request_delay_seconds)
                continue

            if isinstance(scraped_page, ScrapedPage):
                scraped_pages.append(scraped_page)
            else:
                rejected_pages.append(scraped_page)

            time.sleep(self.settings.request_delay_seconds)

        return scraped_pages, rejected_pages, failed_pages

    def _scrape_one(self, item: DiscoveredUrl) -> ScrapedPage | RejectedPage:
        """
        Scrape one discovered URL using Trafilatura first, then optionally
        Playwright if justified.
        """
        first_pass = self.trafilatura_client.fetch_and_extract(item.url)

        cleaned_text = clean_extracted_text(first_pass.extracted_text)
        cleaned_title = clean_title(first_pass.title or item.title)

        quality = assess_text_quality(cleaned_text, self.settings)
        extraction_method = "trafilatura"

        if (
            not quality.is_acceptable
            and self.settings.enable_playwright_fallback
            and should_try_playwright_fallback(
                extracted_text=cleaned_text,
                html_text=first_pass.html,
                settings=self.settings,
            )
        ):
            second_pass = self.playwright_client.render_and_extract(first_pass.final_url)

            fallback_text = clean_extracted_text(second_pass.extracted_text)
            fallback_title = clean_title(second_pass.title or cleaned_title)

            fallback_quality = assess_text_quality(fallback_text, self.settings)

            if fallback_quality.is_acceptable:
                return ScrapedPage(
                    url=second_pass.final_url,
                    matched_keyword=item.matched_keyword,
                    query=item.query,
                    title=fallback_title,
                    text=fallback_text,
                    word_count=count_words(fallback_text),
                    extraction_method="playwright+trafilatura",
                )

            return RejectedPage(
                url=second_pass.final_url,
                reason=fallback_quality.reason,
                matched_keyword=item.matched_keyword,
                query=item.query,
                title=fallback_title,
                snippet=item.snippet,
                extraction_method="playwright+trafilatura",
            )

        if quality.is_acceptable:
            return ScrapedPage(
                url=first_pass.final_url,
                matched_keyword=item.matched_keyword,
                query=item.query,
                title=cleaned_title,
                text=cleaned_text,
                word_count=count_words(cleaned_text),
                extraction_method=extraction_method,
            )

        return RejectedPage(
            url=first_pass.final_url,
            reason=quality.reason,
            matched_keyword=item.matched_keyword,
            query=item.query,
            title=cleaned_title,
            snippet=item.snippet,
            extraction_method=extraction_method,
        )
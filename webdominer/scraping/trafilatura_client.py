from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests
import trafilatura

from webdominer.settings import Settings


@dataclass(slots=True)
class TrafilaturaExtractionResult:
    """
    Result of HTTP fetch + Trafilatura extraction.
    """

    url: str
    final_url: str
    status_code: int
    content_type: str
    html: str
    extracted_text: str
    title: str


class TrafilaturaClient:
    """
    Download pages over HTTP and extract main text using Trafilatura.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.user_agent})

    def fetch_and_extract(self, url: str) -> TrafilaturaExtractionResult:
        """
        Fetch a page and run Trafilatura extraction.
        """
        response = self.session.get(
            url,
            timeout=self.settings.request_timeout_seconds,
            allow_redirects=True,
        )
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        html_text = response.text or ""

        extracted_text = trafilatura.extract(
            html_text,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=True,
        ) or ""

        metadata = trafilatura.extract_metadata(html_text)
        title = metadata.title if metadata and metadata.title else ""

        return TrafilaturaExtractionResult(
            url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=content_type,
            html=html_text,
            extracted_text=extracted_text,
            title=title,
        )
"""Generic RSS feed scraper — works with any job board RSS feed."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import feedparser
import httpx

from jobhunt.models import RawJob
from jobhunt.scrapers.base import BaseScraper

if TYPE_CHECKING:
    from jobhunt.models import SearchCriteria


class RSSScraper(BaseScraper):
    name = "rss"

    def __init__(self, feed_urls: list[str]):
        self._feed_urls = feed_urls

    async def search(self, criteria: SearchCriteria) -> list[RawJob]:
        jobs: list[RawJob] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for url in self._feed_urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.text)

                    for entry in feed.entries:
                        title = entry.get("title", "")
                        if not self._matches_criteria(title, criteria):
                            continue

                        company = entry.get("author", "")
                        if not company and " at " in title:
                            parts = title.split(" at ", 1)
                            title = parts[0].strip()
                            company = parts[1].strip()
                        if not company and " - " in title:
                            parts = title.split(" - ", 1)
                            title = parts[0].strip()
                            company = parts[1].strip()

                        jobs.append(RawJob(
                            title=title,
                            company=company,
                            jd_url=entry.get("link", ""),
                            jd_text=entry.get("summary", "")[:3000],
                            source=f"rss:{url[:50]}",
                            date_found=date.today(),
                        ))
                except Exception:
                    continue
        return jobs

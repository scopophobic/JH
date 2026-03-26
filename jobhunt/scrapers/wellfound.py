"""Wellfound (AngelList) scraper — RSS feed based."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import feedparser
import httpx

from jobhunt.models import RawJob
from jobhunt.scrapers.base import BaseScraper

if TYPE_CHECKING:
    from jobhunt.models import SearchCriteria

BASE_RSS = "https://wellfound.com/jobs.rss"


class WellfoundScraper(BaseScraper):
    name = "wellfound"

    def _build_rss_urls(self, criteria: SearchCriteria) -> list[str]:
        urls = []
        for role in criteria.roles[:3]:
            role_param = role.replace(" ", "+")
            urls.append(f"{BASE_RSS}?role[]={role_param}")
        return urls

    async def search(self, criteria: SearchCriteria) -> list[RawJob]:
        jobs: list[RawJob] = []
        urls = self._build_rss_urls(criteria)

        async with httpx.AsyncClient(timeout=30) as client:
            for url in urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.text)

                    for entry in feed.entries:
                        title = entry.get("title", "")
                        if not self._matches_criteria(title, criteria):
                            continue

                        company = ""
                        if " at " in title:
                            parts = title.split(" at ", 1)
                            title = parts[0].strip()
                            company = parts[1].strip()

                        jobs.append(RawJob(
                            title=title,
                            company=company,
                            jd_url=entry.get("link", ""),
                            jd_text=entry.get("summary", "")[:3000],
                            source=self.name,
                            date_found=date.today(),
                        ))
                except Exception:
                    continue
        return jobs

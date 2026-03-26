"""LinkedIn Jobs scraper — uses SerpAPI's google_jobs engine with LinkedIn filter."""

from __future__ import annotations

import os
from datetime import date
from typing import TYPE_CHECKING

import httpx

from jobhunt.models import RawJob
from jobhunt.scrapers.base import BaseScraper

if TYPE_CHECKING:
    from jobhunt.models import SearchCriteria

SERPAPI_URL = "https://serpapi.com/search.json"


class LinkedInScraper(BaseScraper):
    name = "linkedin"

    async def search(self, criteria: SearchCriteria) -> list[RawJob]:
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            return []

        jobs: list[RawJob] = []

        async with httpx.AsyncClient(timeout=30) as client:
            for role in criteria.roles[:3]:
                for location in criteria.locations[:2]:
                    try:
                        query = f"{role} site:linkedin.com/jobs"
                        resp = await client.get(SERPAPI_URL, params={
                            "engine": "google",
                            "q": query,
                            "location": location,
                            "api_key": api_key,
                            "num": 20,
                            "tbs": "qdr:w",  # past week
                        })
                        resp.raise_for_status()
                        data = resp.json()

                        for result in data.get("organic_results", []):
                            title_raw = result.get("title", "")
                            link = result.get("link", "")
                            snippet = result.get("snippet", "")

                            if "linkedin.com/jobs" not in link:
                                continue

                            title = title_raw.split(" - ")[0].strip() if " - " in title_raw else title_raw
                            company = ""
                            if " - " in title_raw:
                                parts = title_raw.split(" - ")
                                if len(parts) >= 2:
                                    company = parts[1].strip()

                            if not self._matches_criteria(title, criteria):
                                continue

                            jobs.append(RawJob(
                                title=title,
                                company=company,
                                jd_url=link,
                                jd_text=snippet[:3000],
                                source=self.name,
                                date_found=date.today(),
                            ))
                    except Exception:
                        continue
        return jobs

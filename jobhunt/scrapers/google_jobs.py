"""Google Jobs scraper — uses SerpAPI's google_jobs engine."""

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


class GoogleJobsScraper(BaseScraper):
    name = "google_jobs"

    async def search(self, criteria: SearchCriteria) -> list[RawJob]:
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            return []

        jobs: list[RawJob] = []
        queries = self._build_queries(criteria)

        async with httpx.AsyncClient(timeout=30) as client:
            for query in queries:
                for location in criteria.locations[:3]:
                    try:
                        resp = await client.get(SERPAPI_URL, params={
                            "engine": "google_jobs",
                            "q": query,
                            "location": location,
                            "api_key": api_key,
                            "chips": "date_posted:week",
                        })
                        resp.raise_for_status()
                        data = resp.json()

                        for result in data.get("jobs_results", []):
                            title = result.get("title", "")
                            if not self._matches_criteria(title, criteria):
                                continue

                            jobs.append(RawJob(
                                title=title,
                                company=result.get("company_name", ""),
                                jd_url=result.get("share_link", result.get("related_links", [{}])[0].get("link", "")),
                                jd_text=result.get("description", "")[:3000],
                                source=self.name,
                                date_found=date.today(),
                            ))
                    except Exception:
                        continue
        return jobs

    def _build_queries(self, criteria: SearchCriteria) -> list[str]:
        queries = []
        for role in criteria.roles[:3]:
            q = role
            if criteria.keywords:
                q += " " + " ".join(criteria.keywords[:2])
            queries.append(q)
        return queries

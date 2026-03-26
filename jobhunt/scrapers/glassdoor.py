"""Glassdoor scraper — uses SerpAPI Google search with Glassdoor site filter."""

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


class GlassdoorScraper(BaseScraper):
    name = "glassdoor"

    async def search(self, criteria: SearchCriteria) -> list[RawJob]:
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            return []

        jobs: list[RawJob] = []

        async with httpx.AsyncClient(timeout=30) as client:
            for role in criteria.roles[:2]:
                for location in criteria.locations[:2]:
                    try:
                        query = f"{role} site:glassdoor.com/job"
                        if criteria.keywords:
                            query += " " + " ".join(criteria.keywords[:2])

                        resp = await client.get(SERPAPI_URL, params={
                            "engine": "google",
                            "q": query,
                            "location": location,
                            "api_key": api_key,
                            "num": 15,
                            "tbs": "qdr:w",
                        })
                        resp.raise_for_status()
                        data = resp.json()

                        for result in data.get("organic_results", []):
                            title_raw = result.get("title", "")
                            link = result.get("link", "")
                            snippet = result.get("snippet", "")

                            if "glassdoor.com" not in link:
                                continue

                            title = title_raw.split(" - ")[0].strip()
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

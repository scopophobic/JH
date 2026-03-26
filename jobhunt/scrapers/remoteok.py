"""RemoteOK scraper — free JSON API, no auth required."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import httpx

from jobhunt.models import RawJob
from jobhunt.scrapers.base import BaseScraper

if TYPE_CHECKING:
    from jobhunt.models import SearchCriteria

REMOTEOK_API = "https://remoteok.com/api"


class RemoteOKScraper(BaseScraper):
    name = "remoteok"

    async def search(self, criteria: SearchCriteria) -> list[RawJob]:
        jobs: list[RawJob] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    REMOTEOK_API,
                    headers={"User-Agent": "JobHunt/1.0"},
                )
                resp.raise_for_status()
                data = resp.json()

            # First item is metadata, skip it
            listings = data[1:] if len(data) > 1 else []
            keywords_lower = {k.lower() for k in criteria.keywords}
            roles_lower = {r.lower() for r in criteria.roles}

            for item in listings:
                title = item.get("position", "")
                company = item.get("company", "")
                description = item.get("description", "")
                tags = [t.lower() for t in item.get("tags", [])]
                url = item.get("url", "")

                if not self._matches_criteria(title, criteria):
                    continue

                title_lower = title.lower()
                tag_match = any(k in tags for k in keywords_lower)
                role_match = any(r in title_lower for r in roles_lower)

                if tag_match or role_match:
                    jobs.append(RawJob(
                        title=title,
                        company=company,
                        jd_url=f"https://remoteok.com{url}" if url.startswith("/") else url,
                        jd_text=description[:3000],
                        source=self.name,
                        date_found=date.today(),
                    ))
        except Exception:
            pass
        return jobs

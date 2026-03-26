"""YCombinator Jobs scraper — scrapes the Work at a Startup page."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import httpx
from bs4 import BeautifulSoup

from jobhunt.models import RawJob
from jobhunt.scrapers.base import BaseScraper

if TYPE_CHECKING:
    from jobhunt.models import SearchCriteria

YC_JOBS_URL = "https://www.ycombinator.com/jobs"
YC_WORK_URL = "https://www.workatastartup.com/jobs"


class YCombinatorScraper(BaseScraper):
    name = "ycombinator"

    async def search(self, criteria: SearchCriteria) -> list[RawJob]:
        jobs: list[RawJob] = []
        keywords_lower = {k.lower() for k in criteria.keywords}
        roles_lower = {r.lower() for r in criteria.roles}

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(
                    YC_JOBS_URL,
                    headers={"User-Agent": "JobHunt/1.0"},
                )
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            for listing in soup.select("[class*='job'], [class*='listing'], a[href*='/companies/']"):
                title_el = listing.select_one(
                    "[class*='title'], [class*='role'], h3, h4"
                )
                company_el = listing.select_one(
                    "[class*='company'], [class*='name'], h2"
                )

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""

                if not title:
                    continue
                if not self._matches_criteria(title, criteria):
                    continue

                title_lower = title.lower()
                text_lower = listing.get_text().lower()
                role_match = any(r in title_lower for r in roles_lower)
                keyword_match = any(k in text_lower for k in keywords_lower)

                if role_match or keyword_match:
                    link = listing.get("href", "")
                    if link and not link.startswith("http"):
                        link = f"https://www.ycombinator.com{link}"

                    desc_el = listing.select_one(
                        "[class*='description'], [class*='desc'], p"
                    )
                    desc = desc_el.get_text(strip=True)[:3000] if desc_el else ""

                    jobs.append(RawJob(
                        title=title,
                        company=company,
                        jd_url=link,
                        jd_text=desc,
                        source=self.name,
                        date_found=date.today(),
                    ))
        except Exception:
            pass
        return jobs

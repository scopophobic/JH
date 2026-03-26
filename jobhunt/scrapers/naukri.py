"""Naukri.com scraper — direct HTTP scraping."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import httpx
from bs4 import BeautifulSoup

from jobhunt.models import RawJob
from jobhunt.scrapers.base import BaseScraper

if TYPE_CHECKING:
    from jobhunt.models import SearchCriteria

NAUKRI_SEARCH = "https://www.naukri.com/jobapi/v3/search"


class NaukriScraper(BaseScraper):
    name = "naukri"

    async def search(self, criteria: SearchCriteria) -> list[RawJob]:
        jobs: list[RawJob] = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "appid": "109",
            "systemid": "Starter",
        }

        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            for role in criteria.roles[:3]:
                try:
                    keyword = role.replace(" ", "-").lower()
                    locations = ",".join(criteria.locations[:3])

                    resp = await client.get(NAUKRI_SEARCH, params={
                        "noOfResults": 20,
                        "urlType": "search_by_keyword",
                        "searchType": "adv",
                        "keyword": role,
                        "location": locations,
                        "experience": criteria.experience_years[0] if criteria.experience_years else 0,
                        "sort": "r",  # relevance
                        "pageNo": 1,
                    })

                    if resp.status_code != 200:
                        # Fallback: try scraping HTML search results
                        jobs.extend(await self._scrape_html(client, role, criteria))
                        continue

                    data = resp.json()
                    for item in data.get("jobDetails", []):
                        title = item.get("title", "")
                        if not self._matches_criteria(title, criteria):
                            continue

                        company = item.get("companyName", "")
                        jd_url = item.get("jdURL", "")
                        jd_text = item.get("jobDescription", "")

                        jobs.append(RawJob(
                            title=title,
                            company=company,
                            jd_url=jd_url,
                            jd_text=jd_text[:3000],
                            source=self.name,
                            date_found=date.today(),
                        ))
                except Exception:
                    continue
        return jobs

    async def _scrape_html(
        self, client: httpx.AsyncClient, role: str, criteria: SearchCriteria
    ) -> list[RawJob]:
        """Fallback HTML scraping if the API doesn't respond."""
        jobs: list[RawJob] = []
        try:
            slug = role.lower().replace(" ", "-")
            url = f"https://www.naukri.com/{slug}-jobs"
            resp = await client.get(url)
            if resp.status_code != 200:
                return jobs

            soup = BeautifulSoup(resp.text, "html.parser")
            for card in soup.select("article.jobTuple, div.srp-jobtuple-wrapper, div.cust-job-tuple"):
                title_el = card.select_one("a.title, a[class*='title']")
                company_el = card.select_one("a.subTitle, a[class*='comp-name']")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""

                if not title or not self._matches_criteria(title, criteria):
                    continue

                link = title_el.get("href", "") if title_el else ""

                jobs.append(RawJob(
                    title=title,
                    company=company,
                    jd_url=link,
                    jd_text="",
                    source=self.name,
                    date_found=date.today(),
                ))
        except Exception:
            pass
        return jobs

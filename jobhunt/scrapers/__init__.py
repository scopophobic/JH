"""Scraper registry — builds the list of active scrapers from config."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jobhunt.scrapers.base import BaseScraper

if TYPE_CHECKING:
    from jobhunt.config import AppConfig


def get_active_scrapers(cfg: AppConfig) -> list[BaseScraper]:
    """Return instantiated scrapers for all enabled sources."""
    sources = cfg.system.sources
    scrapers: list[BaseScraper] = []

    if sources.remoteok:
        from jobhunt.scrapers.remoteok import RemoteOKScraper
        scrapers.append(RemoteOKScraper())

    if sources.wellfound:
        from jobhunt.scrapers.wellfound import WellfoundScraper
        scrapers.append(WellfoundScraper())

    if sources.ycombinator:
        from jobhunt.scrapers.ycombinator import YCombinatorScraper
        scrapers.append(YCombinatorScraper())

    if sources.google_jobs:
        from jobhunt.scrapers.google_jobs import GoogleJobsScraper
        scrapers.append(GoogleJobsScraper())

    if sources.linkedin:
        from jobhunt.scrapers.linkedin import LinkedInScraper
        scrapers.append(LinkedInScraper())

    if sources.indeed:
        from jobhunt.scrapers.indeed import IndeedScraper
        scrapers.append(IndeedScraper())

    if sources.glassdoor:
        from jobhunt.scrapers.glassdoor import GlassdoorScraper
        scrapers.append(GlassdoorScraper())

    if sources.naukri:
        from jobhunt.scrapers.naukri import NaukriScraper
        scrapers.append(NaukriScraper())

    if sources.rss_feeds:
        from jobhunt.scrapers.rss import RSSScraper
        scrapers.append(RSSScraper(sources.rss_feeds))

    return scrapers

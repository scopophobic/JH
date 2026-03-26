"""Abstract base scraper — all job sources implement this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from jobhunt.models import RawJob

if TYPE_CHECKING:
    from jobhunt.models import SearchCriteria


class BaseScraper(ABC):
    """All scrapers must implement the search method."""

    name: str = "base"

    @abstractmethod
    async def search(self, criteria: SearchCriteria) -> list[RawJob]:
        """Search for jobs matching the criteria. Returns a list of RawJob."""
        ...

    def _matches_criteria(self, title: str, criteria: SearchCriteria) -> bool:
        """Check if a job title roughly matches the search criteria."""
        title_lower = title.lower()
        for exclude in criteria.exclude_keywords:
            if exclude.lower() in title_lower:
                return False
        return True

    def _build_query(self, criteria: SearchCriteria) -> str:
        """Build a search query string from criteria."""
        parts = criteria.roles[:2]
        if criteria.keywords:
            parts.extend(criteria.keywords[:3])
        return " ".join(parts)

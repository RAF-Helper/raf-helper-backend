"""Tavily web search service."""

import logging
from typing import Any, Optional

from tavily import TavilyClient

from app.config import settings

logger = logging.getLogger(__name__)


class TavilyService:
    """Web search service using Tavily API."""

    def __init__(self):
        """Initialize Tavily client with API key from settings."""
        api_key = settings.tavily_api_key
        if not api_key:
            logger.warning("TAVILY_API_KEY not configured - web search will not work")
            self._client = None
        else:
            self._client = TavilyClient(api_key=api_key)

    async def search(self, query: str, max_results: int = 3, include_raw_content = False) -> list[dict[str, Optional[str]]]:
        """
        Search the web for the given query.

        Args:
            query: Search query string
            max_results: Maximum number of results to return (default 3)
            include_raw_content: Whether to return raw content (default False)

        Returns:
            List of search results, each containing title, url, and content
        """
        if not self._client:
            logger.warning("Tavily client not initialized - returning empty results")
            return []

        logger.info(f"Tavily search for: {query}")

        try:
            response = self._client.search(
                query=query,
                max_results=max_results,
                include_answer=False,
                include_raw_content=include_raw_content,
            )

            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", None),
                    "url": item.get("url", None),
                    "content": item.get("content", None),
                    "raw_content": item.get("raw_content", None),
                })

            logger.info(f"Tavily found {len(results)} results for query: '{query}'")
            return results

        except Exception as e:
            logger.error(f"Tavily search error: {e}", exc_info=True)
            return []


# Global singleton instance
_tavily_service: TavilyService | None = None


def get_tavily_service() -> TavilyService:
    """Get or create the global Tavily service instance."""
    global _tavily_service
    if _tavily_service is None:
        _tavily_service = TavilyService()
    return _tavily_service

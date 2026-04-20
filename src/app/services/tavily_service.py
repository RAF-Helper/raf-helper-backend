"""Tavily web search service (mock implementation)."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TavilyService:
    """Web search service using Tavily API.

    This is a mock implementation that returns placeholder results.
    To be replaced with real Tavily API integration later.
    """

    async def search(self, query: str) -> list[dict[str, Any]]:
        """
        Search the web for the given query.

        Args:
            query: Search query string

        Returns:
            List of search results, each containing title, url, and content
        """
        logger.info(f"Mock Tavily search for: {query}")

        # Mock results - replace with real Tavily API call later
        # Real implementation would use: https://api.tavily.com/search
        mock_results = [
            {
                "title": f"Result for '{query}' - Example Source 1",
                "url": "https://example.com/result1",
                "content": f"This is a mock search result for the query '{query}'. "
                           f"Replace this with real Tavily API integration.",
            },
            {
                "title": f"Information about '{query}' - Example Source 2",
                "url": "https://example.com/result2",
                "content": f"Additional mock result for '{query}'. "
                           f"The real Tavily API would return actual web content here.",
            },
        ]

        return mock_results


# Global singleton instance
_tavily_service: TavilyService | None = None


def get_tavily_service() -> TavilyService:
    """Get or create the global Tavily service instance."""
    global _tavily_service
    if _tavily_service is None:
        _tavily_service = TavilyService()
    return _tavily_service

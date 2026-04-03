"""Events agent implementation - uses Elasticsearch staff-index and events-index."""

from .base import BaseAgent, AgentContext
from app.repositories.elasticsearch_repository import ElasticsearchRepository


class EventsAgent(BaseAgent):
    """Provides information about events (from Elasticsearch events-index)."""

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.es_repo = ElasticsearchRepository()

    async def process(self, context: AgentContext, query: str) -> str:
        """Answer questions about events by searching Elasticsearch events-index."""
        raise NotImplementedError("Implement EventsAgent.process()")
        # TODO:
        # 1. Search events index via es_repo.search_events()
        # 2. Format events as context with dates, descriptions, etc.
        # 3. Generate response using LLM with event data

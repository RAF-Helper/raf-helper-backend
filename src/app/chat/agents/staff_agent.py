"""Staff agent implementation - uses Elasticsearch staff-index."""

from .base import BaseAgent, AgentContext
from app.repositories.elasticsearch_repository import ElasticsearchRepository


class StaffAgent(BaseAgent):
    """Provides information about staff members (from Elasticsearch staff-index)."""

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.es_repo = ElasticsearchRepository()

    async def process(self, context: AgentContext, query: str) -> str:
        """Answer questions about staff by searching Elasticsearch staff-index."""
        raise NotImplementedError("Implement StaffAgent.process()")
        # TODO:
        # 1. Search staff index via es_repo.search_staff()
        # 2. Format staff info (name, position, room, department, competences)
        # 3. Generate response with LLM

"""Question answering agent (RAG)."""

from .base import BaseAgent, AgentContext
from app.repositories.elasticsearch_repository import ElasticsearchRepository


class QAAgent(BaseAgent):
    """Question answering based on context materials (RAG)."""

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.es_repo = ElasticsearchRepository()

    async def process(self, context: AgentContext, query: str) -> str:
        """Answer questions using uploaded materials."""
        raise NotImplementedError("Implement QAAgent.process()")
        # TODO:
        # 1. If context_material_ids provided, retrieve those chunks
        # 2. Otherwise perform semantic search on context index
        # 3. Build prompt with retrieved context
        # 4. Generate answer with citations

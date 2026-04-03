"""Events agent implementation - uses Elasticsearch events-index."""

from .base import BaseAgent
from ..state import AgentInput, AgentOutput
from app.repositories.elasticsearch_repository import ElasticsearchRepository
from ...schemas.agent import AgentType


class EventsAgent(BaseAgent):
    """Provides information about events (from Elasticsearch events-index)."""

    agent_type = AgentType.events
    tools = []  # TODO: Add tools for event search if needed

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.es_repo = ElasticsearchRepository()

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Answer questions about events by searching Elasticsearch events-index."""
        # TODO: Implement actual event search
        # 1. Search events index via self.es_repo.search_events(inp.masked_message)
        # 2. Format events as context
        # 3. Generate response

        response = await self._call_llm(
            system_prompt="You are an events assistant. Answer questions about university events.",
            user_prompt=inp.masked_message,
            context="No events found yet.",  # Placeholder
            history=inp.history,
            temperature=0.7,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )

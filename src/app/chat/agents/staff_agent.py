"""Staff agent implementation - uses Elasticsearch staff-index."""

from .base import BaseAgent
from ..state import AgentInput, AgentOutput
from app.repositories.elasticsearch_repository import ElasticsearchRepository
from ...schemas.agent import AgentType


class StaffAgent(BaseAgent):
    """Provides information about staff members (from Elasticsearch staff-index)."""

    agent_type = AgentType.staff
    tools = []  # TODO: Add tools for staff search if needed

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.es_repo = ElasticsearchRepository()

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Answer questions about staff by searching Elasticsearch staff-index."""
        # TODO: Implement actual staff search
        # 1. Search staff index via self.es_repo.search_staff(inp.masked_message)
        # 2. Format staff information
        # 3. Generate response

        response = await self._call_llm(
            system_prompt="You are a staff assistant. Answer questions about faculty staff members.",
            user_prompt=inp.masked_message,
            context="No staff information available yet.",  # Placeholder
            history=inp.history,
            temperature=0.7,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )

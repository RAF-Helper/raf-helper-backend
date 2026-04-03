"""Question answering agent (RAG)."""

from .base import BaseAgent
from ..state import AgentInput, AgentOutput
from app.repositories.elasticsearch_repository import ElasticsearchRepository
from ...schemas.agent import AgentType


class QAAgent(BaseAgent):
    """Question answering based on context materials (RAG)."""

    agent_type = AgentType.qa
    prompt_name = "qa_agent"
    tools = []  # TODO: Add tools for document search if needed

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.es_repo = ElasticsearchRepository()

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Answer questions using uploaded materials."""
        # TODO: Implement actual RAG retrieval
        # 1. If inp.file_ids provided, retrieve those chunks
        # 2. Otherwise perform semantic search on context index
        # 3. Build context with retrieved chunks

        context = "No context materials available."  # Placeholder
        if inp.file_ids:
            # TODO: Retrieve chunks for these file IDs
            pass

        prompt = self._format_prompt(
            query=inp.masked_message,
            context=context,
            history=inp.history[-10:] if inp.history else [],
        )

        response = await self._call_llm(
            system_prompt=prompt,
            temperature=0.7,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )

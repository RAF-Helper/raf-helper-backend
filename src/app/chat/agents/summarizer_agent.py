"""Summarizer agent implementation."""

from .base import BaseAgent
from ...schemas.agent import AgentType
from ..state import AgentInput, AgentOutput


class SummarizerAgent(BaseAgent):
    """Summarizes context materials with different modes."""

    agent_type = AgentType.summarizer
    prompt_name = "summarizer_agent"

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        """
        Summarize materials.
        """

        # TODO: Extract context materials from inp.file_ids or inp.history

        prompt = self._format_prompt(
            mode="default",
            query=inp.masked_message,
            context="No context materials available.",  # Placeholder
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

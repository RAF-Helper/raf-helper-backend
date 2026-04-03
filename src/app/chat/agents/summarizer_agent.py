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

        Query determines mode: "brief", "default", "deep dive".
        """
        # Determine mode from query (simple keyword matching for now)
        query_lower = inp.masked_message.lower()
        if "brief" in query_lower or "кратко" in query_lower:
            mode = "brief"
        elif "deep" in query_lower or "детально" in query_lower or "подробно" in query_lower:
            mode = "deep_dive"
        else:
            mode = "default"

        # TODO: Extract context materials from inp.file_ids or inp.history

        prompt = self._format_prompt(
            mode=mode,
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
            metadata={"summarization_mode": mode},
        )

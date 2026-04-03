"""Support agent implementation."""

from .base import BaseAgent
from ...schemas.agent import AgentType
from ..state import AgentInput, AgentOutput


class SupportAgent(BaseAgent):
    """Handles general support and system capability queries."""

    agent_type = AgentType.support
    prompt_name = "support_agent"

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Process general support queries."""
        # Build prompt with context
        prompt = self._format_prompt(
            query=inp.masked_message,
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

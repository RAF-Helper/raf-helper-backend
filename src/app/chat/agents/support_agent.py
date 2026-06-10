"""Support agent implementation."""

from app.chat.agents.base import BaseAgent
from app.schemas.agent import AgentType
from app.chat.state import AgentInput, AgentOutput


class SupportAgent(BaseAgent):
    """Handles general support and system capability queries."""

    agent_type = AgentType.support
    prompt_name = "support_agent"

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Process general support queries."""
        prompt = self._format_prompt(
            query=inp.masked_message,
        )

        response = await self._call_llm(
            system_prompt=prompt,
            history=inp.history[-10:] if inp.history else [],
            temperature=0.5,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )

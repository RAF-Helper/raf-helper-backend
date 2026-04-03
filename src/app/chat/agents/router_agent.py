"""Router agent implementation."""

from .base import BaseAgent
from ..state import AgentInput, AgentOutput
from ...schemas.agent import AgentType


class RouterAgent(BaseAgent):
    """Router agent - determines which agent to use based on query routing."""

    agent_type = AgentType.orchestrator
    tools = []  # Router doesn't need tools

    def __init__(self, llm_client, agent_names: list[str]):
        super().__init__(llm_client)
        self.agent_names = agent_names

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Route query to appropriate agent based on semantic similarity + LLM fallback."""
        raise NotImplementedError("To be implemented later")

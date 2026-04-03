"""Router agent implementation."""

from .base import BaseAgent, AgentContext


class RouterAgent(BaseAgent):
    """Router agent - determines which agent to use based on query routing."""

    def __init__(self, llm_client, agent_names: list[str]):
        super().__init__(llm_client)
        self.agent_names = agent_names

    async def process(self, context: AgentContext, query: str) -> str:
        """Route query to appropriate agent based on semantic similarity + LLM fallback."""
        raise NotImplementedError("Implement RouterAgent.process()")
        # TODO:
        # 1. Semantic routing: find agent examples most similar to query
        # 2. If tie or low confidence, use LLM fallback to select agent
        # 3. Return the selected agent name

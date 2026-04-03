"""Summarizer agent implementation."""

from .base import BaseAgent, AgentContext


class SummarizerAgent(BaseAgent):
    """Summarizes context materials with different modes."""

    async def process(self, context: AgentContext, query: str) -> str:
        """
        Summarize materials.

        Query determines mode: "brief", "default", "deep dive".
        """
        raise NotImplementedError("Implement SummarizerAgent.process()")
        # TODO:
        # 1. Determine mode from query
        # 2. Load context materials from conversation
        # 3. Generate appropriate summary based on mode
        # 4. For deep dive, focus on user-specified spheres

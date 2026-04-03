"""Presentation agent - generates presentations (subagents: planner, slider)."""

from .base import BaseAgent
from ...schemas.agent import AgentType
from ..state import AgentInput, AgentOutput


class PresentationAgent(BaseAgent):
    """
    Generates PowerPoint presentations from context materials.

    Uses subagents:
    1. SlidePlanner creates slide outline
    2. Slider creates each slide iteratively using previous summaries
    3. SlideSummarizer summarizes previous slides for context
    4. Export to .pptx using python-pptx
    """

    agent_type = AgentType.presentation
    tools = []  # TODO: Add tools for content formatting if needed

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.planner = SlidePlannerAgent(llm_client)
        self.slider = SliderAgent(llm_client)
        self.summarizer = SlideSummarizerAgent(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Generate PowerPoint presentation."""
        # TODO: Implement full presentation generation pipeline
        # For now, return placeholder

        response = await self._call_llm(
            system_prompt="You are a presentation assistant.",
            user_prompt=inp.masked_message,
            context="Presentation generation not yet fully implemented.",
            temperature=0.7,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )


class SlidePlannerAgent(BaseAgent):
    """Plans slide structure."""

    agent_type = AgentType.presentation

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        raise NotImplementedError("Implement SlidePlannerAgent.run()")


class SliderAgent(BaseAgent):
    """Creates individual slides."""

    agent_type = AgentType.presentation

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        raise NotImplementedError("Implement SliderAgent.run()")


class SlideSummarizerAgent(BaseAgent):
    """Summarizes previous slides for context."""

    agent_type = AgentType.presentation

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        raise NotImplementedError("Implement SlideSummarizerAgent.run()")

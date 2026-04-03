"""Presentation agent - generates presentations (subagents: planner, slider)."""

from .base import BaseAgent, AgentContext


class PresentationAgent(BaseAgent):
    """
    Generates PowerPoint presentations from context materials.

    Uses subagents:
    1. SlidePlanner creates slide outline
    2. Slider creates each slide iteratively using previous summaries
    3. SlideSummarizer summarizes previous slides for context
    4. Export to .pptx using python-pptx
    """

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.planner = SlidePlannerAgent(llm_client)
        self.slider = SliderAgent(llm_client)
        self.summarizer = SlideSummarizerAgent(llm_client)

    async def process(self, context: AgentContext, query: str) -> str:
        """Generate PowerPoint presentation."""
        raise NotImplementedError("Implement PresentationAgent.process()")
        # TODO:
        # 1. Planner: create slide outline
        # 2. For each slide: Slider creates slide using previous summaries
        # 3. Summarize slide after creation
        # 4. Generate .pptx file with python-pptx


class SlidePlannerAgent(BaseAgent):
    """Plans slide structure."""

    async def process(self, context: AgentContext, query: str) -> str:
        raise NotImplementedError("Implement SlidePlannerAgent.process()")


class SliderAgent(BaseAgent):
    """Creates individual slides."""

    async def process(self, context: AgentContext, query: str) -> str:
        raise NotImplementedError("Implement SliderAgent.process()")


class SlideSummarizerAgent(BaseAgent):
    """Summarizes previous slides for context."""

    async def process(self, context: AgentContext, query: str) -> str:
        raise NotImplementedError("Implement SlideSummarizerAgent.process()")

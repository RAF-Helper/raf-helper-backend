"""Presentation agent - generates presentations (subagents: planner, slider)."""

import logging

from app.chat.agents.base import BaseAgent
from app.schemas.agent import AgentType
from app.chat.state import AgentInput, AgentOutput
from app.tools.search_tools import get_materials_fragments_def


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
    tools = [get_materials_fragments_def]  # Main tool for presentation content

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.planner = SlidePlannerAgent(llm_client)
        self.slider = SliderAgent(llm_client)
        self.summarizer = SlideSummarizerAgent(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Generate PowerPoint presentation using material retrieval tool."""
        template = self._load_prompt("presentation_agent")
        system_prompt = template.format(query=inp.masked_message)

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=inp.masked_message,
            history=inp.history,
            temperature=0.7,
            use_tools=True,
            file_ids=inp.file_ids,
            use_web_search=inp.use_web_search,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )


class SlidePlannerAgent(BaseAgent):
    """Plans slide structure."""

    agent_type = AgentType.presentation
    tools = []  # Will use get_materials_fragments when fully implemented

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        raise NotImplementedError("Implement SlidePlannerAgent.run()")


class SliderAgent(BaseAgent):
    """Creates individual slides."""

    agent_type = AgentType.presentation
    tools = [get_materials_fragments_def]  # Will need material retrieval

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        raise NotImplementedError("Implement SliderAgent.run()")


class SlideSummarizerAgent(BaseAgent):
    """Summarizes previous slides for context."""

    agent_type = AgentType.presentation
    tools = []  # Summarization doesn't need retrieval

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        raise NotImplementedError("Implement SlideSummarizerAgent.run()")

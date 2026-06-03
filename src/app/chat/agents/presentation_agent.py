"""Presentation agent - generates presentations (subagents: planner, slider)."""

import logging

from app.chat.agents.base import BaseAgent
from app.schemas.agent import AgentType
from app.chat.state import AgentInput, AgentOutput
from app.tools.search_tools import get_materials_fragments_def

logger = logging.getLogger(__name__)

class PresentationAgent(BaseAgent):
    """
    Generates PowerPoint presentations from context materials.
    """

    agent_type = AgentType.presentation
    tools = [get_materials_fragments_def]

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.planner = SlidePlannerAgent(llm_client)
        self.slider = SliderAgent(llm_client)
        self.summarizer = SlideSummarizerAgent(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
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
    prompt_name = "presentation_planner"

    async def run(self, inp: AgentInput) -> AgentOutput:
        system_prompt = self._load_prompt(self.prompt_name)

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=inp.masked_message,
            temperature=0.3
        )

        try:
            import json
            content = response.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            outline = json.loads(content)
            if isinstance(outline, list):
                return AgentOutput(content=json.dumps(outline), agent_used=self.agent_type, masked_query=inp.masked_message)
        except Exception as e:
            logger.error(f"Error parsing slide planner response: {e}")

        return AgentOutput(content="[\"Introduction\", \"Core Concept\", \"Conclusion\"]", agent_used=self.agent_type, masked_query=inp.masked_message)


class SliderAgent(BaseAgent):
    """Creates individual slides."""

    agent_type = AgentType.presentation
    tools = [get_materials_fragments_def]
    prompt_name = "presentation_slider"

    async def run(self, inp: AgentInput) -> AgentOutput:
        system_prompt = self._load_prompt(self.prompt_name)

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=inp.masked_message,
            temperature=0.7,
            use_tools=True,
            file_ids=inp.file_ids,
            use_web_search=inp.use_web_search,
        )

        return AgentOutput(content=response, agent_used=self.agent_type, masked_query=inp.masked_message)


class SlideSummarizerAgent(BaseAgent):
    """Summarizes previous slides for context."""

    agent_type = AgentType.presentation
    prompt_name = "presentation_summarizer"

    async def run(self, inp: AgentInput) -> AgentOutput:
        system_prompt = self._load_prompt(self.prompt_name)

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=inp.masked_message,
            temperature=0.3
        )

        return AgentOutput(content=response, agent_used=self.agent_type, masked_query=inp.masked_message)

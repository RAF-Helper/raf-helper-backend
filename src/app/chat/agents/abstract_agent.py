"""Abstract agent - generates abstracts (subagents: planner, writer, summarizer, reviewer)."""

import logging

from app.chat.agents.base import BaseAgent
from app.schemas.agent import AgentType
from app.chat.state import AgentInput, AgentOutput

logger = logging.getLogger(__name__)

class AbstractAgent(BaseAgent):
    """
    Generates abstracts from context materials.
    """

    agent_type = AgentType.abstract
    tools = []

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.planner = PlannerAgent(llm_client)
        self.writer = ChapterWriterAgent(llm_client)
        self.summarizer = ChapterSummarizerAgent(llm_client)
        self.reviewer = ChapterReviewerAgent(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        """This method is primarily used as a stub; iterative logic is in the graph."""
        return AgentOutput(
            content="Abstract generation is handled by the iterative graph pipeline.",
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )


class PlannerAgent(BaseAgent):
    """Plans chapter structure based on topic research."""

    agent_type = AgentType.abstract
    prompt_name = "abstract_planner"

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
            logger.error(f"Error parsing planner response: {e}")

        return AgentOutput(content="[\"Introduction\", \"Main Content\", \"Conclusion\"]", agent_used=self.agent_type, masked_query=inp.masked_message)


class ChapterWriterAgent(BaseAgent):
    """Writes individual chapters."""

    agent_type = AgentType.abstract
    prompt_name = "abstract_writer"

    async def run(self, inp: AgentInput) -> AgentOutput:
        system_prompt = self._load_prompt(self.prompt_name)

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=inp.masked_message,
            temperature=0.7
        )

        return AgentOutput(content=response, agent_used=self.agent_type, masked_query=inp.masked_message)


class ChapterSummarizerAgent(BaseAgent):
    """Summarizes earlier chapters for context management."""

    agent_type = AgentType.abstract
    prompt_name = "abstract_summarizer"

    async def run(self, inp: AgentInput) -> AgentOutput:
        system_prompt = self._load_prompt(self.prompt_name)

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=inp.masked_message,
            temperature=0.3
        )

        return AgentOutput(content=response, agent_used=self.agent_type, masked_query=inp.masked_message)


class ChapterReviewerAgent(BaseAgent):
    """Reviews generated chapters for quality, coherence, and completeness."""

    agent_type = AgentType.abstract
    prompt_name = "abstract_reviewer"

    async def run(self, inp: AgentInput) -> AgentOutput:
        system_prompt = self._load_prompt(self.prompt_name)

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=inp.masked_message,
            temperature=0.3,
        )

        return AgentOutput(content=response, agent_used=self.agent_type, masked_query=inp.masked_message)

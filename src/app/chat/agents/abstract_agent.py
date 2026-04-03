"""Abstract agent - generates abstracts (subagents: planner, writer, summarizer)."""

from .base import BaseAgent
from ...schemas.agent import AgentType
from ..state import AgentInput, AgentOutput


class AbstractAgent(BaseAgent):
    """
    Generates abstracts from context materials.

    Uses subagents in an iterative pipeline:
    1. Planner constructs chapter outline
    2. For each chapter: Writer creates chapter based on previous chapters
    3. Each N-th chapter: Summarizer condenses earlier chapters
    """

    agent_type = AgentType.abstract
    tools = []  # TODO: Add tools for document access

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.planner = PlannerAgent(llm_client)
        self.writer = ChapterWriterAgent(llm_client)
        self.summarizer = ChapterSummarizerAgent(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Generate abstract with iterative chapter creation."""
        # TODO: Implement full iterative pipeline
        # For now, return placeholder

        response = await self._call_llm(
            system_prompt="You are an abstract generation assistant.",
            user_prompt=inp.masked_message,
            context="Abstract generation not yet fully implemented.",
            temperature=0.7,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )


class PlannerAgent(BaseAgent):
    """Plans chapter structure based on topic research."""

    agent_type = AgentType.abstract

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        raise NotImplementedError("Implement PlannerAgent.run()")


class ChapterWriterAgent(BaseAgent):
    """Writes individual chapters."""

    agent_type = AgentType.abstract

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        raise NotImplementedError("Implement ChapterWriterAgent.run()")


class ChapterSummarizerAgent(BaseAgent):
    """Summarizes earlier chapters for context management."""

    agent_type = AgentType.abstract

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        raise NotImplementedError("Implement ChapterSummarizerAgent.run()")

"""Abstract agent - generates abstracts (subagents: planner, writer, summarizer)."""

from .base import BaseAgent, AgentContext


class AbstractAgent(BaseAgent):
    """
    Generates abstracts from context materials.

    Uses subagents in an iterative pipeline:
    1. Planner constructs chapter outline
    2. For each chapter: Writer creates chapter based on previous chapters
    3. Each N-th chapter: Summarizer condenses earlier chapters
    """

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.planner = PlannerAgent(llm_client)
        self.writer = ChapterWriterAgent(llm_client)
        self.summarizer = ChapterSummarizerAgent(llm_client)

    async def process(self, context: AgentContext, query: str) -> str:
        """Generate abstract with iterative chapter creation."""
        raise NotImplementedError("Implement AbstractAgent.process()")
        # TODO:
        # 1. Planner: create chapter plan from research
        # 2. For each chapter:
        #    - Use previous full chapters + summaries of earlier ones
        #    - Generate chapter content
        # 3. Adapt to LaTeX template


class PlannerAgent(BaseAgent):
    """Plans chapter structure based on topic research."""

    async def process(self, context: AgentContext, query: str) -> str:
        raise NotImplementedError("Implement PlannerAgent.process()")


class ChapterWriterAgent(BaseAgent):
    """Writes individual chapters."""

    async def process(self, context: AgentContext, query: str) -> str:
        raise NotImplementedError("Implement ChapterWriterAgent.process()")


class ChapterSummarizerAgent(BaseAgent):
    """Summarizes earlier chapters for context management."""

    async def process(self, context: AgentContext, query: str) -> str:
        raise NotImplementedError("Implement ChapterSummarizerAgent.process()")

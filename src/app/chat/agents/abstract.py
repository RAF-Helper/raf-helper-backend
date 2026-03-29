"""Abstract agent — generates structured essays from context materials.

Sub-agents (all stubs):
  Planner → ChapterWriter → ChapterSummarizer (iterative per chapter)
LaTeX export: TODO after LLM integration.
"""

from typing import Optional
from ..state import AgentInput, AgentOutput
from ...schemas.agent import AgentType
from ...repositories.elasticsearch_repository import ElasticsearchRepository
from .base import BaseAgent

_PLANNER_PROMPT = """Based on the provided materials and the user's topic, create a detailed
chapter plan. Return a numbered list of chapter titles with a one-sentence description each.
Respond in the same language as the user."""

_WRITER_PROMPT = """Write the next chapter using the context materials and summaries of
previous chapters. Be informative and cite specific facts. Respond in the same language."""

_SUMMARIZER_PROMPT = "Summarize the provided chapter into a concise paragraph for use as context in later chapters."

ROUTING_EXAMPLES = [
    "напиши реферат", "сделай реферат по теме", "abstract",
    "write an essay", "реферат по материалам", "напиши научную работу", "составь реферат",
]


class AbstractAgent(BaseAgent):
    agent_type = AgentType.abstract

    def __init__(self, es_repo: Optional[ElasticsearchRepository] = None):
        self.es_repo = es_repo or ElasticsearchRepository()

    async def run(self, inp: AgentInput) -> AgentOutput:
        hits = await self.es_repo.search_context(
            query=inp.masked_message, document_ids=inp.file_ids or None, limit=30
        )
        context_chunks = [h.get("chunk_text", "") for h in hits if h.get("chunk_text")]

        # TODO Stage 1 — Planner:
        # plan_text = await self._call_llm(_PLANNER_PROMPT, self._build_messages([], inp.masked_message, context_chunks))
        # chapters = _parse_plan(plan_text)
        chapters = ["Chapter 1 (stub)", "Chapter 2 (stub)", "Chapter 3 (stub)"]

        # TODO Stage 2 — ChapterWriter (iterative):
        # for each chapter: write using context + previous chapter (full) + earlier summaries
        # TODO Stage 3 — ChapterSummarizer: summarize each chapter for next iteration
        # TODO: convert assembled text to LaTeX template

        content = (
            f"[STUB] AbstractAgent: LLM integration pending.\n"
            f"Would generate {len(chapters)} chapters from {len(context_chunks)} chunks."
        )

        return AgentOutput(content=content, agent_used=self.agent_type, masked_query=inp.masked_message,
                           metadata={"chapter_count": len(chapters), "chunks_used": len(context_chunks)})

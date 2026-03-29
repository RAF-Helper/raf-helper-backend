"""Orchestrator — routes user messages to the appropriate agent.

Routing strategy (two-stage):
  1. Semantic routing (stub): embed query → cosine similarity vs agent example collections.
  2. LLM fallback (stub): when top-2 agents are too close, ask LLM to decide.

Falls back to keyword routing while embedding/LLM are not integrated.
"""

import math
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.agent import AgentType, SummarizationMode
from .state import AgentInput, AgentOutput
from .agents.support import SupportAgent, ROUTING_EXAMPLES as SUPPORT_EX
from .agents.events import EventsAgent, ROUTING_EXAMPLES as EVENTS_EX
from .agents.staff import StaffAgent, ROUTING_EXAMPLES as STAFF_EX
from .agents.qa import QAAgent, ROUTING_EXAMPLES as QA_EX
from .agents.summarizer import SummarizerAgent, ROUTING_EXAMPLES as SUMMARIZER_EX
from .agents.abstract import AbstractAgent, ROUTING_EXAMPLES as ABSTRACT_EX
from .agents.presentation import PresentationAgent, ROUTING_EXAMPLES as PRESENTATION_EX
from ..pii.presidio_masker import PIIMasker
from ..repositories.elasticsearch_repository import ElasticsearchRepository

_SIMILARITY_THRESHOLD = 0.05

_AGENT_EXAMPLES: dict[AgentType, list[str]] = {
    AgentType.support: SUPPORT_EX,
    AgentType.events: EVENTS_EX,
    AgentType.staff: STAFF_EX,
    AgentType.qa: QA_EX,
    AgentType.summarizer: SUMMARIZER_EX,
    AgentType.abstract: ABSTRACT_EX,
    AgentType.presentation: PRESENTATION_EX,
}


class Orchestrator:
    def __init__(self):
        es_repo = ElasticsearchRepository()
        self._agents = {
            AgentType.support: SupportAgent(),
            AgentType.events: EventsAgent(es_repo),
            AgentType.staff: StaffAgent(es_repo),
            AgentType.qa: QAAgent(es_repo),
            AgentType.summarizer: SummarizerAgent(es_repo),
            AgentType.abstract: AbstractAgent(es_repo),
            AgentType.presentation: PresentationAgent(es_repo),
        }
        self._pii = PIIMasker()

    async def process(
        self,
        message: str,
        chat_id: int,
        user_id: int,
        history: list[dict[str, str]],
        file_ids: list[int],
        use_web_search: bool,
        forced_agent: Optional[AgentType],
        summarization_mode: SummarizationMode,
        session: AsyncSession,
    ) -> AgentOutput:
        masked = await self._pii.mask_text(message)

        inp = AgentInput(
            message=message,
            masked_message=masked,
            chat_id=chat_id,
            user_id=user_id,
            history=history,
            file_ids=file_ids,
            use_web_search=use_web_search,
            summarization_mode=summarization_mode,
            forced_agent=forced_agent,
        )

        agent_type = forced_agent if forced_agent is not None else await self._route(masked)
        return await self._agents[agent_type].run(inp)

    async def _route(self, query: str) -> AgentType:
        try:
            query_vec = await self._embed(query)
            scores: dict[AgentType, float] = {}
            for agent_type, examples in _AGENT_EXAMPLES.items():
                vecs = [await self._embed(ex) for ex in examples]
                scores[agent_type] = max(_cosine(query_vec, v) for v in vecs)
            ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            if ranked[0][1] - ranked[1][1] < _SIMILARITY_THRESHOLD:
                try:
                    return await self._llm_route(query, [t for t, _ in ranked[:3]])
                except NotImplementedError:
                    pass
            return ranked[0][0]
        except NotImplementedError:
            return self._keyword_route(query)

    def _keyword_route(self, query: str) -> AgentType:
        q = query.lower()
        if any(kw in q for kw in ("реферат", "abstract", "essay")):
            return AgentType.abstract
        if any(kw in q for kw in ("презентац", "слайд", "presentation", "slide")):
            return AgentType.presentation
        if any(kw in q for kw in ("суммар", "кратко", "summary", "summarize", "конспект")):
            return AgentType.summarizer
        if any(kw in q for kw in ("событи", "мероприяти", "event", "bonus", "бонус")):
            return AgentType.events
        if any(kw in q for kw in ("сотрудник", "преподаватель", "кабинет", "staff", "professor")):
            return AgentType.staff
        if any(kw in q for kw in ("помощь", "help", "умеешь", "можешь", "система")):
            return AgentType.support
        return AgentType.qa

    async def _embed(self, text: str) -> list[float]:
        """TODO: implement with LangChain embeddings via OpenRouter.

            from langchain_openai import OpenAIEmbeddings
            embedder = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.openrouter_api_key,
                openai_api_base=settings.openrouter_base_url,
            )
            return await embedder.aembed_query(text)
        """
        raise NotImplementedError("Embedding service not yet integrated.")

    async def _llm_route(self, query: str, candidates: list[AgentType]) -> AgentType:
        """TODO: ask a small/fast LLM model to pick the best agent.

            from langchain_openai import ChatOpenAI
            ...
        """
        raise NotImplementedError("LLM routing fallback not yet integrated.")


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0

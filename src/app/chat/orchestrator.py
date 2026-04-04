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
from .agents.support_agent import SupportAgent
from .agents.events_agent import EventsAgent
from .agents.staff_agent import StaffAgent
from .agents.qa_agent import QAAgent
from .agents.summarizer_agent import SummarizerAgent
from .agents.abstract_agent import AbstractAgent
from .agents.presentation_agent import PresentationAgent
from ..pii.presidio_masker import PIIMasker
from ..repositories.elasticsearch_repository import ElasticsearchRepository


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
        masked, spans = await self._pii.mask_text_with_spans(message)

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
            pii_spans=spans,
        )

        agent_type = forced_agent if forced_agent is not None else await self._route(masked)
        return await self._agents[agent_type].run(inp)

    async def _route(self, query: str) -> AgentType:
        """TODO: implement routing pipeline with calling of the agent necessary.
        Will include:
        - Embedding the query;
        - Finding the closest examples in the postgres table of route examples;
        - Analysing results and choosing the best possible routes;
        - Call LLM in case the routes are too close or can't be determined.

        Fallback examples or route mechanics may be added in the future, but for now pipeline is fixed.
        """
        raise NotImplementedError("Routing not done yet.")

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

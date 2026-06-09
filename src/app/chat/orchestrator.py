"""Orchestrator — routes user messages to the appropriate agent.

Routing strategy (two-stage):
  1. Semantic routing (stub): embed query → cosine similarity vs agent example collections.
  2. LLM fallback (stub): when top-2 agents are too close, ask LLM to decide.

Falls back to keyword routing while embedding/LLM are not integrated.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.services import ChatServices
from app.schemas.agent import AgentType, SummarizationMode
from app.chat.state import AgentInput, AgentOutput
from app.chat.agents.support_agent import SupportAgent
from app.chat.agents.events_agent import EventsAgent
from app.chat.agents.staff_agent import StaffAgent
from app.chat.agents.qa_agent import QAAgent
from app.chat.agents.summarizer_agent import SummarizerAgent
from app.chat.agents.abstract_agent import AbstractAgent
from app.chat.agents.presentation_agent import PresentationAgent
from app.pii.presidio_masker import PIIMasker
from app.chat.llm import OpenRouterClient, LLMMessage
from app.services.embedding_service import get_embedding_service
from app.repositories.routing_repository import RoutingRepository
from app.config import settings
from app.chat.agents.router_agent import RouterAgent
from app.chat.state import AgentInput

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, services: ChatServices):
        self._services = services
        self._llm = services.agentic_llm
        self.router_llm = services.router_llm
        self._pii = services.pii
        self._embedder = services.embedder

        self._agents = {
            AgentType.support: SupportAgent(self._llm),
            AgentType.events: EventsAgent(self._llm),
            AgentType.staff: StaffAgent(self._llm),
            AgentType.qa: QAAgent(self._llm),
            AgentType.summarizer: SummarizerAgent(self._llm),
            AgentType.abstract: AbstractAgent(self._llm),
            AgentType.presentation: PresentationAgent(self._llm),
        }

    async def route(self, query: str, session: AsyncSession) -> AgentType:
        """Route query using two-stage pipeline: Semantic Search -> RouterAgent Fallback."""
        try:
            # Instantiate repo with request session
            routing_repo = RoutingRepository(session)

            # Stage 1: Semantic Routing
            vector = await self._embedder.embed_text(query)
            hits = await routing_repo.search_intents(vector, k=5)

            if hits:
                # Aggregate scores by route
                route_scores: dict[str, list[float]] = {}
                for hit in hits:
                    rid = hit["route_id"]
                    score = hit["score"]
                    if rid not in route_scores:
                        route_scores[rid] = []
                    route_scores[rid].append(score)

                # Calculate average similarity per route
                averages = {rid: sum(s)/len(s) for rid, s in route_scores.items()}
                sorted_routes = sorted(averages.items(), key=lambda x: x[1], reverse=True)

                s1, r1 = sorted_routes[0]
                s2 = sorted_routes[1][1] if len(sorted_routes) > 1 else 0.0

                # Decision Engine: Threshold and Margin check
                if s1 >= settings.routing_threshold and (s1 - s2) >= settings.routing_margin:
                    logger.info(f"Semantic route found: {r1} (score: {s1:.4f}, margin: {s1-s2:.4f}, threshold: {settings.routing_threshold}, margin_req: {settings.routing_margin})")
                    return AgentType(r1)

                logger.info(f"Semantic routing ambiguous or low confidence (s1: {s1:.4f}, s2: {s2:.4f}, delta: {s1-s2:.4f}). Falling back to RouterAgent.")

        except Exception as e:
            logger.error(f"Error during semantic routing: {e}", exc_info=True)
            # IMPORTANT: Rollback the session to clear the failed transaction state
            # so that subsequent DB calls in the same request don't fail.
            await session.rollback()

        router = RouterAgent(self.router_llm)
        router_inp = AgentInput(
            message="",
            masked_message=query,
            chat_id=0,
            user_id=0,
            history=[],
            file_ids=[],
            use_web_search=False,
            summarization_mode=None,
            forced_agent=None,
            pii_spans=[],
        )

        result = await router.run(router_inp)
        return AgentType(result.content)

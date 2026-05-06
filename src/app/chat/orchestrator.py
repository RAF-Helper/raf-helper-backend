"""Orchestrator — routes user messages to the appropriate agent.

Routing strategy (two-stage):
  1. Semantic routing (stub): embed query → cosine similarity vs agent example collections.
  2. LLM fallback (stub): when top-2 agents are too close, ask LLM to decide.

Falls back to keyword routing while embedding/LLM are not integrated.
"""

import logging
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
from .llm import OpenRouterClient, LLMMessage
from ..services.embedding_service import get_embedding_service
from ..repositories.routing_repository import RoutingRepository
from ..config import settings

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        llm_client = OpenRouterClient()
        self._llm = llm_client
        self._agents = {
            AgentType.support: SupportAgent(llm_client),
            AgentType.events: EventsAgent(llm_client),
            AgentType.staff: StaffAgent(llm_client),
            AgentType.qa: QAAgent(llm_client),
            AgentType.summarizer: SummarizerAgent(llm_client),
            AgentType.abstract: AbstractAgent(llm_client),
            AgentType.presentation: PresentationAgent(llm_client),
        }
        self._pii = PIIMasker()
        self._embedder = get_embedding_service()
        self._routing_repo = RoutingRepository()

    async def process(
        self,
        message: str,
        chat_id: int,
        user_id: int,
        history: list[dict[str, str]],
        file_ids: list[str],
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
        """Route query using two-stage pipeline: Semantic Search -> LLM Fallback.

        1. Embed query and search for similar intents in Elasticsearch.
        2. If the top route is confident and unambiguous, route immediately.
        3. Otherwise, fallback to LLM-based routing.
        """
        try:
            # Stage 1: Semantic Routing
            vector = await self._embedder.embed_text(query)
            hits = await self._routing_repo.search_intents(vector, k=5)

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
                    logger.info(f"Semantic route found: {r1} (score: {s1:.4f}, margin: {s1-s2:.4f})")
                    return AgentType(r1)

                logger.info(f"Semantic routing ambiguous or low confidence (s1: {s1:.4f}, s2: {s2:.4f}). Falling back to LLM.")

        except Exception as e:
            logger.error(f"Error during semantic routing: {e}", exc_info=True)

        # Stage 2: LLM Fallback
        return await self._llm_route(query)


    async def _llm_route(self, query: str) -> AgentType:
        """Ask LLM to pick the best agent for the given query using structured JSON output."""
        system = (
            "You are a routing assistant. Based on the user's query, choose the single best agent.\n\n"
            "Agents:\n"
            "- support: off-topic questions, questions about the system itself, greetings\n"
            "- events: university events, competitions, hackathons, bonuses, dates\n"
            "- staff: faculty staff, professors, who teaches what, room numbers\n"
            "- qa: questions about uploaded study materials (lectures, books, PDFs)\n"
            "- summarizer: summarize uploaded materials\n"
            "- abstract: write an essay/abstract based on materials\n"
            "- presentation: create a presentation based on materials\n\n"
            "You must respond in JSON format with a single key 'route' containing the agent slug.\n"
            "Example: {\"route\": \"qa\"}\n"
            "One of: support, events, staff, qa, summarizer, abstract, presentation"
        )
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=query),
        ]
        try:
            # We use a low temperature for deterministic routing
            response = await self._llm.chat(messages=messages, temperature=0.0, max_tokens=50)
            content = response.content.strip()

            # Basic JSON extraction in case the LLM adds markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            import json
            data = json.loads(content)
            chosen = data.get("route", "").strip().lower()

            if chosen in AgentType.__members__:
                return AgentType(chosen)

            logger.warning(f"LLM returned invalid route: {chosen}. Falling back to QA.")
            return AgentType.qa
        except Exception as e:
            logger.error(f"Error in LLM routing: {e}")
            return AgentType.qa

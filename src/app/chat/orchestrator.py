"""Orchestrator — routes user messages to the appropriate agent.

Routing strategy (two-stage):
  1. Semantic routing (stub): embed query → cosine similarity vs agent example collections.
  2. LLM fallback (stub): when top-2 agents are too close, ask LLM to decide.

Falls back to keyword routing while embedding/LLM are not integrated.
"""

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
        """Route query to the appropriate agent using LLM.

        Sends the query to the LLM with a routing prompt describing each agent,
        then parses the response to select the best matching AgentType.
        Falls back to QA agent if parsing fails.
        """
        return await self._llm_route(query)

    async def _llm_route(self, query: str) -> AgentType:
        """Ask LLM to pick the best agent for the given query."""
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
            "Reply with ONLY the agent name, nothing else. "
            "One of: support, events, staff, qa, summarizer, abstract, presentation"
        )
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=query),
        ]
        try:
            response = await self._llm.chat(messages=messages, temperature=0.0, max_tokens=20)
            chosen = response.content.strip().lower().split()[0]
            return AgentType(chosen)
        except Exception:
            return AgentType.qa

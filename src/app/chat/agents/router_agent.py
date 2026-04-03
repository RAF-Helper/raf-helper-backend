"""Router agent implementation."""

from .base import BaseAgent
from ..state import AgentInput, AgentOutput
from ...schemas.agent import AgentType


class RouterAgent(BaseAgent):
    """Router agent - determines which agent to use based on query routing."""

    agent_type = AgentType.orchestrator
    tools = []  # Router doesn't need tools

    def __init__(self, llm_client, agent_names: list[str]):
        super().__init__(llm_client)
        self.agent_names = agent_names

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Route query to appropriate agent based on semantic similarity + LLM fallback."""
        # For now, use keyword routing from masked_message
        query = inp.masked_message

        # Check if forced agent is specified
        if inp.forced_agent:
            agent_type = inp.forced_agent.name
        else:
            agent_type = self._keyword_route(query)

        return AgentOutput(
            content=f"Routing to {agent_type}",
            agent_used=AgentType[agent_type],
            masked_query=inp.masked_message,
            metadata={"routed_agent": agent_type},
        )

    def _keyword_route(self, query: str) -> str:
        """Simple keyword-based routing fallback."""
        q = query.lower()
        if any(kw in q for kw in ("реферат", "abstract", "essay")):
            return "abstract"
        if any(kw in q for kw in ("презентац", "слайд", "presentation", "slide")):
            return "presentation"
        if any(kw in q for kw in ("суммар", "кратко", "summary", "summarize", "конспект")):
            return "summarizer"
        if any(kw in q for kw in ("событи", "мероприяти", "event", "bonus", "бонус")):
            return "events"
        if any(kw in q for kw in ("сотрудник", "преподаватель", "кабинет", "staff", "professor")):
            return "staff"
        if any(kw in q for kw in ("помощь", "help", "умеешь", "можешь", "система")):
            return "support"
        return "qa"

"""Events agent implementation - uses Elasticsearch events-index."""

from app.chat.agents.base import BaseAgent
from app.chat.state import AgentInput, AgentOutput
from app.schemas.agent import AgentType
from app.tools.search_tools import get_events_documents_def


class EventsAgent(BaseAgent):
    """Provides information about events (from Elasticsearch events-index)."""

    agent_type = AgentType.events
    tools = [get_events_documents_def]

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Answer questions about events by searching Elasticsearch events-index.

        Uses the `get_events_documents` tool to retrieve event information.
        """
        system_prompt = self._load_prompt("events_agent")  # Loads from prompts/events_agent.txt
        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=inp.masked_message,
            history=inp.history,
            temperature=0.7,
            use_tools=True,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )

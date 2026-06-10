"""Staff agent implementation - uses Elasticsearch staff-index."""

from app.chat.agents.base import BaseAgent
from app.chat.state import AgentInput, AgentOutput
from app.repositories.elasticsearch_repository import ElasticsearchRepository
from app.schemas.agent import AgentType
from app.tools.search_tools import get_staff_documents_def


class StaffAgent(BaseAgent):
    """Provides information about staff members (from Elasticsearch staff-index)."""

    agent_type = AgentType.staff
    tools = [get_staff_documents_def]

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.es_repo = ElasticsearchRepository()

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Answer questions about staff by searching Elasticsearch staff-index.

        First, performs selective unmasking to restore staff names from the database
        in the user query. Then uses the `get_staff_documents` tool to retrieve
        staff information.
        """
        # Step 1: Selective unmasking - restore staff names
        user_prompt = inp.masked_message
        if inp.pii_spans:
            entity_staff_map = await self.es_repo.find_staff_by_entities(inp.pii_spans)
            if entity_staff_map:
                unmasked_text = inp.masked_message
                spans_to_replace = [
                    span for span in inp.pii_spans
                    if span["entity_type"] == "PERSON" and span["original"] in entity_staff_map
                ]
                spans_to_replace.sort(key=lambda s: s["start"], reverse=True)
                for span in spans_to_replace:
                    hits = entity_staff_map[span["original"]]
                    if hits:
                        top = hits[0]
                        canonical = " ".join([
                            top["surname"],
                            top["name"],
                            top.get("fathers_name") or ""
                        ]).strip()
                        before = unmasked_text[:span["start"]]
                        after = unmasked_text[span["end"]:]
                        unmasked_text = before + canonical + after
                user_prompt = unmasked_text

        # Step 2: Use tool to search staff database
        system_prompt = self._load_prompt("staff_agent")  # Loads from prompts/staff_agent.txt
        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            history=inp.history,
            temperature=0.5,
            use_tools=True,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )

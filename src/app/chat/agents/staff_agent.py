"""Staff agent implementation - uses Elasticsearch staff-index."""

from .base import BaseAgent
from ..state import AgentInput, AgentOutput
from app.repositories.elasticsearch_repository import ElasticsearchRepository
from ...schemas.agent import AgentType


class StaffAgent(BaseAgent):
    """Provides information about staff members (from Elasticsearch staff-index)."""

    agent_type = AgentType.staff
    tools = []  # TODO: Add tools for staff search if needed

    def __init__(self, llm_client):
        super().__init__(llm_client)
        self.es_repo = ElasticsearchRepository()

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Answer questions about staff by searching Elasticsearch staff-index.

        Performs selective unmasking: if PII spans include staff names, they are
        restored from the staff database to preserve useful information in queries.
        """
        # Step 1: Selective unmasking using staff database
        user_prompt = inp.masked_message
        if inp.pii_spans:
            # Find staff matching detected PII PERSON entities
            entity_staff_map = await self.es_repo.find_staff_by_entities(inp.pii_spans)

            if entity_staff_map:
                # Build unmasked version by replacing masked tokens at correct positions.
                # Process spans in reverse order (by start descending) so offsets remain valid.
                unmasked_text = inp.masked_message
                # Filter to PERSON spans that have staff matches
                spans_to_replace = [
                    span for span in inp.pii_spans
                    if span["entity_type"] == "PERSON" and span["original"] in entity_staff_map
                ]
                # Sort descending by start index
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

        # Step 2: Search staff using the original user query (better matching)
        staff_results = await self.es_repo.search_staff(query=inp.message, limit=5)

        # Format staff info as context
        if staff_results:
            context_lines = []
            for s in staff_results:
                full_name = " ".join([s["surname"], s["name"], s.get("fathers_name") or ""]).strip()
                context_lines.append(
                    f"- {full_name}, {s['position']} ({s['department']}), каб. {s['room']}"
                )
            context = "Найдены сотрудники:\n" + "\n".join(context_lines)
        else:
            context = "Информация о сотрудниках не найдена."

        # Step 3: Generate response
        response = await self._call_llm(
            system_prompt="You are a staff assistant. Answer questions about faculty staff members. Provide accurate information based on the context.",
            user_prompt=user_prompt,
            context=context,
            history=inp.history,
            temperature=0.7,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )

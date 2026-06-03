"""Question answering agent (RAG)."""

from app.chat.agents.base import BaseAgent
from app.chat.state import AgentInput, AgentOutput
from app.schemas.agent import AgentType
from app.tools.search_tools import get_materials_fragments_def


class QAAgent(BaseAgent):
    """Question answering based on context materials (RAG)."""

    agent_type = AgentType.qa
    prompt_name = "qa_agent"
    tools = [get_materials_fragments_def]

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Answer questions using uploaded materials.

        Uses the `get_materials_fragments` tool to retrieve relevant document chunks.
        The LLM decides when to invoke the tool based on the query and chat history.
        """
        system_prompt = self._load_prompt("qa_agent")  # Loads from prompts/qa_agent.txt
        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=inp.masked_message,
            history=inp.history[-10:] if inp.history else [],
            temperature=0.7,
            use_tools=True,
            file_ids=inp.file_ids,
            use_web_search=inp.use_web_search,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )

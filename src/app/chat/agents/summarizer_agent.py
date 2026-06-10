"""Summarizer agent implementation."""

from app.chat.agents.base import BaseAgent
from app.schemas.agent import AgentType
from app.chat.state import AgentInput, AgentOutput
from app.tools.search_tools import (
    get_materials_fragments_def,
    list_context_files_def,
    get_file_content_def,
)



class SummarizerAgent(BaseAgent):
    """Summarizes context materials with different modes."""

    agent_type = AgentType.summarizer
    prompt_name = "summarizer_agent"
    tools = [
        get_materials_fragments_def,
        list_context_files_def,
        get_file_content_def,
    ]


    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        """
        Summarize materials using the `get_materials_fragments` tool to retrieve content.
        """
        # Load the base summarizer prompt which includes {mode} and {mode_instructions} placeholders
        template = self._load_prompt("summarizer_agent")
        # Format with the summarization mode from the input
        mode = inp.summarization_mode.value if hasattr(inp.summarization_mode, 'value') else str(inp.summarization_mode)
        # Get mode instructions from the separate file
        mode_instructions = self._load_prompt("summarizer_mode_instructions")
        system_prompt = template.format(mode=mode, mode_instructions=mode_instructions)

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=inp.masked_message,
            history=inp.history[-10:] if inp.history else [],
            temperature=0.4,
            use_tools=True,
            file_ids=inp.file_ids,
            use_web_search=inp.use_web_search,
            chat_id=inp.chat_id,
        )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )

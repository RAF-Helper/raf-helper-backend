"""Router agent for selecting the best specialized agent."""

import logging
import json
from app.chat.agents.base import BaseAgent
from app.chat.state import AgentInput, AgentOutput
from app.schemas.agent import AgentType

logger = logging.getLogger(__name__)

class RouterAgent(BaseAgent):
    """Agent responsible for routing queries to specialized agents using LLM."""

    agent_type = AgentType.support # Default type for the router itself
    prompt_name = "router_agent"

    async def run(self, inp: AgentInput) -> AgentOutput:
        """Determine the best agent for the given query."""
        system_prompt = self._load_prompt("router_agent")

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=inp.masked_message,
            temperature=0.0,
            max_tokens=50,
        )

        try:
            content = response.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            route = data.get("route", "").strip().lower()

            if route in AgentType.__members__:
                return AgentOutput(
                    content=route,
                    agent_used=self.agent_type,
                    masked_query=inp.masked_message,
                )

            logger.warning(f"RouterAgent returned invalid route: {route}. Falling back to QA.")
            return AgentOutput(content="qa", agent_used=self.agent_type, masked_query=inp.masked_message)

        except Exception as e:
            logger.error(f"Error parsing router response: {e}. Falling back to QA.")
            return AgentOutput(content="qa", agent_used=self.agent_type, masked_query=inp.masked_message)

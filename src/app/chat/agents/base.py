"""Base agent interface."""

from abc import ABC, abstractmethod
from typing import Any

from ...config import settings
from ..state import AgentInput, AgentOutput
from ...schemas.agent import AgentType


class BaseAgent(ABC):
    agent_type: AgentType

    @abstractmethod
    async def run(self, inp: AgentInput) -> AgentOutput:
        ...

    async def _call_llm(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """Send conversation to LLM and return assistant reply.

        TODO: implement with LangChain + OpenRouter:

            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

            llm = ChatOpenAI(
                model=settings.openrouter_model,
                openai_api_key=settings.openrouter_api_key,
                openai_api_base=settings.openrouter_base_url,
            )
            lc_messages = [SystemMessage(content=system_prompt)]
            for m in messages:
                if m["role"] == "user":
                    lc_messages.append(HumanMessage(content=m["content"]))
                elif m["role"] == "assistant":
                    lc_messages.append(AIMessage(content=m["content"]))
            response = await llm.ainvoke(lc_messages)
            return response.content
        """
        raise NotImplementedError("LLM integration pending.")

    @staticmethod
    def _build_messages(
        history: list[dict[str, str]],
        user_message: str,
        context_chunks: list[str] | None = None,
    ) -> list[dict[str, str]]:
        msgs = list(history)
        if context_chunks:
            ctx_text = "\n\n---\n\n".join(context_chunks)
            msgs.append({"role": "system", "content": f"Relevant context:\n\n{ctx_text}"})
        msgs.append({"role": "user", "content": user_message})
        return msgs

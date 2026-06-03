"""Base agent interface."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.config import settings
from app.chat.state import AgentInput, AgentOutput
from app.schemas.agent import AgentType
from app.chat.llm import LLMMessage, BaseLLMClient
from app.prompt_loader import get_prompt_manager
from app.tools import TOOL_FUNCTIONS

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents."""

    agent_type: AgentType
    tools: list[dict[str, Any]] = []  # Placeholder for future tool definitions
    prompt_name: str | None = None    # Name of prompt file in prompts/ directory

    def __init__(self, llm_client: BaseLLMClient):
        """
        Initialize agent with LLM client.

        Args:
            llm_client: OpenRouterClient instance for LLM calls
        """
        self.llm_client = llm_client
        self.prompt_manager = get_prompt_manager()
        logger.debug(f"{self.__class__.__name__} initialized")

    @abstractmethod
    async def run(self, inp: AgentInput, **kwargs) -> AgentOutput:
        """Process input and return output."""
        ...

    async def _call_llm(
        self,
        *,
        messages: list[LLMMessage] | None = None,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
        temperature: float = 0.7,
        model: str | None = None,
        max_tokens: int | None = None,
        use_tools: bool = False,
        file_ids: list[int] | None = None,
        use_web_search: bool = False,
        session: Any = None,
        **kwargs: Any,
    ) -> str:
        """
        Unified method to call LLM with flexible input patterns.
        Supports tool calling when use_tools=True and self.tools is defined.
        Automatically executes tool calls in a loop until final response.

        Args:
            messages: Pre-built list of LLMMessage objects (highest priority)
            system_prompt: System message
            user_prompt: User message
            context: Additional context (added as system message)
            history: Optional chat history to prepend as messages with "user"/"assistant" roles
            temperature: Sampling temperature
            model: Override model for this call
            max_tokens: Max tokens to generate
            use_tools: Whether to enable tool calling (tools from self.tools)
            file_ids: List of document IDs from chat context (injected into tool calls)
            use_web_search: Whether to enable web search (injected into tool calls)
            **kwargs: Additional arguments to chat methods

        Returns:
            Final response content string after tool execution (if any)

        Typical patterns:
            # Simple one-shot:
            await self._call_llm(system_prompt="You are a helpful assistant.",
                                 user_prompt="What is 2+2?")

            # With history from AgentInput:
            await self._call_llm(system_prompt="You are a helpful assistant.",
                                 user_prompt="What is 2+2?",
                                 history=inp.history)

            # With context documents:
            await self._call_llm(user_prompt="Question?",
                                 context="Document 1: ... Document 2: ...")

            # With tool context (file_ids, use_web_search):
            await self._call_llm(system_prompt="...",
                                 user_prompt="...",
                                 use_tools=True,
                                 file_ids=inp.file_ids,
                                 use_web_search=inp.use_web_search)
        """
        if messages is not None:
            # Use provided messages directly
            final_messages = messages
        else:
            # Build messages from components
            final_messages = []

            # Add history if provided
            if history:
                for h in history:
                    role = h.get("role", "user")
                    content = h.get("content", "")
                    if content:
                        final_messages.append(LLMMessage(role=role, content=content))

            # Add system prompt (with or without context)
            if system_prompt:
                if context:
                    system_prompt = f"{system_prompt}\n\nContext:\n{context}"
                final_messages.append(LLMMessage(role="system", content=system_prompt))
            elif context:
                # If no system prompt but context exists, use context as system
                final_messages.append(LLMMessage(role="system", content=f"Context:\n{context}"))

            # Add user prompt
            if user_prompt is not None:
                final_messages.append(LLMMessage(role="user", content=user_prompt))

        if not final_messages:
            raise ValueError("No messages provided to LLM")

        # Select calling method based on tools
        if use_tools and self.tools:
            logger.debug(f"Calling LLM with {len(self.tools)} tools")
            # Import tool functions registry here to avoid circular imports

            # Tool execution loop
            while True:
                response = await self.llm_client.chat_with_tools(
                    messages=final_messages,
                    tools=self.tools,
                    temperature=temperature,
                    model=model,
                    max_tokens=max_tokens,
                    **kwargs,
                )

                # Check for tool calls
                tool_calls = response.metadata.get("tool_calls", []) if response.metadata else []

                if not tool_calls:
                    # No tool calls, final response received
                    return response.content

                # Execute each tool call and append result to messages
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("args", {})
                    tool_id = tool_call.get("id")

                    if not tool_name:
                        logger.warning("Tool call missing name, skipping")
                        continue

                    # Inject chat context into tool args for materials search
                    if tool_name == "get_materials_fragments":
                        # Inject document_ids from chat context if not provided
                        if file_ids is not None and "document_ids" not in tool_args:
                            tool_args["document_ids"] = file_ids
                        # Inject use_web_search flag
                        tool_args["use_web_search"] = use_web_search

                    try:
                        func = TOOL_FUNCTIONS.get(tool_name)
                        if not func:
                            result = f"Error: tool '{tool_name}' not found"
                        else:
                            logger.info(f"Executing tool [{tool_name}] with args: {tool_args}")
                            result = await func(**tool_args)
                            logger.info(f"Tool [{tool_name}] returned: {str(result)[:500]}...")
                        result_str = str(result)
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                        result_str = f"Error: {str(e)}"
                        if session:
                            await session.rollback()

                    # Append tool result as a message with role "tool" and tool_call_id
                    final_messages.append(LLMMessage(
                        role="tool",
                        content=result_str,
                        tool_call_id=tool_id or "",
                    ))

                # Continue loop: LLM will process tool results and produce final answer
        else:
            response = await self.llm_client.chat(
                messages=final_messages,
                temperature=temperature,
                model=model,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.content

    def _load_prompt(self, name: str | None = None) -> str:
        """
        Load a prompt template from prompts/ directory.

        Args:
            name: Prompt name (without .txt). Uses self.prompt_name if None.

        Returns:
            Prompt template string
        """
        prompt_name = name or self.prompt_name
        if not prompt_name:
            raise ValueError(f"{self.__class__.__name__} has no prompt_name set")

        return self.prompt_manager.load(prompt_name)

    def _format_prompt(self, name: str | None = None, **kwargs) -> str:
        """
        Load and format a prompt with placeholders.

        Args:
            name: Prompt name (uses self.prompt_name if None)
            **kwargs: Values for placeholders (e.g., query, context, history)

        Returns:
            Formatted prompt string
        """
        template = self._load_prompt(name)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing placeholder in prompt '{name}': {e}")
            raise

    @staticmethod
    def _build_messages(
        history: list[dict[str, str]],
        user_message: str,
        context_chunks: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """
        Build a message list from history, user message, and optional context.

        Args:
            history: Chat history list
            user_message: Current user message
            context_chunks: Optional context chunks to include

        Returns:
            List of message dicts with 'role' and 'content'
        """
        msgs = list(history)
        if context_chunks:
            ctx_text = "\n\n---\n\n".join(context_chunks)
            msgs.append({"role": "system", "content": f"Relevant context:\n\n{ctx_text}"})
        msgs.append({"role": "user", "content": user_message})
        return msgs

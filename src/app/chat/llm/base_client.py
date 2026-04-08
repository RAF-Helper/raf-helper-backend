"""Abstract base LLM client."""

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM."""

    content: str
    usage: dict[str, int] | None = None
    model: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class LLMMessage:
    """Message for LLM conversation."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_call_id: str | None = None  # Required when role="tool"


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send chat completion request to LLM.

        Args:
            messages: List of chat messages
            model: Model to use (optional, uses default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse with content and metadata
        """
        pass

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Chat with tool/function calling support.

        Args:
            messages: List of chat messages
            tools: List of tool definitions in OpenAI format
            model: Model to use
            temperature: Sampling temperature
            **kwargs: Additional arguments

        Returns:
            LLMResponse with tool calls in metadata if any
        """
        pass

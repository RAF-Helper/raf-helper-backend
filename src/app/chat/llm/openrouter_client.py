"""OpenRouter LLM client implementation using LangChain."""

import json
import logging
import time
from typing import Any, AsyncIterator, Callable, TypeVar, Generic
from pydantic import BaseModel
from langchain_openrouter import ChatOpenRouter
from langchain_core.exceptions import LangChainException
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    BaseMessage,
)
from langchain_core.tools import tool as lc_tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from .base_client import BaseLLMClient, LLMResponse, LLMMessage
from app.config import settings
from ...logging_config import log_llm_request, log_llm_response, log_llm_error

logger = logging.getLogger(__name__)


class OpenRouterError(Exception):
    """Custom exception for OpenRouter client errors."""

    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.message = message

    def __str__(self) -> str:
        if self.original_exception:
            return f"{self.message}: {self.original_exception}"
        return self.message

T = TypeVar("T", bound=BaseModel)


class OpenRouterClient(BaseLLMClient):
    """
    OpenRouter API client using LangChain's ChatOpenRouter.

    Features:
    - Async chat completions
    - Tool/function calling in OpenAI format
    - Streaming responses
    - Structured output with Pydantic schemas
    - Automatic retries and error handling
    - Token usage tracking
    - Easy model switching
    """

    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.default_model = settings.openrouter_model

        # Initialize the LangChain client
        self._client = ChatOpenRouter(
            model=self.default_model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=0.7,
            max_tokens=None,
        )

        logger.info(
            f"OpenRouterClient initialized with model={self.default_model}, "
            f"base_url={self.base_url}"
        )

    def _convert_messages(
        self, messages: list[LLMMessage]
    ) -> list[BaseMessage]:
        """
        Convert our LLMMessage format to LangChain BaseMessage format.

        Args:
            messages: List of our LLMMessage objects

        Returns:
            List of LangChain message objects
        """
        converted = []
        for msg in messages:
            if msg.role == "system":
                converted.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                converted.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                converted.append(AIMessage(content=msg.content))
            else:
                logger.warning(f"Unknown message role: {msg.role}, skipping")
        return converted

    def _extract_usage(self, response: Any) -> dict[str, int] | None:
        """
        Extract token usage from LangChain response.

        Args:
            response: LangChain response object

        Returns:
            Dictionary with token_usage or None if not available
        """
        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            return {
                "prompt_tokens": getattr(usage, "input_tokens", 0),
                "completion_tokens": getattr(usage, "output_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }
        return None

    def _build_response(self, response: Any) -> LLMResponse:
        """
        Convert LangChain response to our LLMResponse format.

        Args:
            response: LangChain AIMessage or similar

        Returns:
            LLMResponse object
        """
        content = ""
        if hasattr(response, "content"):
            content = response.content or ""

        usage = self._extract_usage(response)

        metadata: dict[str, Any] = {}
        if hasattr(response, "response_metadata"):
            metadata["response_metadata"] = dict(response.response_metadata)

        # Extract tool calls if present
        if hasattr(response, "tool_calls") and response.tool_calls:
            metadata["tool_calls"] = [
                {
                    "name": tc["name"],
                    "args": tc["args"],
                    "id": tc.get("id"),
                }
                for tc in response.tool_calls
            ]

        # Include additional kwargs (like parsed structured output)
        if hasattr(response, "additional_kwargs"):
            for key, value in response.additional_kwargs.items():
                metadata[key] = value

        model = getattr(response, "response_metadata", {}).get("model_name", None)

        return LLMResponse(
            content=content,
            usage=usage,
            model=model,
            metadata=metadata if metadata else None,
        )

    async def chat(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send chat completion request to OpenRouter.

        Args:
            messages: List of chat messages
            model: Model to use (overrides default if specified)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments passed to ChatOpenRouter

        Returns:
            LLMResponse with content, usage, and metadata

        Raises:
            Exception: If API call fails
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        start_time = time.time()
        model_used = model or self.default_model

        # Log the request
        log_llm_request(
            method="chat",
            messages_count=len(messages),
            model=model_used,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_kwargs=kwargs,
        )

        converted_messages = self._convert_messages(messages)

        # Create a temporary client with overridden parameters if needed
        client = self._client
        if model or temperature != 0.7 or max_tokens:
            client = ChatOpenRouter(
                model=model_used,
                api_key=self.api_key,
                base_url=self.base_url,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

        try:
            response = await client.ainvoke(converted_messages)
            built_response = self._build_response(response)

            # Calculate duration and log success
            duration_ms = (time.time() - start_time) * 1000
            log_llm_response(
                method="chat",
                status="success",
                content_length=len(built_response.content),
                usage=built_response.usage,
                model=built_response.model,
                duration_ms=duration_ms,
            )

            return built_response

        except LangChainException as e:
            duration_ms = (time.time() - start_time) * 1000
            log_llm_error(
                method="chat",
                error=e,
                context={"model": model_used, "duration_ms": duration_ms},
            )
            raise OpenRouterError(f"OpenRouter API error: {e}", e) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_llm_error(
                method="chat",
                error=e,
                context={"model": model_used, "duration_ms": duration_ms},
            )
            raise OpenRouterError(f"OpenRouter request failed: {e}", e) from e

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
            **kwargs: Additional arguments passed to ChatOpenRouter

        Returns:
            LLMResponse with tool calls in metadata if any
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")
        if not tools:
            raise ValueError("Tools list cannot be empty")

        start_time = time.time()
        model_used = model or self.default_model

        # Log the request
        log_llm_request(
            method="chat_with_tools",
            messages_count=len(messages),
            model=model_used,
            temperature=temperature,
            tools_count=len(tools),
            extra_kwargs=kwargs,
        )

        converted_messages = self._convert_messages(messages)

        # Create client with tools bound
        client = ChatOpenRouter(
            model=model_used,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=temperature,
            **kwargs,
        )

        # Bind tools using .bind_tools()
        # LangChain accepts tools in OpenAI format or as Tool objects
        client_with_tools = client.bind_tools(tools)

        try:
            response = await client_with_tools.ainvoke(converted_messages)
            built_response = self._build_response(response)

            # Calculate duration and log success
            duration_ms = (time.time() - start_time) * 1000
            tool_calls_count = len(built_response.metadata.get("tool_calls", [])) if built_response.metadata else 0

            log_llm_response(
                method="chat_with_tools",
                status="success",
                content_length=len(built_response.content),
                usage=built_response.usage,
                model=built_response.model,
                duration_ms=duration_ms,
            )

            return built_response

        except LangChainException as e:
            duration_ms = (time.time() - start_time) * 1000
            log_llm_error(
                method="chat_with_tools",
                error=e,
                context={"model": model_used, "tools": len(tools), "duration_ms": duration_ms},
            )
            raise OpenRouterError(f"OpenRouter API error: {e}", e) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_llm_error(
                method="chat_with_tools",
                error=e,
                context={"model": model_used, "tools": len(tools), "duration_ms": duration_ms},
            )
            raise OpenRouterError(f"OpenRouter request failed: {e}", e) from e

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream chat completion response.

        Args:
            messages: List of chat messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments

        Yields:
            String chunks of the response as they arrive

        Raises:
            Exception: If API call fails
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        start_time = time.time()
        model_used = model or self.default_model
        total_chars = 0

        # Log the request
        log_llm_request(
            method="chat_stream",
            messages_count=len(messages),
            model=model_used,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_kwargs=kwargs,
        )

        converted_messages = self._convert_messages(messages)

        client = ChatOpenRouter(
            model=model_used,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        try:
            async for chunk in client.astream(converted_messages):
                if hasattr(chunk, "content") and chunk.content:
                    total_chars += len(chunk.content)
                    yield chunk.content

            # Log completion
            duration_ms = (time.time() - start_time) * 1000
            log_llm_response(
                method="chat_stream",
                status="success",
                content_length=total_chars,
                model=model_used,
                duration_ms=duration_ms,
            )

        except LangChainException as e:
            duration_ms = (time.time() - start_time) * 1000
            log_llm_error(
                method="chat_stream",
                error=e,
                context={"model": model_used, "duration_ms": duration_ms},
            )
            raise OpenRouterError(f"OpenRouter API error: {e}", e) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_llm_error(
                method="chat_stream",
                error=e,
                context={"model": model_used, "duration_ms": duration_ms},
            )
            raise OpenRouterError(f"OpenRouter request failed: {e}", e) from e

    async def chat_with_schema(
        self,
        messages: list[LLMMessage],
        schema: type[BaseModel],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Chat with structured output using a Pydantic schema.

        Args:
            messages: List of chat messages
            schema: Pydantic BaseModel class defining the output structure
            model: Model to use
            temperature: Sampling temperature
            **kwargs: Additional arguments

        Returns:
            LLMResponse with parsed structured data in metadata['parsed']

        Raises:
            Exception: If parsing fails or API call fails
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        start_time = time.time()
        model_used = model or self.default_model

        # Log the request
        log_llm_request(
            method="chat_with_schema",
            messages_count=len(messages),
            model=model_used,
            temperature=temperature,
            schema=schema.__name__,
            extra_kwargs=kwargs,
        )

        converted_messages = self._convert_messages(messages)

        client = ChatOpenRouter(
            model=model_used,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=temperature,
            **kwargs,
        )

        # Enable structured output
        structured_client = client.with_structured_output(schema)

        try:
            response = await structured_client.ainvoke(converted_messages)
            built_response = self._build_response(response)

            # Calculate duration and log success
            duration_ms = (time.time() - start_time) * 1000
            log_llm_response(
                method="chat_with_schema",
                status="success",
                content_length=len(built_response.content),
                usage=built_response.usage,
                model=built_response.model,
                duration_ms=duration_ms,
            )

            return built_response

        except LangChainException as e:
            duration_ms = (time.time() - start_time) * 1000
            log_llm_error(
                method="chat_with_schema",
                error=e,
                context={"model": model_used, "schema": schema.__name__, "duration_ms": duration_ms},
            )
            raise OpenRouterError(f"OpenRouter API error: {e}", e) from e
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_llm_error(
                method="chat_with_schema",
                error=e,
                context={"model": model_used, "schema": schema.__name__, "duration_ms": duration_ms},
            )
            raise OpenRouterError(f"OpenRouter request failed: {e}", e) from e

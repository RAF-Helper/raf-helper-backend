# OpenRouter LLM Client

**Location:** `src/app/chat/llm/openrouter_client.py`

## Overview

Production-ready async client for OpenRouter API. Built on LangChain's `ChatOpenRouter`.

**Key Features:**
- Async chat, streaming, tool calling, structured output
- Automatic fallback retry logic
- Token tracking and structured logging
- Model override per request

## Quick Example

```python
from app.chat.llm import OpenRouterClient, LLMMessage

client = OpenRouterClient()

# Basic chat
response = await client.chat([
    LLMMessage(role="user", content="What is the capital of France?")
])
print(response.content)  # "Paris is the capital of France."
print(response.usage)    # {'prompt_tokens': 42, 'completion_tokens': 12, ...}

# With tools
tools = [{
    "type": "function",
    "function": {
        "name": "search_staff",
        "description": "Search faculty directory",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}}
    }
}]
response = await client.chat_with_tools(
    messages=[LLMMessage(role="user", content="Find Professor Smith")],
    tools=tools
)
```

## Configuration

Set in `.env`:

```bash
OPENROUTER_API_KEY=your-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-oss-20b:free  # default
```

Optional: Configure fallback models at initialization:

```python
client = OpenRouterClient(
    model="qwen/qwen3.6-plus:free",
    fallback_models=["stepfun/step-3.5-flash:free", "openai/gpt-oss-20b:free"]
)
```

## API Methods

All methods are `async` and raise `OpenRouterError` on final failure.

### `chat(messages, model=None, temperature=0.7, max_tokens=None, **kwargs)`

Basic completion. Returns `LLMResponse`.

```python
response = await client.chat(messages)
```

### `chat_with_tools(messages, tools, model=None, temperature=0.7, **kwargs)`

Tool calling. Tool calls returned in `response.metadata["tool_calls"]`.

```python
if tool_calls := response.metadata.get("tool_calls"):
    for call in tool_calls:
        print(call["name"], call["args"])
```

### `chat_stream(messages, ...) → AsyncIterator[str]`

Stream response chunks:

```python
async for chunk in client.chat_stream(messages):
    print(chunk, end="", flush=True)
```

### `chat_with_schema(messages, schema, ...)`

Structured output with Pydantic model. Parsed result in `response.metadata["parsed"]`.

```python
class Weather(BaseModel):
    location: str
    temp: float

response = await client.chat_with_schema(messages, Weather)
weather: Weather = response.metadata["parsed"]
```

## Data Types

```python
@dataclass
class LLMMessage:
    role: str                    # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: str | None    # when role="tool"

@dataclass
class LLMResponse:
    content: str
    usage: dict[str, int] | None
    model: str | None
    metadata: dict[str, Any] | None
```

## Fallback Behavior

- **Retryable:** rate limits (429), 5xx, timeouts, connection errors
- **Non-retryable:** 401/403 auth, 400 invalid model, content policy
- Tries models in order: `[primary] + fallback_models`
- Logs each attempt with `is_fallback` flag

## Logging

Logs to `logs/llm.log` automatically (configured in `src/app/app.py`):

```
INFO  Request → chat | model=... | temp=0.7 | messages=2
INFO  Response ← chat | status=success | len=245 | usage=... | 1234ms
ERROR Error in chat: OpenRouterError: ... | context={'model': ..., 'duration_ms': ...}
```

Monitor with: `tail -f logs/llm.log`

## Agents Integration

Agents receive client via dependency injection:

```python
class StaffAgent(BaseAgent):
    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        response = await self.llm_client.chat_with_tools(
            messages=[LLMMessage(role="user", content=inp.masked_message)],
            tools=[get_staff_documents_def]
        )
        # Process response...
```

Base agent (`src/app/chat/agents/base.py`) handles tool execution loop.

## Error Handling

```python
from app.chat.llm import OpenRouterError

try:
    response = await client.chat(messages)
except OpenRouterError as e:
    logger.error(f"LLM failed: {e}")
    # Return user-friendly message or retry with different model
```

## Important Notes

- **Tool calling:** Requires models that support function calling (Claude, GPT, Qwen).
- **Token limits:** Check OpenRouter model specs; trim history if needed.
- **Streaming:** Not all models support streaming; fallback to non-streaming if chunks empty.
- **Cost:** Free models have daily limits (~50 requests/day). Monitor usage.
- **Reuse client:** Instantiate once (at app startup) and reuse across requests.

## See Also

- [Agents](agents.md) - Agent architecture and implementation
- [Tools](tools.md) - Tool definitions and usage patterns
- [Test UI](../chat/test_ui.md) - Interactive testing interface
- [OpenRouter Docs](https://openrouter.ai/docs)

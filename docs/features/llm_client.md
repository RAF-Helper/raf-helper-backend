# OpenRouter LLM Client Documentation

## Overview

The `OpenRouterClient` is the main interface for all LLM interactions in the RAF Helper Backend system. It provides a unified, production-ready client for communicating with OpenRouter's API using **LangChain's `ChatOpenRouter`** integration.

### Location
`src/app/chat/llm/openrouter_client.py`

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Code                        │
│     (Orchestrator, Agents, Services, etc.)                 │
└────────────────────────┬────────────────────────────────────┘
                         │ uses
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               OpenRouterClient (our interface)             │
│  • chat()              - Basic completions                 │
│  • chat_with_tools()   - Function/tool calling            │
│  • chat_stream()       - Streaming responses              │
│  • chat_with_schema()  - Structured output (Pydantic)     │
└────────────────────────┬────────────────────────────────────┘
                         │ delegates to
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          ChatOpenRouter (LangChain integration)            │
│  • Async HTTP client                                       │
│  • Retry logic                                             │
│  • Token tracking                                          │
│  • Response parsing                                        │
└────────────────────────┬────────────────────────────────────┘
                         │ makes HTTP calls to
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                OpenRouter API (openrouter.ai)              │
│  • Model routing                                           │
│  • Provider abstraction                                    │
│  • Cost optimization                                       │
└─────────────────────────────────────────────────────────────┘
```

## Features

✅ **Async Operation** - Full async/await support for high-concurrency applications  
✅ **Tool Calling** - Native support for function/tool calling in OpenAI format  
✅ **Streaming** - Real-time streaming responses with async iteration  
✅ **Structured Output** - Automatic JSON parsing into Pydantic models  
✅ **Token Tracking** - Usage statistics (prompt, completion, total tokens)  
✅ **Model Flexibility** - Override default model per request  
✅ **Error Handling** - Custom exceptions with proper logging  
✅ **Observability Ready** - Integrates with Langfuse via LangChain callbacks  
✅ **Production-Ready** - Built on battle-tested LangChain library  
✅ **Structured Logging** - Detailed logs to files for debugging and monitoring  

## Configuration

### Environment Variables

The client reads configuration from environment variables (managed via `pydantic-settings`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | (required) | Your OpenRouter API key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | Base URL for API |
| `OPENROUTER_MODEL` | `openai/gpt-oss-20b:free` | Default model to use |

### Configuration File

Settings are defined in `src/app/config.py`:

```python
class Settings(BaseSettings):
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-oss-20b:free"
```

## Usage Examples

### Basic Chat Completion

```python
from app.chat.llm import OpenRouterClient, LLMMessage

client = OpenRouterClient()

messages = [
    LLMMessage(role="system", content="You are a helpful assistant."),
    LLMMessage(role="user", content="What is the capital of France?"),
]

response = await client.chat(messages)
print(response.content)  # "The capital of France is Paris."
print(response.usage)    # {'prompt_tokens': 42, 'completion_tokens': 12, ...}
```

### Tool/Function Calling

```python
from app.chat.llm import OpenRouterClient, LLMMessage

client = OpenRouterClient()

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. 'Paris'"
                    }
                },
                "required": ["location"]
            }
        }
    }
]

messages = [
    LLMMessage(role="user", content="What's the weather in Tokyo?")
]

response = await client.chat_with_tools(messages, tools)

# Check if tool was called
if response.metadata and "tool_calls" in response.metadata:
    for tool_call in response.metadata["tool_calls"]:
        print(f"Tool: {tool_call['name']}, Args: {tool_call['args']}")
```

### Streaming Responses

```python
from app.chat.llm import OpenRouterClient, LLMMessage

client = OpenRouterClient()

messages = [
    LLMMessage(role="user", content="Write a haiku about coding.")
]

async for chunk in client.chat_stream(messages):
    print(chunk, end="", flush=True)
# Output arrives in real-time:
# Lines of code flow
# Bugs emerge then vanish fast
# Debugging twilight
```

### Structured Output (Pydantic)

```python
from pydantic import BaseModel, Field
from app.chat.llm import OpenRouterClient, LLMMessage

# Define your output schema
class WeatherReport(BaseModel):
    location: str = Field(description="City name")
    temperature: float = Field(description="Temperature in Celsius")
    conditions: str = Field(description="Weather conditions")
    confidence: float = Field(description="Confidence score 0-1")

client = OpenRouterClient()

messages = [
    LLMMessage(role="user", content="Weather in Paris right now?")
]

response = await client.chat_with_schema(messages, WeatherReport)

# Access parsed structured data
if "parsed" in response.metadata:
    weather: WeatherReport = response.metadata["parsed"]
    print(f"Temp: {weather.temperature}°C, Conditions: {weather.conditions}")
```

### Model Override

```python
# Use a different model for this specific request
response = await client.chat(
    messages,
    model="anthropic/claude-sonnet-4.5",
    temperature=0.3,
    max_tokens=1000
)
```

### With Custom Parameters (kwargs)

```python
# Additional OpenRouter-specific parameters
response = await client.chat(
    messages,
    model="openai/gpt-oss-20b:free",
    temperature=0.7,
    max_tokens=500,
    top_p=0.9,          # Nucleus sampling
    top_k=50,           # Top-k sampling
    seed=42,            # For reproducible results
    extra_headers={     # Custom headers
        "HTTP-Referer": "https://myapp.com",
        "X-Title": "My App"
    }
)
```

## API Reference

### `OpenRouterClient`

#### `__init__()`
Initializes the client with configuration from settings.

**Raises:** `OpenRouterError` if configuration is invalid.

#### `async chat(messages, model=None, temperature=0.7, max_tokens=None, **kwargs) -> LLMResponse`

Basic chat completion without tool calling.

**Parameters:**
- `messages` (list[LLMMessage]): List of messages with `role` ("system", "user", "assistant") and `content`
- `model` (str | None): Override default model
- `temperature` (float): Sampling temperature (0.0-2.0, default 0.7)
- `max_tokens` (int | None): Maximum tokens to generate
- `**kwargs`: Additional arguments for ChatOpenRouter

**Returns:** `LLMResponse` with:
  - `content` (str): Generated text
  - `usage` (dict[str, int] | None): Token usage statistics
  - `model` (str | None): Model used
  - `metadata` (dict[str, Any] | None): Additional response metadata

**Raises:**
- `ValueError`: If messages list is empty
- `OpenRouterError`: If API call fails

---

#### `async chat_with_tools(messages, tools, model=None, temperature=0.7, **kwargs) -> LLMResponse`

Chat completion with tool/function calling support.

**Parameters:**
- `messages` (list[LLMMessage]): List of messages
- `tools` (list[dict]): List of tool definitions in OpenAI format
- `model`, `temperature`, `**kwargs`: Same as `chat()`

**Returns:** `LLMResponse` with tool calls in `metadata["tool_calls"]` if any.

**Tool Call Format:**
```python
response.metadata["tool_calls"] = [
    {
        "name": "get_weather",
        "args": {"location": "Paris"},
        "id": "call_abc123"
    }
]
```

**Raises:**
- `ValueError`: If messages or tools empty
- `OpenRouterError`: If API call fails

---

#### `async chat_stream(messages, model=None, temperature=0.7, max_tokens=None, **kwargs) -> AsyncIterator[str]`

Stream chat completion response in real-time.

**Parameters:** Same as `chat()`.

**Yields:** String chunks as they arrive (may be partial words).

**Usage:**
```python
async for chunk in client.chat_stream(messages):
    print(chunk, end="", flush=True)
```

**Raises:**
- `ValueError`: If messages empty
- `OpenRouterError`: If stream fails

---

#### `async chat_with_schema(messages, schema, model=None, temperature=0.7, **kwargs) -> LLMResponse`

Chat with structured output using a Pydantic model schema.

**Parameters:**
- `messages` (list[LLMMessage]): List of messages
- `schema` (type[BaseModel]): Pydantic model class defining output structure
- `model`, `temperature`, `**kwargs`: Same as `chat()`

**Returns:** `LLMResponse` with parsed structured data in `metadata["parsed"]`.

**Usage:**
```python
class MySchema(BaseModel):
    answer: str
    score: float

response = await client.chat_with_schema(messages, MySchema)
parsed: MySchema = response.metadata["parsed"]
```

**Raises:**
- `ValueError`: If messages empty
- `OpenRouterError`: If parsing or API call fails

---

### Data Structures

#### `LLMMessage`
Simple message container:
```python
@dataclass
class LLMMessage:
    role: str      # "system", "user", or "assistant"
    content: str   # Message text
```

#### `LLMResponse`
Response container:
```python
@dataclass
class LLMResponse:
    content: str                      # Generated text
    usage: dict[str, int] | None      # {'prompt_tokens': ..., ...}
    model: str | None                 # Model identifier
    metadata: dict[str, Any] | None   # Tool calls, parsed data, etc.
```

## Error Handling

The client defines `OpenRouterError` for all API-related failures. It wraps the original exception for debugging.

```python
from app.chat.llm import OpenRouterError

try:
    response = await client.chat(messages)
except OpenRouterError as e:
    print(f"Error: {e}")
    print(f"Original: {e.original_exception}")
    # Handle gracefully - retry, fallback, or user-friendly message
```

### Error Recovery Strategies

1. **Transient failures**: Implement retry with exponential backoff
2. **Rate limits**: Check `response_metadata` for rate limit info
3. **Invalid API key**: Fail fast at initialization (check config)
4. **Model unavailable**: Try fallback model: `model="anthropic/claude-3.7-sonnet"`

## Integration with Agents

All agents in `src/app/chat/agents/` receive `OpenRouterClient` via dependency injection:

```python
class QAAgent(BaseAgent):
    def __init__(self, llm_client: BaseLLMClient):
        super().__init__(llm_client)

    async def process(self, context: AgentContext, query: str) -> str:
        prompt = self._build_prompt(query, context)
        messages = [LLMMessage(role="user", content=prompt)]
        response = await self.llm_client.chat(messages)
        return response.content
```

The base agent interface in `src/app/chat/agents/base.py` defines `BaseAgent` which all agents inherit from.

## Best Practices

### 1. **Use System Prompts for Role Definition**
```python
messages = [
    LLMMessage(
        role="system",
        content="You are a university assistant. Answer concisely."
    ),
    LLMMessage(role="user", content=query)
]
```

### 2. **Choose Models Based on Task Complexity**
- **Simple Q&A**: `openai/gpt-oss-20b:free` (fast, cheap, good for Russian)
- **Complex reasoning**: `anthropic/claude-sonnet-4.5` or `openai/gpt-4.1`
- **Tool-heavy tasks**: Models with strong tool calling (Claude, GPT-4)

### 3. **Limit Context Length**
OpenRouter models have token limits. Trim chat history:
```python
# Keep last 10 messages to avoid hitting limits
recent_messages = messages[-10:]
```

### 4. **Handle Tool Calls in Chat Loop**
When using `chat_with_tools`, be prepared for the model to request tool execution:

```python
def _execute_tool_call(tool_name: str, arguments: dict) -> str:
    # Your tool execution logic
    return result

# In agent:
response = await client.chat_with_tools(messages, tools)
if tool_calls := response.metadata.get("tool_calls"):
    for tool_call in tool_calls:
        result = _execute_tool_call(tool_call["name"], tool_call["args"])
        # Append tool result to messages and call LLM again
        messages.append(LLMMessage(role="tool", content=str(result)))
        response = await client.chat(messages)
```

### 5. **Set Appropriate Temperature**
- `temperature=0.0`: Deterministic, factual answers
- `temperature=0.7` (default): Balanced creativity
- `temperature=1.0+`: More creative, varied outputs

### 6. **Track Costs**
Log `response.usage` and calculate costs using OpenRouter pricing:
```python
usage = response.usage
if usage:
    cost = (usage["prompt_tokens"] * prompt_cost_per_1k +
            usage["completion_tokens"] * completion_cost_per_1k) / 1000
```

### 7. **Add Observability with Langfuse**
To enable tracing and prompt versioning, add Langfuse callbacks:

```python
from langfuse.callback import CallbackHandler

langfuse_handler = CallbackHandler()

client = ChatOpenRouter(
    model="openai/gpt-oss-20b:free",
    callbacks=[langfuse_handler],
    # ... other config
)
```

### 8. **Validate Schemas for Structured Output**
Ensure your Pydantic models have clear field descriptions for better LLM compliance:

```python
class Output(BaseModel):
    answer: str = Field(description="The final answer to the user's query")
    confidence: float = Field(description="Confidence score 0.0-1.0")
```

## Testing

### Unit Testing with Mocks

Use `unittest.mock.AsyncMock` to mock LLM responses:

```python
from unittest.mock import AsyncMock, patch
from app.chat.llm import OpenRouterClient, LLMResponse

async def test_qa_agent():
    mock_response = LLMResponse(
        content="Paris is the capital of France.",
        usage={"prompt_tokens": 10, "completion_tokens": 5}
    )

    with patch.object(OpenRouterClient, 'chat', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = mock_response

        client = OpenRouterClient()
        result = await client.chat([LLMMessage(role="user", content="Capital of France?")])

        assert result.content == "Paris is the capital of France."
```

### Integration Testing

For end-to-end tests with real API:
```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api():
    client = OpenRouterClient()
    response = await client.chat([
        LLMMessage(role="user", content="Hello!")
    ])
    assert response.content
    assert response.usage
```

## Performance Considerations

### Async Operations
All methods are `async` and use LangChain's async I/O (`ainvoke`, `astream`) to avoid blocking the event loop.

### Connection Pooling
`ChatOpenRouter` uses `httpx.AsyncClient` under the hood with connection pooling. The client is initialized once at app startup (see `src/app/app.py` for FastAPI integration pattern).

### Streaming vs Non-Streaming
- Use `chat_stream()` for real-time user-facing responses (chat UI)
- Use `chat()` for background processing where you need the full response before proceeding

### Token Limits
- Check model context window limits on [OpenRouter docs](https://openrouter.ai/docs)
- Trim message history before exceeding limits
- Consider chunking long context materials

## Logging

The OpenRouter client includes comprehensive structured logging to help you monitor and debug LLM interactions.

### Log Files

Logs are written to the `logs/` directory:

- **`logs/app.log`** - All application logs (including LLM logs)
- **`logs/llm.log`** - Dedicated file for LLM-specific logs only (filtered)

### Log Format

```
2026-03-31 17:16:14.950 | INFO     | app.chat.llm.openrouter_client:chat:187 - 
    Request → chat | model=openai/gpt-oss-20b:free | 
    temp=0.7 | messages=5 | kwargs={}
```

### What Gets Logged

**For every request:**
- Method name (`chat`, `chat_with_tools`, `chat_stream`, `chat_with_schema`)
- Model used
- Temperature setting
- Number of messages
- Additional parameters (max_tokens, tools count, schema name)

**For every response:**
- Status (`success` or `error`)
- Response content length
- Token usage (prompt, completion, total)
- Model that responded
- Request duration in milliseconds

**For errors:**
- Exception type and message
- Context (model, duration, tool count, schema)
- Full stack trace (in file logs)

### Setting Up Logging

Logging is automatically configured when the FastAPI app starts (see `src/app/app.py`). The `setup_logging()` function in `src/app/logging_config.py` configures:

- Log directory: `logs/` (created automatically)
- Log level: `DEBUG` if `settings.debug=True`, else `INFO`
- Console output: Enabled only in debug mode
- File output: Always enabled for both app.log and llm.log

You can also initialize logging manually:

```python
from app.logging_config import setup_logging

setup_logging(
    log_dir="logs",
    log_level="DEBUG",  # or INFO, WARNING, ERROR
    enable_console=True,
)
```

### Viewing Logs

```bash
# Real-time monitoring
tail -f logs/llm.log

# Search for errors
grep -i error logs/llm.log

# View recent requests
grep "Request →" logs/llm.log | tail -20

# Check API performance
grep "duration_ms" logs/llm.log | sort -nr | head -10

# Filter by model
grep "model=qwen" logs/llm.log
```

### Sample Log Entries

**Request:**
```
2026-03-31 17:16:14.950 | INFO | app.chat.llm.openrouter_client:chat:189 - 
    Request → chat | model=openai/gpt-oss-20b:free | 
    temp=0.7 | messages=2 | max_tokens=None | extra_kwargs={}
```

**Response:**
```
2026-03-31 17:16:16.234 | INFO | app.chat.llm.openrouter_client:chat:220 - 
    Response ← chat | status=success | len=245 | 
    model=openai/gpt-oss-20b:free | 
    usage={'prompt_tokens': 87, 'completion_tokens': 32, 'total_tokens': 119} | 
    1284.5ms
```

**Error:**
```
2026-03-31 17:16:18.567 | ERROR | app.chat.llm.openrouter_client:chat:234 - 
    Error in chat: OpenRouterError: OpenRouter API error: ... | 
    context={'model': 'openai/gpt-oss-20b:free', 'duration_ms': 1502.3}
    Traceback (most recent call last):
      File "...openrouter_client.py", line 220, in chat
        response = await client.ainvoke(converted_messages)
```

### Integration with Observability Tools

For production deployments, consider integrating with:

- **Langfuse** - LLM observability and tracing (see "Observability Ready" feature)
- **Prometheus + Grafana** - Metrics collection and dashboards
- **Sentry** - Error tracking and alerting

Example of adding Langfuse callbacks to the client (in code):

```python
from langfuse.callback import CallbackHandler

langfuse_handler = CallbackHandler()

# When creating ChatOpenRouter instances, pass callbacks
client = ChatOpenRouter(
    model="...",
    callbacks=[langfuse_handler],
)
```

## Security

### API Key Management
- Store `OPENROUTER_API_KEY` in environment variables or secret manager
- Never commit API keys to version control
- Rotate keys regularly
- Use separate keys for dev/staging/prod

### Input Validation
- Validate user input before sending to LLM
- Sanitize sensitive data (PII) - use Presidio as per architecture
- Implement rate limiting per user to prevent abuse

### Output Filtering
- Apply content moderation if needed
- Don't trust LLM outputs blindly - validate before using in critical paths

## Future Enhancements

Planned improvements (see `docs/architecture.md`):

1. **LangGraph Integration** - Multi-agent workflows with state
2. **Langfuse Observability** - Full tracing and prompt management
3. **Caching Layer** - Cache frequent queries (Redis)
4. **Fallback Models** - Automatic fallback if primary model fails
5. **Prompt Management** - Version-controlled prompts stored in DB
6. **Cost Optimization** - Smart model routing based on query complexity

## Troubleshooting

### "Invalid API key"
Check `OPENROUTER_API_KEY` is set correctly. Test with:
```bash
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     https://openrouter.ai/api/v1/models
```

### "Model not found"
Verify the model name exists in your account. Some models require additional credits.

### Rate limits hit
OpenRouter has per-minute limits. Implement retry with backoff:
```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(multiplier=1, min=4, max=10),
       stop=stop_after_attempt(3))
async def chat_with_retry(messages):
    return await client.chat(messages)
```

### Streaming chunks are empty
Some models don't support streaming. Check the model capabilities on OpenRouter. Fallback to non-streaming.

### Tool calling not working
Ensure your tool definitions follow OpenAI format exactly. Check that the model you're using supports tool calling (not all do).

## References

- [OpenRouter API Docs](https://openrouter.ai/docs)
- [LangChain ChatOpenRouter](https://python.langchain.com/docs/integrations/chat/openrouter)
- [LangChain Chat Models Guide](https://python.langchain.com/docs/concepts/chat_models/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling) (format reference)
- [Pydantic V2](https://docs.pydantic.dev/latest/)

---

**Last Updated:** March 31, 2026  
**Client Version:** 1.0.0  
**Compatible Models:** All OpenRouter models (Qwen, Claude, GPT, etc.)

# Agent System Documentation

## Overview

The RAF Helper Backend uses a **multi-agent architecture** where each agent specializes in a specific domain. Agents receive user queries, optionally use tools to retrieve data from Elasticsearch, interact with the LLM via `OpenRouterClient`, and return responses.

### Location

- Base agent class: `src/app/chat/agents/base.py`
- Agent implementations: `src/app/chat/agents/*.py`
- Tool definitions: `src/app/tools/search_tools.py`
- Prompts: `src/prompts/*.txt`
- Data models: `src/app/chat/state.py` (AgentInput, AgentOutput)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Chat Request (/chat)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Orchestrator                             │
│  • Applies PII masking                                     │
│  • Routes to appropriate agent (or uses forced_agent)     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent (e.g., StaffAgent)                │
│  • Receives AgentInput (message, masked_message, etc.)    │
│  • Optionally performs custom pre-processing (unmasking)  │
│  • Calls _call_llm(use_tools=True) with system prompt    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  BaseAgent._call_llm                       │
│  • Builds messages from history + system + user prompt   │
│  • If use_tools: calls chat_with_tools()                  │
│  • Handles tool execution loop                            │
│  • Returns final LLM response content                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                OpenRouterClient                            │
│  • Sends messages + tools to LLM                          │
│  • Returns LLMResponse with tool_calls if any             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
            [LLM may request tool calls]
                         │
                         ├──────────────┐
                         │              │
                    Tool results      Final answer
                         │              │
                         └───────┬──────┘
                                 │
                                 ▼
                        AgentOutput returned
```

## BaseAgent

The `BaseAgent` class provides the foundation for all agents.

### Core Methods

#### `_call_llm(...) -> str`

Unified method to call the LLM with flexible patterns.

**Parameters:**
- `messages` (list[LLMMessage] | None): Pre-built messages (highest priority)
- `system_prompt` (str | None): System message
- `user_prompt` (str | None): User message
- `context` (str | None): Additional context (appended to system prompt)
- `history` (list[dict[str, str]] | None): Chat history list of `{"role": "...", "content": "..."}`
- `temperature` (float): Sampling temp (default 0.7)
- `model` (str | None): Override default model
- `max_tokens` (int | None): Token limit
- `use_tools` (bool): Enable tool calling if `self.tools` is non-empty
- `**kwargs`: Additional args to LLM client

**Returns:** `str` - Final response content (after tool execution if applicable)

**Tool Execution Loop:** When `use_tools=True` and `self.tools` is set:
1. Calls `llm_client.chat_with_tools(messages, tools, ...)`
2. If LLM returns `tool_calls` in metadata, executes each tool function from `TOOL_FUNCTIONS`
3. Appends tool results as "tool" role messages
4. Repeats until LLM returns final answer without tool calls

#### `_load_prompt(name: str) -> str`

Load a prompt template from `src/prompts/{name}.txt`.

#### `_format_prompt(name: str, **kwargs) -> str`

Load and format a prompt with placeholders (e.g., `{query}`, `{context}`). The `BaseAgent._call_llm` does automatic formatting if you pass `system_prompt` via `_format_prompt` result.

### Class Attributes

- `agent_type: AgentType` - Required. Enum value identifying the agent.
- `tools: list[dict]` - List of OpenAI-format tool definitions (empty by default)
- `prompt_name: str | None` - Name of prompt file in `src/prompts/` (if using `_load_prompt()` without explicit name)

### Subclassing Pattern

```python
from .base import BaseAgent
from ...schemas.agent import AgentType
from ...tools.search_tools import get_staff_documents_def  # if using tools

class MyAgent(BaseAgent):
    agent_type = AgentType.my_agent
    tools = [get_staff_documents_def]  # or [] if no tools

    def __init__(self, llm_client):
        super().__init__(llm_client)

    async def run(self, inp: AgentInput) -> AgentOutput:
        # Optional: custom pre-processing of inp.masked_message
        user_query = inp.masked_message

        # Option A: Use tools (let LLM decide when to call)
        response = await self._call_llm(
            system_prompt=self._load_prompt("my_agent"),
            user_prompt=user_query,
            history=inp.history,
            temperature=0.7,
            use_tools=True,
        )

        # Option B: Call tool manually and pass as context
        # result = await my_tool_function(query=user_query)
        # response = await self._call_llm(
        #     system_prompt=self._load_prompt("my_agent"),
        #     user_prompt=user_query,
        #     context=result,
        #     history=inp.history,
        # )

        return AgentOutput(
            content=response,
            agent_used=self.agent_type,
            masked_query=inp.masked_message,
        )
```

## AgentInput and AgentOutput

Located in `src/app/chat/state.py`.

### AgentInput

```python
@dataclass
class AgentInput:
    message: str                   # Original user message (raw)
    masked_message: str            # PII-masked version (sent to LLM)
    chat_id: int
    user_id: int
    history: list[dict[str, str]]  # Chat history
    file_ids: list[int]            # Context material PG file IDs
    use_web_search: bool
    summarization_mode: SummarizationMode
    forced_agent: Optional[AgentType]
    extra: dict[str, Any] = field(default_factory=dict)
    pii_spans: list[dict] = field(default_factory=list)  # From masking
```

### AgentOutput

```python
@dataclass
class AgentOutput:
    content: str                  # Final response to user
    agent_used: AgentType        # Which agent produced this
    masked_query: Optional[str] = None  # Masked query for logging
    metadata: dict[str, Any] = field(default_factory=dict)
```

## Tool System

### Tool Definition Format

Tools follow OpenAI function calling schema:

```python
tool_definition = {
    "name": "tool_name",
    "description": "What it does",
    "parameters": {
        "type": "object",
        "properties": {
            "param_name": {
                "type": "string",
                "description": "Parameter description"
            },
            # ...
        },
        "required": ["param1", ...]
    }
}
```

### Tool Registration

1. Define the async function in `src/app/tools/search_tools.py` (or new module)
2. Define the tool schema in the same file
3. Export the definition and function:
   ```python
   ALL_TOOLS = [tool_def1, tool_def2, ...]
   TOOL_FUNCTIONS = {"tool_name": tool_function, ...}
   ```
4. In agent, import the definition and add to `tools` class attribute
5. `BaseAgent._call_llm` automatically executes tool functions from `TOOL_FUNCTIONS`

### Built-in Tools

| Tool | Description | Agent(s) |
|------|-------------|----------|
| `get_staff_documents` | Search staff by name/position/department/room | StaffAgent |
| `get_events_documents` | Search events with date/bonus filters | EventsAgent |
| `get_materials_fragments` | Search context material chunks | QAAgent, SummarizerAgent, PresentationAgent |

See `docs/tools.md` (to be created) for detailed tool documentation.

## Agent Implementations

### StaffAgent

- **AgentType:** `staff`
- **Tools:** `get_staff_documents`
- **Prompt:** `src/prompts/staff_agent.txt`
- **Special:** Performs selective PII unmasking before LLM call. If user mentions a person's name that exists in staff DB, it restores the canonical name.

**Flow:**
1. Receive `AgentInput` with `masked_message` and `pii_spans`
2. For each `PERSON` span, query `find_staff_by_entities()` to check if it matches staff
3. If match, replace `[NAME]` in `masked_message` with full staff name from DB
4. Call LLM with unmasked user query + `get_staff_documents` tool
5. Return response

### EventsAgent

- **AgentType:** `events`
- **Tools:** `get_events_documents`
- **Prompt:** `src/prompts/events_agent.txt`
- **Flow:** Direct tool call, no special logic.

### QAAgent

- **AgentType:** `qa`
- **Tools:** `get_materials_fragments`
- **Prompt:** `src/prompts/qa_agent.txt`
- **Special:** Uses last 10 history messages to maintain context.
- **Flow:** LLM decides when to search documents; tool returns chunks.

### SummarizerAgent

- **AgentType:** `summarizer`
- **Tools:** `get_materials_fragments`
- **Prompt:** `src/prompts/summarizer_agent.txt` + `summarizer_mode_instructions.txt`
- **Formatting:** System prompt is formatted with `{mode}` and `{mode_instructions}` based on `inp.summarization_mode`
- **Flow:** Loads template, injects mode instructions, calls LLM with tool access.

### PresentationAgent

- **AgentType:** `presentation`
- **Tools:** `get_materials_fragments`
- **Prompt:** `src/prompts/presentation_agent.txt` (requires `{query}`)
- **Flow:** Formats prompt with user query, LLM creates presentation outline and content using material retrieval.

### AbstractAgent, SupportAgent

- Currently stubs; will be implemented later.

## Creating a New Agent

1. Create file `src/app/chat/agents/my_agent.py`
2. Define class inheriting from `BaseAgent`
3. Set `agent_type = AgentType.my_agent` (add to `AgentType` enum in `src/app/schemas/agent.py`)
4. Set `tools = [...]` if using tools
5. Implement `async def run(self, inp: AgentInput) -> AgentOutput`
6. Create prompt file `src/prompts/my_agent.txt`
7. (Optional) Add agent to orchestrator routing logic when implemented

## Prompt Guidelines

- Keep prompts concise and specific
- Instruct the LLM to use tools when appropriate
- Avoid embedding `{context}` or `{query}` placeholders when using tools; context comes from tool results, not system prompt
- For non-tool agents that need placeholders, use `{query}`, `{context}`, `{history}` as needed
- The `summarizer_agent.txt` shows advanced formatting with `{mode}` and `{mode_instructions}`

## Testing

_TODO: describe test chat interface_

## Observability

LLM interactions (including tool calls) are logged to `logs/llm.log` with:
- Agent name
- Tool calls requested and results
- Model used, token counts, duration

Check logs for debugging:
```bash
grep "tool_calls" logs/llm.log
tail -f logs/llm.log
```

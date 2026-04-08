# Test UI Documentation

## Overview

The Chainlit Test UI provides an interactive web interface for testing the multi-agent system. It allows you to:

- Select any agent (Staff, Events, Q&A, Summarizer, Presentation, Support, Abstract)
- Override the LLM model (choose from OpenRouter models)
- Chat in real-time and see agent responses
- View tool calls and token usage metadata
- Maintain chat history per session

**Location:** `src/app/chat/test_ui.py`

## Screenshot

*(Not available - run the UI to see it)*

## Requirements

- **DEBUG=True** in environment (test UI only runs in debug mode) — see explanation below
- OpenRouter API key configured (`OPENROUTER_API_KEY`)
- Elasticsearch running with data indexed (for tool-based agents)
- Dependencies: `chainlit>=2.5.0`

### Why DEBUG Mode?

The test UI is intended for **development and testing only**. It is restricted to debug mode because:

1. **Security:** The UI provides direct access to all agents and potentially sensitive operations. It bypasses authentication (Firebase) and authorization checks that the production API has.
2. **Resource Usage:** Tool calling agents make potentially expensive LLM API calls. In production, you want rate limiting, user quotas, and billing tracking — which the test UI doesn't implement.
3. **Isolation:** Debug mode ensures the test UI isn't accidentally exposed in production deployments. It's a safety barrier.
4. **Cost Control:** Free OpenRouter models have daily limits (~50 requests/day). Debug mode reminds developers to be mindful of usage.

To enable, set in your `.env` file or environment:
```bash
DEBUG=True
```

If you need the test UI in a staging environment, you can modify the check in `src/app/chat/test_ui.py` at your own discretion.

## Installation

The dependency is already in `pyproject.toml`:

```toml
"chainlit>=2.5.0",
```

Install with:

```bash
uv sync
```

## Starting the UI

Run the provided script:

```bash
# Set debug mode
export DEBUG=True

# Start the UI (default port 8001)
./scripts/start_test_ui.sh

# Or directly:
uv run chainlit run src.app.chat.test_ui:app --host 0.0.0.0 --port 8001
```

The UI will be available at: **http://localhost:8001**

## Usage

### 1. Configuration

- Click the ⚙️ (Settings) icon in the top-right
- Choose an **Agent** from the dropdown:
  - Staff — Faculty directory search
  - Events — University events
  - Q&A — Document-based question answering
  - Summarizer — Document summarization
  - Presentation — Generate presentation outline
  - Support — General assistance
  - Abstract — Abstract generation
- Choose a **Model** (optional override):
  - Qwen 3.6 Plus (free) — default, good for Russian
  - Claude 3.7 Sonnet — advanced reasoning
  - GPT-4o — balanced
  - GPT-4.1 — latest OpenAI

### 2. Chat

- Type your message in the input box and press Enter
- The agent will process your message and respond
- For tool-based agents (Staff, Events, Q&A), the LLM may call tools to retrieve data

### 3. Metadata

Each response shows:
- **Agent:** Which agent was used
- **🔧 Tools:** Number of tool calls (if any)
- **📊 Tokens:** Total token count for the turn

Click the response to expand and see full metadata (including `tool_calls` array if applicable).

## Example Queries

### Staff Agent (with PII unmasking)

```text
Найдите Петрова Ивана Сергеевича
```

If "Иванов Иван" exists in the staff index, the PII masking system will:
1. Detect `PERSON` entity in the query
2. Query staff database for matching names
3. Replace `[NAME]` with the canonical staff name from DB
4. LLM receives: "Найдите Иванов Иван Сергеевич"

### Events Agent

```text
Какие события запланированы в марте?
```

The agent will call `get_events_documents` with appropriate date filters.

### Q&A Agent

```text
Опишите требования к проекту
```

Assumes you have uploaded materials (documents) indexed in `context_materials`. The agent will use `get_materials_fragments` to search and answer.

## Architecture Notes

### Direct Agent Invocation

Unlike the production `/chat` endpoint which uses the `Orchestrator` (with PII masking and routing), the test UI:

1. Applies PII masking using `PIIMasker`
2. Creates an `AgentInput` with masked message and history
3. Instantiates the selected agent with an `OpenRouterClient`
4. Calls `agent.run(inp)` directly
5. Maintains chat history in the Chainlit session

### History Management

Chat history is stored in the Chainlit user session and included in subsequent messages. The history is trimmed to the last 20 turns to avoid token limit issues.

### Model Override

Model override is currently captured in the UI settings but not yet implemented in the agent's LLM client. Agents use the default model from settings. Future work will propagate the selected model to the `OpenRouterClient`.

### Tool Calling

Tool calling is handled by `BaseAgent._call_llm` when `use_tools=True`. The LLM decides which tools to invoke. Tool results are appended to the message history and the LLM generates a final response.

## Troubleshooting

### "Test UI is only available in DEBUG mode"

Set `DEBUG=True` in your environment or `.env` file.

### "Test UI is disabled in production mode"

Make sure `settings.debug` is True. Check your config.

### No tool calls appearing

Ensure:
- The agent you selected has `tools` defined (Staff, Events, Q&A, Summarizer, Presentation)
- Elasticsearch is running and has data indexed
- The LLM model you're using supports tool calling (most do)

### PII masking not working

The PII masker requires the Russian spaCy model:
```bash
uv run python -m spacy download ru_core_news_md
```

### Token errors

If you see errors about tokens, check that your OpenRouter API key is valid and you have credits.

## Extending the Test UI

### Adding a New Agent

1. Create the agent class in `src/app/chat/agents/`
2. Add it to `AGENT_CLASSES` mapping in `test_ui.py`
3. Add an entry to the `agent_options` in `@cl.on_chat_start`
4. Ensure the agent has a prompt file in `src/prompts/`

### Customizing Starter Messages

Edit the `@cl.set_starters` function to provide your own starter messages.

## Future Enhancements

- Model override propagation to agents
- File upload support (to index materials)
- Chat persistence (saving conversations)
- Multi-agent routing (orchestrator integration)
- Langfuse tracing integration
- Real-time tool call visualization

## See Also

- [Agents Documentation](agents.md) — Detailed agent architecture
- [Tools Documentation](tools.md) — Tool definitions and usage
- [LLM Client Documentation](llm_client.md) — OpenRouter client API
- [Requirements](../design/requirements.md) — System requirements and design

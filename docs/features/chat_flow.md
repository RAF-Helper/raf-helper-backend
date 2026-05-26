# Chat Flow & Agent Orchestration

## Overview
The system implements a multi-agent architecture where a central `Orchestrator` routes user requests to specialized agents. Each agent is equipped with specific tools and prompts to handle different domains of university knowledge.

## Request Lifecycle

### 1. API Gateway (`/chats/{chat_id}/messages`)
When a user sends a message, the system:
- Validates the user via Firebase token.
- Retrieves the chat session settings (e.g., web search preference).
- Fetches the chat history and the list of document IDs linked to the session context.
- Passes the request to the `Orchestrator`.

### 2. Orchestration & Routing
The `Orchestrator` acts as the brain of the system:
- **PII Masking**: Uses `PIIMasker` to hide sensitive information from the LLM.
- **Semantic Routing**: Uses a specialized LLM routing prompt to select the most appropriate agent based on the user's intent.
    - `support`: General system help, greetings.
    - `events`: University events, hackathons, bonus points.
    - `staff`: Faculty information, room numbers, teaching assignments.
    - `qa`: Questions based on uploaded study materials.
    - `summarizer`: Summarization of uploaded materials.
    - `abstract`: Essay and abstract writing.
    - `presentation`: Slide deck content generation.
- **Dispatch**: Forwards the `AgentInput` (message, history, file IDs, etc.) to the selected agent.

### 3. Agent Execution (`BaseAgent`)
All agents follow a unified execution pattern defined in `BaseAgent`:
- **Prompt Loading**: Loads agent-specific system prompts from `src/prompts/`.
- **Tool-Augmented Generation (TAG)**: If the agent has tools enabled, it enters a loop:
    1. **LLM Decision**: The LLM decides which tool to call and with what arguments.
    2. **Context Injection**: The system automatically injects `file_ids` and `use_web_search` flags into tool calls (e.g., `get_materials_fragments`) so the agent doesn't have to track them manually.
    3. **Tool Execution**: The tool is executed asynchronously (e.g., searching Elasticsearch or Tavily).
    4. **Feedback Loop**: The tool result is appended to the conversation history, and the LLM is called again to synthesize the final answer.

### 4. Response & Persistence
- The final synthesized response is saved to the database as an `assistant` message.
- The response is returned to the client along with metadata about which agent was used and the masked query.

## Agent Summary Table

| Agent | Primary Goal | Key Tool |
| :--- | :--- | :--- |
| **Support** | General assistance | N/A |
| **Events** | Event information | `get_events_documents` |
| **Staff** | Staff/Faculty lookup | `get_staff_documents` |
| **QA** | Document-based Q&A | `get_materials_fragments` |
| **Summarizer** | Content condensation | `get_materials_fragments` |
| **Abstract** | Academic writing | `get_materials_fragments` |
| **Presentation** | Slide content creation | `get_materials_fragments` |

## Key Architectural Decisions
- **Stateless Agents**: Agents do not store state; all necessary context (history, files) is passed in the `AgentInput` for each request.
- **Separation of Concerns**: The `Orchestrator` handles routing, while `BaseAgent` handles the tool-calling loop and LLM communication.
- **Dynamic Context**: The set of documents searched is determined by the chat session's linked files, ensuring the agent only accesses materials relevant to the current conversation.

# Chat Endpoints List

This document lists all endpoints involved in the chat flow and their relationship to the orchestration system.

## Main Orchestration Flow
The primary entry point for user interaction with the agent system is the message sending endpoint.

### Message Interaction
- `POST /chats/{chat_id}/messages`
    - **Role**: Orchestration Entry Point.
    - **Flow**: Endpoint $\rightarrow$ `Orchestrator.process` $\rightarrow$ `LangGraph` (PII $\rightarrow$ Router $\rightarrow$ Agent) $\rightarrow$ Response.
    - **Description**: Sends a user message to the system, triggers the LangGraph state machine, and returns the agent's response.

- `GET /chats/{chat_id}/messages`
    - **Role**: History Retrieval.
    - **Description**: Retrieves the message history for a specific chat session.

## Session & Context Management
These endpoints manage the state and materials used by the agents.

### Chat Sessions
- `POST /chats` - Create a new chat session.
- `GET /chats` - List all chat sessions for the user.
- `GET /chats/{chat_id}` - Retrieve specific chat details.
- `PATCH /chats/{chat_id}` - Update chat settings (e.g., web search, title).
- `DELETE /chats/{chat_id}` - Delete a chat session.

### RAG Context
- `GET /chats/{chat_id}/context` - List files linked as context to the chat.
- `POST /chats/{chat_id}/context/{file_id}` - Link a file to the chat context.
- `DELETE /chats/{chat_id}/context/{file_id}` - Unlink a file from the chat context.

## Redundancy Analysis
Current API surface is lean and follows RESTful patterns. No redundant endpoints identified.

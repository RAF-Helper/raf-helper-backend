"""Agent / chat interaction schemas."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    orchestrator = "orchestrator"
    support = "support"
    events = "events"
    staff = "staff"
    qa = "qa"
    summarizer = "summarizer"
    abstract = "abstract"
    presentation = "presentation"


class SummarizationMode(str, Enum):
    brief = "brief"
    default = "default"
    deep_dive = "deep_dive"


class ChatMessageRequest(BaseModel):
    """Request body for POST /chats/{chat_id}/messages."""

    message: str = Field(min_length=1, max_length=8192)
    agent: Optional[AgentType] = Field(
        default=None,
        description="Pin to a specific agent; if None the orchestrator routes.",
    )
    summarization_mode: SummarizationMode = SummarizationMode.default


class AgentChatResponse(BaseModel):
    """Response after agent processes a message."""

    message_id: int
    chat_id: int
    role: str = "assistant"
    content: str
    agent_used: AgentType
    masked_query: Optional[str] = None

"""Shared state types for the multi-agent system."""

from dataclasses import dataclass, field
from typing import Any, Optional

from ..schemas.agent import AgentType, SummarizationMode


@dataclass
class AgentInput:
    """Everything an agent needs to process a turn."""

    message: str
    masked_message: str
    chat_id: int
    user_id: int
    history: list[dict[str, str]]          # [{"role": ..., "content": ...}]
    file_ids: list[int]                    # PG file IDs in chat context
    use_web_search: bool
    summarization_mode: SummarizationMode
    forced_agent: Optional[AgentType]
    extra: dict[str, Any] = field(default_factory=dict)
    pii_spans: list[dict] = field(default_factory=list)  # PII spans from mask_text_with_spans


@dataclass
class AgentOutput:
    """What an agent returns after processing."""

    content: str
    agent_used: AgentType
    masked_query: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
